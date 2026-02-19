import io
import logging
import re
import zipfile
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
from openpyxl import Workbook
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema

from .companies_form import CompanySearchForm
from .apollo_service import search_companies, search_people, search_tags, enrich_people_bulk

logger = logging.getLogger(__name__)

# Apollo credits (estimated) – logged per API request
CREDITS_COMPANY_SEARCH = 1
CREDITS_PEOPLE_SEARCH = 1
CREDITS_TAGS_SEARCH = 0
CREDITS_ENRICH_PER_PERSON = 1  # bulk_match: ~1 credit per contact


def log_apollo_credits(endpoint_label: str, credits: int, detail: str = ""):
    """Log Apollo credits consumed for this API request (estimated)."""
    msg = f"====== {endpoint_label}  Credits: {credits} ======"
    if detail:
        msg += f"  ({detail})"
    logger.info(msg)
    # Also print so it shows in runserver console
    print(msg)


from .serializers import (
    CompanySearchSerializer,
    CompanySearchResponseSerializer,
    PeopleSearchSerializer,
    PeopleSearchResponseSerializer,
)


def normalize_companies(accounts: list) -> list:
    """Normalize Apollo API response to consistent format for UI."""
    companies = []
    for acc in accounts:
        # All location-related fields (HQ + other offices) for search/filter
        loc_parts = [
            acc.get("organization_raw_address"),
            acc.get("raw_address"),
            acc.get("organization_city"),
            acc.get("organization_state"),
            acc.get("organization_country"),
            acc.get("city"),
            acc.get("state"),
            acc.get("country"),
        ]
        searchable_location_string = " ".join(
            str(p).strip() for p in loc_parts if p
        ).lower()

        companies.append(
            {
                "id": acc.get("id"),
                "name": acc.get("name"),
                "primary_domain": acc.get("primary_domain"),
                "logo_url": acc.get("logo_url"),
                "industry": acc.get("industry"),
                "estimated_num_employees": acc.get("estimated_num_employees"),
                "city": acc.get("organization_city") or acc.get("city"),
                "state": acc.get("organization_state") or acc.get("state"),
                "country": acc.get("organization_country") or acc.get("country"),
                "searchable_location_string": searchable_location_string,
                "linkedin_url": acc.get("linkedin_url"),
                "founded_year": acc.get("founded_year"),
                "annual_revenue": acc.get("organization_revenue"),
                "annual_revenue_printed": acc.get("organization_revenue_printed"),
                "phone": acc.get("phone"),
                "website_url": acc.get("website_url"),
            }
        )
    return companies


def build_apollo_payload(data: dict) -> dict:
    """
    Build Apollo mixed_companies/search payload (organization search only).
    Job titles and seniorities are for people search only — not sent here.
    """
    page = data.get("page") or 1
    per_page = data.get("per_page") or 25
    try:
        page = int(page) if page is not None else 1
    except (TypeError, ValueError):
        page = 1
    try:
        per_page = min(int(per_page), 100) if per_page is not None else 25
    except (TypeError, ValueError):
        per_page = 25
    payload = {"page": page, "per_page": per_page}

    # Organization name
    company_name = data.get("company_name")
    if company_name and company_name.strip():
        payload["q_organization_name"] = company_name.strip()

    # Domains → q_organization_domains_list (array)
    domains = data.get("domains")
    if domains:
        domain_list = [d.strip() for d in domains.split(",") if d.strip()]
        if domain_list:
            payload["q_organization_domains_list"] = domain_list

    # Locations include – Apollo format: organization_locations array (lowercase, e.g. ["pakistan"])
    locations_included = data.get("locations_included")
    if locations_included:
        if isinstance(locations_included, str):
            loc_list = [
                x.strip().lower() for x in locations_included.split(",") if x.strip()
            ]
        else:
            loc_list = [
                str(x).strip().lower() for x in locations_included if str(x).strip()
            ]
        if loc_list:
            payload["organization_locations"] = loc_list

    # Locations exclude – Apollo format: organization_not_locations array (lowercase, e.g. ["india"])
    locations_excluded = data.get("locations_excluded")
    if locations_excluded:
        if isinstance(locations_excluded, str):
            loc_list = [
                x.strip().lower() for x in locations_excluded.split(",") if x.strip()
            ]
        else:
            loc_list = [
                str(x).strip().lower() for x in locations_excluded if str(x).strip()
            ]
        if loc_list:
            payload["organization_not_locations"] = loc_list

    # Employee range → organization_num_employees_ranges (list of "min,max")
    emp_min = data.get("employees_min")
    emp_max = data.get("employees_max")
    if emp_min is not None or emp_max is not None:
        min_val = emp_min if emp_min is not None else 1
        max_val = emp_max if emp_max is not None else 1000000
        payload["organization_num_employees_ranges"] = [f"{min_val},{max_val}"]

    # Revenue range → revenue_range { min, max } (values in millions as per form)
    rev_min = data.get("revenue_min")
    rev_max = data.get("revenue_max")
    if rev_min is not None or rev_max is not None:
        min_val = rev_min if rev_min is not None else 0
        max_val = rev_max if rev_max is not None else 999999
        payload["revenue_range"] = {"min": min_val, "max": max_val}

    # Organization keyword tags
    keyword_tags = data.get("organization_keyword")
    if keyword_tags:
        if isinstance(keyword_tags, str):
            tag_list = [t.strip() for t in keyword_tags.split(",") if t.strip()]
        else:
            tag_list = [str(t).strip() for t in keyword_tags if str(t).strip()]
        if tag_list:
            payload["q_organization_keyword_tags"] = tag_list

    # Organization job titles (company search filter)
    org_job_titles = data.get("q_organization_job_titles") or data.get(
        "organization_job_titles"
    )
    if org_job_titles:
        if isinstance(org_job_titles, str):
            org_job_titles = [t.strip() for t in org_job_titles.split(",") if t.strip()]
        else:
            org_job_titles = [str(t).strip() for t in org_job_titles if str(t).strip()]
        if org_job_titles:
            payload["q_organization_job_titles"] = org_job_titles

    # Organization job locations
    job_locs = data.get("organization_job_locations")
    if job_locs:
        if isinstance(job_locs, str):
            job_locs = [t.strip() for t in job_locs.split(",") if t.strip()]
        else:
            job_locs = [str(t).strip() for t in job_locs if str(t).strip()]
        if job_locs:
            payload["organization_job_locations"] = job_locs

    # Lookalike organization IDs (optional)
    lookalike_ids = data.get("lookalike_organization_ids")
    if lookalike_ids:
        if isinstance(lookalike_ids, str):
            lookalike_ids = [t.strip() for t in lookalike_ids.split(",") if t.strip()]
        else:
            lookalike_ids = [str(t).strip() for t in lookalike_ids if str(t).strip()]
        if lookalike_ids:
            payload["lookalike_organization_ids"] = lookalike_ids

    # Industries: Apollo accepts organization_industry_tag_ids and organization_not_industry_tag_ids (ID arrays).
    industry_ids = data.get("industries")
    if industry_ids:
        if isinstance(industry_ids, str):
            industry_ids = [s.strip() for s in industry_ids.split(",") if s.strip()]
        else:
            industry_ids = [str(i).strip() for i in industry_ids if str(i).strip()]
        if industry_ids:
            payload["organization_industry_tag_ids"] = industry_ids
    industry_exclude_ids = data.get("industries_exclude")
    if industry_exclude_ids:
        if isinstance(industry_exclude_ids, str):
            industry_exclude_ids = [
                s.strip() for s in industry_exclude_ids.split(",") if s.strip()
            ]
        else:
            industry_exclude_ids = [
                str(i).strip() for i in industry_exclude_ids if str(i).strip()
            ]
        if industry_exclude_ids:
            payload["organization_not_industry_tag_ids"] = industry_exclude_ids

    return payload


def normalize_people(people: list) -> list:
    """Normalize Apollo API response for people to consistent format for UI."""
    contacts = []
    for person in people:
        # Get phone numbers
        phone_numbers = []
        if person.get("phone_numbers"):
            phone_numbers = [
                p.get("sanitized_number") or p.get("raw_number")
                for p in person.get("phone_numbers", [])
                if p
            ]

        contacts.append(
            {
                "id": person.get("id"),
                "first_name": person.get("first_name"),
                "last_name": person.get("last_name"),
                "name": person.get("name")
                or f"{person.get('first_name', '')} {person.get('last_name', '')}".strip(),
                "email": person.get("email"),
                "title": person.get("title"),
                "seniority": person.get("seniority"),
                "city": person.get("city"),
                "state": person.get("state"),
                "country": person.get("country"),
                "linkedin_url": person.get("linkedin_url"),
                "phone_numbers": phone_numbers,
                "organization_name": (
                    person.get("organization", {}).get("name")
                    if person.get("organization")
                    else None
                ),
            }
        )
    return contacts


def build_people_payload(data: dict) -> dict:
    """
    Build Apollo API payload for people search (api_search endpoint).
    Seniorities use 'value' (e.g. c_suite, vp). Avoids params that cause 422 on deprecated /search.
    """
    payload = {
        "page": data.get("page", 1) or 1,
        "per_page": data.get("per_page", 25) or 25,
    }

    # Organization ID (ensure string for Apollo)
    org_id = data.get("organization_id")
    if org_id and str(org_id).strip():
        payload["organization_ids"] = [str(org_id).strip()]

    org_ids = data.get("organization_ids")
    if org_ids:
        org_ids_clean = [str(oid).strip() for oid in org_ids if str(oid).strip()]
        if org_ids_clean:
            payload["organization_ids"] = org_ids_clean

    # Domains (api_search accepts q_organization_domains_list)
    domains = data.get("domains")
    if domains:
        domain_list = [d.strip() for d in domains.split(",") if d.strip()]
        if domain_list:
            payload["q_organization_domains_list"] = domain_list

    # Job titles → person_titles (lowercase for Apollo mixed_people api_search)
    job_titles = data.get("job_titles")
    if job_titles:
        if isinstance(job_titles, str):
            job_titles = [job_titles]
        job_titles = [
            str(t).strip().lower() for t in job_titles if t and str(t).strip()
        ]
        if job_titles:
            payload["person_titles"] = job_titles

    # Seniorities → person_seniorities (value: c_suite, vp, owner, etc.)
    seniorities = data.get("seniorities")
    if seniorities:
        if isinstance(seniorities, str):
            seniorities = [seniorities]
        seniorities = [s for s in seniorities if s and str(s).strip()]
        if seniorities:
            payload["person_seniorities"] = seniorities

    return payload


def company_search_view(request):
    """
    View for searching companies via Apollo API.
    Shows filters form and results table.
    """
    form = CompanySearchForm()
    companies = None
    total_count = 0
    error = None

    if request.method == "POST":
        form = CompanySearchForm(request.POST)
        if form.is_valid():
            try:
                data = form.cleaned_data
                data.setdefault("page", 1)
                data.setdefault("per_page", 25)
                payload = build_apollo_payload(data)
                response = search_companies(payload)
                # Prefer organizations array; fallback to accounts
                organizations = response.get("organizations") or []
                accounts = response.get("accounts") or []
                raw_list = organizations if organizations else accounts
                companies = normalize_companies(raw_list)
                pagination = response.get("pagination", {})
                total_count = pagination.get("total_entries", len(companies))
                log_apollo_credits("POST / (company search)", CREDITS_COMPANY_SEARCH)
            except Exception as e:
                error = str(e)

    return render(
        request,
        "apollo_ingest/company_search.html",
        {
            "form": form,
            "companies": companies,
            "total_count": total_count,
            "error": error,
        },
    )


class CompanySearchAPIView(APIView):
    """API endpoint for searching companies via Apollo."""

    @extend_schema(
        request=CompanySearchSerializer,
        responses={200: CompanySearchResponseSerializer},
        description="Search for companies using various filters",
        tags=["Companies"],
    )
    def post(self, request):
        serializer = CompanySearchSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            data = dict(serializer.validated_data)
            data.setdefault("page", 1)
            data.setdefault("per_page", 25)
            payload = build_apollo_payload(data)
            response = search_companies(payload)
            organizations = response.get("organizations") or []
            accounts = response.get("accounts") or []
            raw_list = organizations if organizations else accounts
            companies = normalize_companies(raw_list)
            pagination = response.get("pagination", {})
            total_count = pagination.get("total_entries", len(companies))
            log_apollo_credits(
                request.path or "/api/companies/search/",
                CREDITS_COMPANY_SEARCH,
            )

            return Response(
                {
                    "companies": companies,
                    "total_count": total_count,
                    "page": pagination.get("page", 1),
                    "per_page": pagination.get("per_page", 25),
                }
            )
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TagsSearchAPIView(APIView):
    """
    Search Apollo tags (e.g. industry tags). Undocumented Apollo endpoint;
    use to get tag IDs for company search filter_expression (industry_tags).
    """

    @extend_schema(
        parameters=[
            {
                "name": "q",
                "in": "query",
                "required": True,
                "description": "Fuzzy search for tag name (e.g. software, banking)",
                "schema": {"type": "string"},
            }
        ],
        responses={200: {"description": "tags[] from Apollo"}},
        description="Search tags (industry etc.) to get IDs for filters. Uses Apollo undocumented POST /api/v1/tags/search",
        tags=["Companies"],
    )
    def get(self, request):
        q = (request.query_params.get("q") or "").strip()
        if not q:
            return Response(
                {"error": "Query param 'q' required (e.g. ?q=software)"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            data = search_tags(q)
            log_apollo_credits(
                request.path or "/api/tags/search/",
                CREDITS_TAGS_SEARCH,
            )
            return Response({"tags": data.get("tags", [])})
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def post(self, request):
        q = (request.data.get("q") or request.data.get("q_tag_fuzzy_name") or "").strip()
        if not q:
            return Response(
                {"error": "Body 'q' or 'q_tag_fuzzy_name' required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            data = search_tags(q)
            log_apollo_credits(
                request.path or "/api/tags/search/",
                CREDITS_TAGS_SEARCH,
            )
            return Response({"tags": data.get("tags", [])})
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PeopleSearchAPIView(APIView):
    """API endpoint for searching people/contacts via Apollo."""

    @extend_schema(
        request=PeopleSearchSerializer,
        responses={200: PeopleSearchResponseSerializer},
        description="Search for people/contacts using organization ID, domains, job titles, or seniorities",
        tags=["People"],
    )
    def post(self, request):
        serializer = PeopleSearchSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            payload = build_people_payload(serializer.validated_data)
            response = search_people(payload)

            # Apollo returns 'people' for people data (no email/linkedin from search)
            people = normalize_people(response.get("people", []))
            pagination = response.get("pagination", {})
            # Total count for badge & pagination (Apollo may use total_entries or total_count)
            total_count = (
                pagination.get("total_entries")
                or pagination.get("total_count")
                or response.get("total_entries")
                or response.get("total_count")
            )
            if total_count is None:
                total_count = 0

            # Enrich each person to get email, linkedin_url, etc. (consumes credits)
            ids = [p["id"] for p in people if p.get("id")]
            enrich_credits = 0
            if ids:
                enriched_by_id = enrich_people_bulk(ids)
                _merge_enriched_into_people(people, enriched_by_id)
                enrich_credits = len(ids) * CREDITS_ENRICH_PER_PERSON
            total_credits = CREDITS_PEOPLE_SEARCH + enrich_credits
            log_apollo_credits(
                request.path or "/api/people/search/",
                total_credits,
                detail=f"search=1 enrich={enrich_credits} ({len(ids)} contacts)",
            )

            return Response(
                {
                    "people": people,
                    "total_count": total_count,
                    "page": pagination.get("page", 1),
                    "per_page": pagination.get("per_page", 25),
                }
            )
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


def _merge_enriched_into_people(people: list, enriched_by_id: dict) -> None:
    """Merge enriched email, linkedin, seniority, location, phone into people in place."""
    for p in people:
        pid = p.get("id")
        if pid is None:
            continue
        key = str(pid)
        if key not in enriched_by_id:
            continue
        e = enriched_by_id[key]
        if e.get("email"):
            p["email"] = e.get("email")
        if e.get("linkedin_url"):
            p["linkedin_url"] = e.get("linkedin_url")
        if e.get("seniority"):
            p["seniority"] = e.get("seniority")
        if e.get("city") is not None:
            p["city"] = e.get("city")
        if e.get("state") is not None:
            p["state"] = e.get("state")
        if e.get("country") is not None:
            p["country"] = e.get("country")
        if e.get("phone_numbers"):
            p["phone_numbers"] = [
                ph.get("sanitized_number") or ph.get("raw_number")
                for ph in e.get("phone_numbers", [])
                if ph
            ]


def get_people_for_company(
    organization_id,
    domain,
    job_titles=None,
    seniorities=None,
    per_page=100,
):
    """
    Same flow as PeopleSearchAPIView / frontend loadContacts: people search + enrich.
    Returns list of normalized, enriched people for the given company.
    """
    payload = {
        "page": 1,
        "per_page": per_page,
        "organization_id": organization_id and str(organization_id).strip() or None,
        "domains": (domain or "").strip() or None,
        "job_titles": job_titles or [],
        "seniorities": seniorities or [],
    }
    people = []
    search_calls = 1
    try:
        response = search_people(build_people_payload(payload))
        people = normalize_people(response.get("people", []))
        if not people and (job_titles or seniorities):
            payload_no_filter = {
                "page": 1,
                "per_page": per_page,
                "organization_id": payload["organization_id"],
                "domains": payload["domains"],
                "job_titles": [],
                "seniorities": [],
            }
            response2 = search_people(build_people_payload(payload_no_filter))
            people = normalize_people(response2.get("people", []))
            search_calls = 2
    except Exception as e:
        logger.exception(
            "get_people_for_company failed for org_id=%s domain=%s: %s",
            organization_id,
            domain,
            e,
        )
        raise
    if people:
        ids = [p["id"] for p in people if p.get("id")]
        if ids:
            enriched_by_id = enrich_people_bulk(ids)
            _merge_enriched_into_people(people, enriched_by_id)
            enrich_credits = len(ids) * CREDITS_ENRICH_PER_PERSON
            search_credits = search_calls * CREDITS_PEOPLE_SEARCH
            total_credits = search_credits + enrich_credits
            log_apollo_credits(
                "get_people_for_company (org_id=%s)" % (organization_id or domain or "?"),
                total_credits,
                detail=f"search={search_calls} enrich={enrich_credits} ({len(ids)} contacts)",
            )
    return people


def _sanitize_filename(name: str, max_len: int = 200) -> str:
    """Remove chars invalid for filenames; truncate."""
    s = re.sub(r'[<>:"/\\|?*]', "", str(name).strip())
    return (s[:max_len] + "...") if len(s) > max_len else (s or "company")


@require_http_methods(["POST"])
@ensure_csrf_cookie
def export_companies_view(request):
    """
    Export selected companies as one Excel file per company (Name, Email, LinkedIn, Job Title, Seniority, Location),
    then return all files in a single ZIP download. Uses current job_titles and seniorities from request body.
    """
    import json

    try:
        body = json.loads(request.body)
    except Exception:
        return Response({"error": "Invalid JSON"}, status=status.HTTP_400_BAD_REQUEST)
    companies = body.get("companies") or []
    job_titles = body.get("job_titles") or []
    seniorities = body.get("seniorities") or []
    if not companies:
        return Response(
            {"error": "No companies selected"}, status=status.HTTP_400_BAD_REQUEST
        )
    # Export: use people[] from request if present (frontend called people/search per company); else fetch server-side
    log_apollo_credits(
        request.path or "/api/export/companies/",
        0,
        detail="per-company credits logged below when people are fetched",
    )
    logger.info("Export: request for %s company(ies)", len(companies))
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for c in companies:
            cid = c.get("id")
            cname = c.get("name") or "company"
            cdomain = (c.get("domain") or c.get("primary_domain") or "").strip()
            people = c.get("people") if isinstance(c.get("people"), list) else []
            if not people:
                try:
                    logger.info(
                        "Export: fetching people for company id=%s name=%s", cid, cname
                    )
                    people = get_people_for_company(
                        organization_id=cid,
                        domain=cdomain or None,
                        job_titles=job_titles,
                        seniorities=seniorities,
                        per_page=100,
                    )
                except Exception as e:
                    logger.warning(
                        "Export: skip company id=%s name=%s: %s", cid, cname, e
                    )
            wb = Workbook()
            ws = wb.active
            ws.title = "Contacts"
            ws.append(
                ["Name", "Email", "LinkedIn", "Job Title", "Seniority", "Location"]
            )
            for p in people:
                loc = (
                    ", ".join(
                        filter(None, [p.get("city"), p.get("state"), p.get("country")])
                    )
                    or ""
                )
                ws.append(
                    [
                        p.get("name") or "",
                        p.get("email") or "",
                        p.get("linkedin_url") or "",
                        p.get("title") or "",
                        p.get("seniority") or "",
                        loc,
                    ]
                )
            xlsx_buffer = io.BytesIO()
            wb.save(xlsx_buffer)
            xlsx_buffer.seek(0)
            safe_name = _sanitize_filename(cname) + ".xlsx"
            zf.writestr(safe_name, xlsx_buffer.getvalue())
    zip_buffer.seek(0)
    response = HttpResponse(zip_buffer.getvalue(), content_type="application/zip")
    response["Content-Disposition"] = 'attachment; filename="companies_export.zip"'
    return response

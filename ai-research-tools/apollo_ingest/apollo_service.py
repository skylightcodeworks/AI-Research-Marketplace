import os
import time
import requests

APOLLO_COMPANY_SEARCH_URL = "https://api.apollo.io/api/v1/mixed_companies/search"
# mixed_people/search is deprecated and can return 422; api_search is the supported endpoint.
APOLLO_PEOPLE_SEARCH_URL = "https://api.apollo.io/api/v1/mixed_people/api_search"
APOLLO_PEOPLE_BULK_ENRICH_URL = "https://api.apollo.io/api/v1/people/bulk_match"
# Undocumented: used to fetch industry/tag IDs for filters (e.g. industry_tags).
APOLLO_TAGS_SEARCH_URL = "https://app.apollo.io/api/v1/tags/search"

# Timeout in seconds (Apollo can be slow on large result sets). Override via APOLLO_REQUEST_TIMEOUT.
DEFAULT_TIMEOUT = int(os.getenv("APOLLO_REQUEST_TIMEOUT", "120"))
MAX_RETRIES = 2


def _get_headers():
    """Get headers for Apollo API requests."""
    api_key = os.getenv("APOLLO_API_KEY")
    if not api_key:
        raise RuntimeError("Missing APOLLO_API_KEY in environment")
    return {
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
        "X-Api-Key": api_key,
    }


def _post_with_retry(
    url: str, json: dict, headers: dict, timeout: int = DEFAULT_TIMEOUT
) -> requests.Response:
    """POST with retries on read/connect timeout."""
    last_error = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            r = requests.post(url, json=json, headers=headers, timeout=timeout)
            return r
        except (
            requests.exceptions.ReadTimeout,
            requests.exceptions.ConnectTimeout,
        ) as e:
            last_error = e
            if attempt < MAX_RETRIES:
                time.sleep(2)
            else:
                raise last_error
    raise last_error


def search_tags(q_tag_fuzzy_name: str) -> dict:
    """
    Search Apollo tags (e.g. industry tags). Undocumented endpoint; use to get tag IDs
    for filter_expression (e.g. industry_tags). Returns response with tags[].
    May consume credits depending on plan; primary credit use is search + bulk_match.
    """
    headers = _get_headers()
    params = {"q_tag_fuzzy_name": (q_tag_fuzzy_name or "").strip() or ""}
    r = requests.post(
        APOLLO_TAGS_SEARCH_URL,
        json={},
        params=params,
        headers=headers,
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def search_companies(payload: dict) -> dict:
    """Search for companies using Apollo API. Consumes Apollo credits."""
    headers = _get_headers()
    print(f"Apollo company search payload: {payload}")
    r = _post_with_retry(APOLLO_COMPANY_SEARCH_URL, payload, headers)
    # print(f"Apollo company search response: {r.json()}")
    if r.status_code == 422:
        try:
            err_body = r.json()
        except Exception:
            err_body = r.text
        raise RuntimeError(
            "Apollo company search 422 (invalid payload): %s" % (err_body,)
        )
    r.raise_for_status()
    return r.json()


def search_people(payload: dict) -> dict:
    """Search for people/contacts using Apollo API. Consumes Apollo credits."""
    headers = _get_headers()
    r = _post_with_retry(APOLLO_PEOPLE_SEARCH_URL, payload, headers)
    r.raise_for_status()
    return r.json()


def enrich_people_bulk(
    person_ids: list[str],
    reveal_personal_emails: bool = False,
    reveal_phone_number: bool = False,
) -> dict[str, dict]:
    """
    Enrich up to 10 people at a time via bulk_match. Returns dict of person_id -> enriched person (email, linkedin_url, etc.).
    Consumes credits. Skips empty ids; batches of 10.
    """
    if not person_ids:
        return {}
    ids_clean = [str(pid).strip() for pid in person_ids if str(pid).strip()]
    if not ids_clean:
        return {}
    result_by_id = {}
    for i in range(0, len(ids_clean), 10):
        batch = ids_clean[i : i + 10]
        payload = {"details": [{"id": pid} for pid in batch]}
        params = {
            "reveal_personal_emails": str(reveal_personal_emails).lower(),
            "reveal_phone_number": str(reveal_phone_number).lower(),
        }
        headers = _get_headers()
        try:
            r = requests.post(
                APOLLO_PEOPLE_BULK_ENRICH_URL,
                json=payload,
                params=params,
                headers=headers,
                timeout=30,
            )
            r.raise_for_status()
            data = r.json()
            for match in data.get("matches") or []:
                pid = match.get("id")
                if pid is not None:
                    result_by_id[str(pid)] = match
        except Exception:
            # Don't fail the whole flow if enrichment fails for a batch
            pass
    return result_by_id

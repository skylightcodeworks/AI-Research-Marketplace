"""
Default Apollo search filters (company + people) per ICP spec.
Used as form initial values and merged into API payloads.
"""

# Employee ranges: cap at 100 (exclude 500+)
DEFAULT_EMPLOYEE_RANGES = ["1,10", "11,50", "51,100"]

# Industry tag IDs (Apollo organization_industry_tag_ids)
DEFAULT_INDUSTRY_IDS = [
    "5567cd4e7369643b70010000",  # computer software
    "5567cd4d736964397e020000",  # internet
    "5567cd4773696439b10b0000",  # information technology & services
    "5567cd877369644cf94b0000",  # computer & network security
]

# Extra keywords (no exact Apollo industry tag for SaaS / AI / financial services)
DEFAULT_ORGANIZATION_KEYWORDS = [
    "Artificial Intelligence",
    "Financial Services",
]

DEFAULT_INDUSTRY_EXCLUDE_IDS = [
    "5567e09973696410db020800",  # staffing & recruiting
]

# Keyword excludes (management consulting not in industry list)
DEFAULT_ORGANIZATION_KEYWORD_EXCLUDE = [
    "Management Consulting",
]

DEFAULT_LOCATIONS_INCLUDED = "US, Canada, Saudia, EMEA"


def default_form_initial() -> dict:
    """Default values for CompanySearchForm (GET and after successful search)."""
    return {
        "locations_included": DEFAULT_LOCATIONS_INCLUDED,
        "employee_ranges": "; ".join(DEFAULT_EMPLOYEE_RANGES),
        "industries": list(DEFAULT_INDUSTRY_IDS),
        "industries_exclude": list(DEFAULT_INDUSTRY_EXCLUDE_IDS),
        "organization_keyword": ", ".join(DEFAULT_ORGANIZATION_KEYWORDS),
        "organization_keyword_exclude": ", ".join(DEFAULT_ORGANIZATION_KEYWORD_EXCLUDE),
        "funding_stages": ", ".join(DEFAULT_FUNDING_STAGES),
        "organization_job_titles": ", ".join(DEFAULT_ORG_JOB_TITLES),
        "job_titles": [t.lower() for t in DEFAULT_JOB_TITLES],
        "seniorities": list(DEFAULT_SENIORITIES),
        "page": 1,
        "per_page": 100,
    }


def cleaned_data_to_form_initial(data: dict) -> dict:
    """Map merged cleaned_data back to form initial for display."""
    initial = default_form_initial()
    for key in initial:
        if key in data and data[key] not in (None, "", []):
            initial[key] = data[key]
    return initial

# People search defaults
DEFAULT_JOB_TITLES = [
    "CEO",
    "Founder",
    "Co-Founder",
    "CTO",
    "VP Engineering",
    "Head of Engineering",
    "Head of Product",
    "VP Product",
    "Product Manager",
    "COO",
    "Operations Lead",
]

DEFAULT_SENIORITIES = [
    "c_suite",
    "founder",
    "vp",
    "director",
    "head",
]

# Funding stages (Apollo mixed_companies/search)
DEFAULT_FUNDING_STAGES = [
    "Pre-seed",
    "Seed",
    "Series A",
    "Series B",
]

# Hiring signal: active job postings by department (org job titles filter)
DEFAULT_ORG_JOB_TITLES = [
    "Engineering",
    "Product",
]

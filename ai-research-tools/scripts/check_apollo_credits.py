#!/usr/bin/env python3
"""
One-off: Search 100 companies via Apollo, then fetch people for top 10 via your API.
Reports Apollo credit usage (usage_stats) before/after each phase.

Usage:
  export APOLLO_API_KEY=your_key
  export API_BASE_URL=http://127.0.0.1:8000   # optional; your Django app
  python scripts/check_apollo_credits.py

Requires: requests (pip install requests)
"""

import json
import os
import sys

try:
    import requests
except ImportError:
    print("Install: pip install requests")
    sys.exit(1)

APOLLO_BASE = "https://api.apollo.io/api/v1"
APOLLO_KEY = os.environ.get("APOLLO_API_KEY")
API_BASE = os.environ.get("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")


def apollo_headers():
    if not APOLLO_KEY:
        print("Set APOLLO_API_KEY in environment")
        sys.exit(1)
    return {
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
        "X-Api-Key": APOLLO_KEY,
    }


def get_usage_stats():
    """Apollo usage stats (needs master API key; 403 if not)."""
    r = requests.post(
        f"{APOLLO_BASE}/usage_stats/api_usage_stats",
        headers=apollo_headers(),
        json={},
        timeout=15,
    )
    if r.status_code == 403:
        return None
    r.raise_for_status()
    return r.json()


def extract_consumed(stats, keys):
    """Get consumed for given endpoint keys. keys = list of [path, action]."""
    if not stats:
        return None
    out = {}
    for k in keys:
        key_str = json.dumps(k)
        if key_str in stats:
            out[key_str] = {
                "minute": stats[key_str].get("minute", {}).get("consumed"),
                "hour": stats[key_str].get("hour", {}).get("consumed"),
                "day": stats[key_str].get("day", {}).get("consumed"),
            }
    return out


def search_companies_apollo(per_page=100, page=1):
    """Search companies via Apollo (direct)."""
    r = requests.post(
        f"{APOLLO_BASE}/mixed_companies/search",
        headers=apollo_headers(),
        json={"page": page, "per_page": per_page},
        timeout=120,
    )
    r.raise_for_status()
    return r.json()


def login_your_api():
    """Login to your Django app; returns session with cookies."""
    import re
    s = requests.Session()
    s.headers["User-Agent"] = "ApolloCreditsCheck/1.0"
    r0 = s.get(f"{API_BASE}/login/", timeout=10)
    csrf = ""
    if "csrfmiddlewaretoken" in r0.text:
        m = re.search(r'name="csrfmiddlewaretoken"\s+value="([^"]+)"', r0.text)
        if m:
            csrf = m.group(1)
    if not csrf and "csrftoken" in s.cookies:
        csrf = s.cookies.get("csrftoken", "")
    r = s.post(
        f"{API_BASE}/login/",
        data={
            "username": "admin@skyapollo.com",
            "password": "skyapollo@admin123",
            "csrfmiddlewaretoken": csrf,
        },
        allow_redirects=True,
        timeout=10,
    )
    return s


def people_search_via_your_api(session, organization_id, per_page=25):
    """POST /api/people/search/ with organization_id. Sends CSRF from cookie."""
    csrf = session.cookies.get("csrftoken", "")
    r = session.post(
        f"{API_BASE}/api/people/search/",
        json={"organization_id": organization_id, "per_page": per_page},
        headers={
            "Content-Type": "application/json",
            "X-CSRFToken": csrf,
        },
        timeout=60,
    )
    return r


def main():
    print("=== Apollo credits check ===\n")
    print("Phase 1: Usage stats BEFORE (Apollo)")
    stats_before = get_usage_stats()
    keys_of_interest = [
        ["api/v1/mixed_companies", "search"],
        ["api/v1/mixed_people", "search"],
        ["api/v1/people", "bulk_match"],
    ]
    if stats_before:
        consumed_before = extract_consumed(stats_before, keys_of_interest)
        for k, v in (consumed_before or {}).items():
            print(f"  {k}: day={v.get('day')} hour={v.get('hour')} minute={v.get('minute')}")
    else:
        print("  (403 or error – need Apollo master API key for exact stats)\n")

    print("\nPhase 2: Apollo company search – 100 companies")
    try:
        company_res = search_companies_apollo(per_page=100, page=1)
    except Exception as e:
        print(f"  Error: {e}")
        sys.exit(1)
    orgs = company_res.get("organizations") or company_res.get("accounts") or []
    print(f"  Fetched {len(orgs)} companies")
    if not orgs:
        print("  No companies returned; check API key / plan.")
        sys.exit(1)

    stats_after_companies = get_usage_stats()
    if stats_after_companies:
        consumed_after = extract_consumed(stats_after_companies, [["api/v1/mixed_companies", "search"]])
        if consumed_after:
            k = list(consumed_after)[0]
            print(f"  mixed_companies/search consumed (day): {consumed_after[k].get('day')}")
    print("  → Typically 1 company search request = 1 credit (Apollo docs). So ~1 credit for this call.\n")

    top10 = orgs[:10]
    org_ids = []
    for o in top10:
        oid = o.get("id")
        if oid:
            org_ids.append(str(oid))
    print(f"  Top 10 organization IDs: {org_ids[:3]}... ({len(org_ids)} total)\n")

    print("Phase 3: Usage stats BEFORE people (Apollo)")
    stats_before_people = get_usage_stats()
    if stats_before_people:
        consumed = extract_consumed(stats_before_people, keys_of_interest)
        for k, v in (consumed or {}).items():
            print(f"  {k}: day={v.get('day')} hour={v.get('hour')} minute={v.get('minute')}")

    print("\nPhase 4: Your API – people/contacts for top 10 companies (curl-style)")
    try:
        sess = login_your_api()
    except Exception as e:
        print(f"  Login failed: {e}. Is Django running at {API_BASE}?")
        print("  Run: python manage.py runserver")
        sys.exit(1)

    for i, oid in enumerate(org_ids):
        r = people_search_via_your_api(sess, oid, per_page=25)
        if r.status_code == 200:
            data = r.json()
            total = data.get("total_count", 0)
            people = data.get("people", [])
            print(f"  Company {i+1} (id={oid}): {len(people)} people returned, total_count={total}")
        else:
            print(f"  Company {i+1} (id={oid}): HTTP {r.status_code}")

    print("\nPhase 5: Usage stats AFTER people (Apollo)")
    stats_after_people = get_usage_stats()
    if stats_after_people:
        consumed = extract_consumed(stats_after_people, keys_of_interest)
        for k, v in (consumed or {}).items():
            print(f"  {k}: day={v.get('day')} hour={v.get('hour')} minute={v.get('minute')}")

    print("\n--- Summary ---")
    print("1) 100 companies search (Apollo direct): usually 1 credit per request (this run = 1 call).")
    print("2) Your API (people for 10 companies): each call does search_people + enrich_people_bulk.")
    print("   So: 10 × (1 people search + 1 bulk_match for up to 25 people) → ~10 search + 10 enrich batches.")
    print("   Enrichment (bulk_match) consumes credits per contact; check usage_stats above for exact 'consumed'.")
    if not stats_after_people:
        print("   Set a master APOLLO_API_KEY to see exact consumed in usage_stats.")
    print("\nDone.")


if __name__ == "__main__":
    main()

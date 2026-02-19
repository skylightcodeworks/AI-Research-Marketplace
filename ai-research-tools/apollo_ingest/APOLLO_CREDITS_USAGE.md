# Apollo Credits / Connects – Where They’re Used in This App

## Credit-consuming Apollo endpoints used by this Django app

| Apollo endpoint | Our code | When it runs | Credits |
|-----------------|----------|--------------|--------|
| `POST /api/v1/mixed_companies/search` | `apollo_service.search_companies()` | Company search (UI + API) | Yes |
| `POST /api/v1/mixed_people/api_search` | `apollo_service.search_people()` | People search (UI + API + export) | Yes |
| `POST /api/v1/people/bulk_match` | `apollo_service.enrich_people_bulk()` | After people search / export (email, phone, etc.) | Yes (enrichment) |
| `POST https://app.apollo.io/api/v1/tags/search` | `apollo_service.search_tags()` | Tag/industry filter lookup | Check plan |

## Exact locations in code

### 1. Company search (consumes credits)

- **`apollo_ingest/views.py`**
  - **~316** – `company_search_view()` (POST): form submit → `search_companies(payload)`
  - **~358** – `CompanySearchAPIView.post()`: API → `search_companies(payload)`

### 2. People search (consumes credits)

- **`apollo_ingest/views.py`**
  - **~447** – `PeopleSearchAPIView.post()`: API → `search_people(payload)`
  - **~533** – `get_people_for_company()`: `search_people(build_people_payload(payload))`
  - **~544** – same helper: fallback `search_people(...)` when filters return no one

### 3. People enrichment – bulk_match (consumes credits)

- **`apollo_ingest/views.py`**
  - **~465** – `PeopleSearchAPIView.post()`: after people search → `enrich_people_bulk(ids)`
  - **~557** – `get_people_for_company()`: after people fetch → `enrich_people_bulk(ids)`
- **`apollo_ingest/apollo_service.py`**
  - **~94–134** – `enrich_people_bulk()`: calls `POST /api/v1/people/bulk_match` (batches of 10)

### 4. Tags search (for filter IDs – may or may not use credits)

- **`apollo_ingest/views.py`**
  - **~408** – `TagsSearchAPIView.get()`: `search_tags(q)`
  - **~423** – `TagsSearchAPIView.post()`: `search_tags(q)`
- **`apollo_ingest/apollo_service.py`**
  - **~49–65** – `search_tags()`: `POST https://app.apollo.io/api/v1/tags/search`

### 5. Export (companies → people → enrich)

- **`apollo_ingest/views.py`**
  - **~561 onwards** – `export_companies_view()`: for each company calls `get_people_for_company()` → `search_people` + `enrich_people_bulk`, so export uses both search and enrichment credits.

---

## Track usage with Apollo API (curl)

Apollo’s **View API Usage Stats** returns rate limits and **consumed** counts per endpoint (per minute/hour/day).  
**Note:** This endpoint needs a **master API key** (normal key returns 403).

```bash
# From project root, with APOLLO_API_KEY in env (e.g. from .env or venv)
cd ai-research-tools
source venv/bin/activate   # or: source .venv/bin/activate
export $(grep -v '^#' .env | xargs)   # load .env if you use it

curl -s -X POST "https://api.apollo.io/api/v1/usage_stats/api_usage_stats" \
  -H "Content-Type: application/json" \
  -H "Cache-Control: no-cache" \
  -H "X-Api-Key: $APOLLO_API_KEY" \
  -d '{}' | python3 -m json.tool
```

If you don’t use `.env`:

```bash
curl -s -X POST "https://api.apollo.io/api/v1/usage_stats/api_usage_stats" \
  -H "Content-Type: application/json" \
  -H "Cache-Control: no-cache" \
  -H "X-Api-Key: YOUR_MASTER_API_KEY" \
  -d '{}' | python3 -m json.tool
```

In the JSON response, look for keys that match what this app uses:

- **`["api/v1/mixed_companies", "search"]`** – company search
- **`["api/v1/mixed_people", "search"]`** – people search (may appear as `api_search` in docs)
- **`["api/v1/people", "bulk_match"]`** – people enrichment (connects/credits)

Each has `minute`, `hour`, `day` with `limit`, `consumed`, `left_over` so you can see where connects/credits are being used.

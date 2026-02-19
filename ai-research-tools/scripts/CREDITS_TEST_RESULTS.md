# Apollo credits test – 100 companies + top 10 people via your API

## Test run summary

### 1) Apollo se 100 companies search (direct)

- **Credits:** Usage stats: `mixed_companies/search` **day** 192 → **193** → **1 credit** is call pe.
- **Conclusion:** 100 companies ek hi request (`per_page=100`) = **1 credit**.

### 2) Tumhari API se top 10 companies ke people (curl / script)

- **Flow:** Login → 10 × `POST /api/people/search/` with `organization_id` (top 10 org IDs).
- **Is run me:** Saari 10 companies se **0 people** aaye (plan/data limit ho sakta hai).
- **Credits:**  
  - `mixed_people/search`: day=0 (0 people hone ki wajah se shayad call hi na ho ya count na chade).  
  - `people/bulk_match`: **minute** 0 → **3** (3 enrich batches chaley).
- **Conclusion:** Jab bhi API se people + enrich chalega: **har company = 1 people search + 1 (ya zyada) bulk_match**. Contacts jitne zyada (e.g. 25 per company), utne zyada **bulk_match** credits (enrichment).

---

## Curl se khud run karne ke liye

### Step 1: Usage stats (pehle – optional)

```bash
export APOLLO_API_KEY=your_master_key

curl -s -X POST "https://api.apollo.io/api/v1/usage_stats/api_usage_stats" \
  -H "Content-Type: application/json" \
  -H "Cache-Control: no-cache" \
  -H "X-Api-Key: $APOLLO_API_KEY" \
  -d '{}' | python3 -m json.tool
```

### Step 2: 100 companies search (Apollo direct)

```bash
curl -s -X POST "https://api.apollo.io/api/v1/mixed_companies/search" \
  -H "Content-Type: application/json" \
  -H "Cache-Control: no-cache" \
  -H "X-Api-Key: $APOLLO_API_KEY" \
  -d '{"page": 1, "per_page": 100}' | python3 -m json.tool > companies_100.json
```

Credits: is 1 call = **1 credit** (usage_stats me `mixed_companies/search` day +1).

### Step 3: Top 10 org IDs nikalna

```bash
# companies_100.json se first 10 org IDs (jq chahiye)
python3 -c "
import json
with open('companies_100.json') as f:
    d = json.load(f)
orgs = d.get('organizations') or d.get('accounts') or []
ids = [str(o['id']) for o in orgs[:10] if o.get('id')]
print(ids)
"
```

### Step 4: Login tumhari API par (session + CSRF)

```bash
API_BASE=http://127.0.0.1:8000   # ya apna Vercel URL

# Cookie file banao
curl -c cookies.txt -b cookies.txt -s "$API_BASE/login/" -o /dev/null
# CSRF nikalna (form me se) – ya next step me header me bhejna
curl -b cookies.txt -s "$API_BASE/login/" | grep -oP 'name="csrfmiddlewaretoken"\s+value="\K[^"]+' | head -1
```

Phir login POST (CSRF value upar wale grep se aayi):

```bash
CSRF=PASTE_CSRF_VALUE_HERE
curl -c cookies.txt -b cookies.txt -s -X POST "$API_BASE/login/" \
  -d "username=admin@skyapollo.com&password=skyapollo@admin123&csrfmiddlewaretoken=$CSRF" \
  -H "Referer: $API_BASE/login/" -L -o /dev/null
```

### Step 5: Ek company ke liye people (tumhari API by curl)

```bash
# CSRF cookie se (Django often sends in cookie)
CSRF=$(grep csrftoken cookies.txt | awk '{print $NF}')
ORG_ID=6499d53178c3930001e4b9cb   # companies_100 se koi bhi org id

curl -b cookies.txt -s -X POST "$API_BASE/api/people/search/" \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: $CSRF" \
  -H "Referer: $API_BASE/" \
  -d "{\"organization_id\": \"$ORG_ID\", \"per_page\": 25}" | python3 -m json.tool
```

Har aise **1** `POST /api/people/search/` = backend me **1× search_people + 1× enrich_people_bulk** (jab people milen) → **kitne credits** = Apollo usage_stats me `mixed_people/search` aur `people/bulk_match` ka **consumed** dekh lo.

### Step 6: Usage stats (baad me – credits verify)

Same as Step 1; diff dekh lo:

- `["api/v1/mixed_companies", "search"]` → company search credits.
- `["api/v1/mixed_people", "search"]` → people search credits.
- `["api/v1/people", "bulk_match"]` → enrichment (connects) credits.

---

## Short answers

| Action | Credits (is test ke hisaab se) |
|--------|--------------------------------|
| Apollo se 100 companies search (1 request) | **1 credit** |
| Tumhari API se 1 company ke people (1 POST /api/people/search/) | 1 people search + enrichment (contacts ke hisaab se bulk_match credits) |
| Tumhari API se top 10 companies ke people (10 calls) | 10 × people search + 10 × enrich; is run me bulk_match minute 3 tak gaya |

Apollo **master API key** se hi `usage_stats` theek aata hai; normal key pe 403 aata hai.

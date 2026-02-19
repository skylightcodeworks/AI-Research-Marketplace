# Credits kahan burn ho rahe hain (100 companies export)

## Vercel logs me kya dikhega

- **`====== /api/people/search/  Credits: N ======`** – har people search request pe (search=1 + enrich=contacts)
- **`====== POST / (company search)  Credits: 1 ======`** – jab 100 companies search karte ho (1 hi credit)
- **`====== /api/export/companies/  Credits: 0 ======`** – export API khud koi credit use nahi karti; detail me dikhega kitni companies pe server-side fetch hua

## 100 companies export flow

1. **Company search (1 credit)**  
   Pehle 100 companies search → 1 Apollo credit (`mixed_companies/search`).

2. **Export click**  
   Frontend **har selected company** ke liye **ek baar** `POST /api/people/search/` call karta hai (organization_id + filters).  
   - 100 companies = **100 calls** to `/api/people/search/`.  
   - Har call = **1 search + N enrich** (N = contacts, ab max 25 per company export ke liye).

3. **Credits formula (export)**  
   - Pehle: **per_page 100** → 100 × (1 + 100) = **10,100** tak ja sakta tha.  
   - Ab: **per_page 25** → 100 × (1 + 25) = **2,600** max (25 contacts per company).

4. **Double fetch kab hota tha (extra burn)**  
   - Jab org_id se 0 people aate the, frontend **dobara** domain se call karta tha → us company pe **2 search** credits.  
   - Export ke time **sirf export** ke liye naya fetch hota hai; UI me pehle load kiye hue contacts reuse nahi hote (design aisa hai).

## Kya change kiya (credits kam karne ke liye)

- **Export me `per_page` 100 → 25**  
  Export ke liye ab 25 contacts per company (frontend). Zyada chahiye ho to `company_search.html` me `exportPerPage = 25` badha sakte ho.

- **Export logs**  
  - Start: "X companies with people[] from request, Y will fetch server-side".  
  - End: "Export summary: X companies, Y server-side fetches".  
  Jab frontend companies + people bhejta hai to Y=0 (server-side fetch nahi, credits pehle hi frontend calls me use ho chuke).

## Summary

| Action              | Credits (estimated) |
|---------------------|----------------------|
| 100 companies search| 1                    |
| Export 100 companies (frontend 100× people/search, 25 contacts/company) | 100 × (1 + 25) = **2,600** |
| Export 100 companies (agar server-side fetch ho, per company 100 contacts) | 100 × (1 + 100) = **10,100** |

Extra burn kam karne ke liye: export me **per_page chota** rakho, aur Vercel logs me **`Credits: N`** line se dekh lo har request pe kitna use hua.

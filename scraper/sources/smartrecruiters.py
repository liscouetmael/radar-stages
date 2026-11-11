"""SmartRecruiters : https://api.smartrecruiters.com/v1/companies/<slug>/postings"""
from ..geo import country_from_name
from ..http import get_json
from ..text import html_to_text, is_internship

QUERIES = ["intern", "stage", "praktikum", "internship"]


def fetch_company(c, ctx):
    base = f"https://api.smartrecruiters.com/v1/companies/{c['slug']}/postings"
    seen, hits = set(), []
    for q in QUERIES:
        offset = 0
        while offset < 500:
            data = get_json(base, params={"q": q, "limit": 100, "offset": offset})
            for p in data.get("content", []):
                if p["id"] not in seen and is_internship(p.get("name", "")):
                    seen.add(p["id"])
                    hits.append(p)
            offset += 100
            if offset >= data.get("totalFound", 0):
                break

    out = []
    for p in hits[: ctx["max_details"]]:
        try:
            d = get_json(f"{base}/{p['id']}")
            secs = ((d.get("jobAd") or {}).get("sections") or {})
            desc = "\n\n".join(html_to_text((secs.get(k) or {}).get("text", ""))
                               for k in ("companyDescription", "jobDescription",
                                         "qualifications", "additionalInformation"))
        except Exception:
            desc = ""
        loc = p.get("location") or {}
        out.append({
            "id": f"sr-{c['slug']}-{p['id']}",
            "title": p["name"],
            "company": (p.get("company") or {}).get("name") or c["name"],
            "url": f"https://jobs.smartrecruiters.com/{c['slug']}/{p['id']}",
            "source": "SmartRecruiters",
            "location": ", ".join(x for x in (loc.get("city"), loc.get("region"),
                                              (loc.get("country") or "").upper()) if x),
            "country": (loc.get("country") or "").upper() or country_from_name(loc.get("country", "")),
            "remote": bool(loc.get("remote")),
            "posted": (p.get("releasedDate") or "")[:10],
            "description": desc,
            "sector_hint": (p.get("industry") or {}).get("label", ""),
            "company_sector": c.get("sector", ""),
        })
    return out

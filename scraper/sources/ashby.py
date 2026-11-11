"""Ashby : https://api.ashbyhq.com/posting-api/job-board/<slug>"""
from ..geo import country_from_name, guess_country
from ..http import get_json
from ..text import html_to_text, is_internship


def fetch_company(c, ctx):
    data = get_json(f"https://api.ashbyhq.com/posting-api/job-board/{c['slug']}")
    out = []
    for j in data.get("jobs", []):
        if not is_internship(j.get("title", ""), j.get("employmentType", "")):
            continue
        addr = ((j.get("address") or {}).get("postalAddress") or {})
        loc = j.get("location", "")
        country = country_from_name(addr.get("addressCountry", "")) or guess_country(loc)
        out.append({
            "id": f"ashby-{c['slug']}-{j['id']}",
            "title": j["title"],
            "company": c["name"],
            "url": j.get("jobUrl", ""),
            "source": "Ashby",
            "location": loc,
            "country": country,
            "remote": bool(j.get("isRemote")),
            "posted": (j.get("publishedAt") or "")[:10],
            "description": j.get("descriptionPlain") or html_to_text(j.get("descriptionHtml", "")),
            "company_sector": c.get("sector", ""),
        })
    return out

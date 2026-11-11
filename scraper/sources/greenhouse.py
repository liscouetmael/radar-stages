"""Greenhouse : https://boards-api.greenhouse.io/v1/boards/<slug>/jobs"""
from ..geo import guess_country
from ..http import get_json
from ..text import html_to_text, is_internship


def fetch_company(c, ctx):
    data = get_json(f"https://boards-api.greenhouse.io/v1/boards/{c['slug']}/jobs",
                    params={"content": "true"})
    out = []
    for j in data.get("jobs", []):
        if not is_internship(j.get("title", "")):
            continue
        loc = (j.get("location") or {}).get("name", "")
        out.append({
            "id": f"gh-{c['slug']}-{j['id']}",
            "title": j["title"],
            "company": c["name"],
            "url": j.get("absolute_url", ""),
            "source": "Greenhouse",
            "location": loc,
            "country": guess_country(loc),
            "remote": "remote" in loc.lower(),
            "posted": (j.get("first_published") or j.get("updated_at") or "")[:10],
            "description": html_to_text(j.get("content", "")),
            "company_sector": c.get("sector", ""),
        })
    return out

"""Workable : https://apply.workable.com/api/v1/widget/accounts/<slug>?details=true"""
from ..geo import country_from_name, guess_country
from ..http import get_json
from ..text import html_to_text, is_internship


def fetch_company(c, ctx):
    data = get_json(f"https://apply.workable.com/api/v1/widget/accounts/{c['slug']}",
                    params={"details": "true"})
    out = []
    for j in data.get("jobs", []):
        if not is_internship(j.get("title", ""), j.get("employment_type", "")):
            continue
        loc = ", ".join(x for x in (j.get("city"), j.get("country")) if x)
        out.append({
            "id": f"workable-{c['slug']}-{j['shortcode']}",
            "title": j["title"],
            "company": c["name"],
            "url": j.get("url") or j.get("shortlink", ""),
            "source": "Workable",
            "location": loc,
            "country": country_from_name(j.get("country", "")) or guess_country(loc),
            "remote": bool(j.get("telecommuting")),
            "posted": (j.get("published_on") or j.get("created_at") or "")[:10],
            "description": html_to_text(j.get("description", "")),
            "sector_hint": j.get("industry", ""),
            "company_sector": c.get("sector", ""),
        })
    return out

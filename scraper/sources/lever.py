"""Lever : https://api.lever.co/v0/postings/<slug>?mode=json"""
from datetime import datetime, timezone

from ..geo import country_from_name, guess_country
from ..http import get_json
from ..text import html_to_text, is_internship


def fetch_company(c, ctx):
    data = get_json(f"https://api.lever.co/v0/postings/{c['slug']}", params={"mode": "json"})
    out = []
    for j in data if isinstance(data, list) else []:
        cats = j.get("categories") or {}
        if not is_internship(j.get("text", ""), cats.get("commitment", "")):
            continue
        loc = cats.get("location", "") or ", ".join(cats.get("allLocations", []) or [])
        parts = [j.get("descriptionPlain", "")]
        for lst in j.get("lists", []) or []:
            parts += [lst.get("text", ""), lst.get("content", "")]
        parts.append(j.get("additionalPlain", ""))
        ts = j.get("createdAt")
        out.append({
            "id": f"lever-{c['slug']}-{j['id']}",
            "title": j["text"],
            "company": c["name"],
            "url": j.get("hostedUrl", ""),
            "source": "Lever",
            "location": loc,
            "country": country_from_name(j.get("country") or "") or guess_country(loc),
            "remote": j.get("workplaceType") == "remote",
            "posted": datetime.fromtimestamp(ts / 1000, timezone.utc).strftime("%Y-%m-%d") if ts else "",
            "description": html_to_text("\n".join(p for p in parts if p)),
            "company_sector": c.get("sector", ""),
        })
    return out

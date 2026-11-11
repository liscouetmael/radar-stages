"""Arbeitnow : API publique sans clé (Allemagne / Europe, souvent en anglais)."""
from datetime import datetime, timezone

from ..geo import guess_country
from ..http import get_json
from ..text import html_to_text, is_internship


def fetch(cfg, ctx):
    out = []
    for page in range(1, cfg.get("pages", 5) + 1):
        try:
            data = get_json("https://www.arbeitnow.com/api/job-board-api", params={"page": page})
        except Exception as e:
            print(f"  [arbeitnow] page {page}: {e}")
            break
        jobs = data.get("data", [])
        for j in jobs:
            if not is_internship(j.get("title", ""), " ".join(j.get("job_types") or [])):
                continue
            loc = j.get("location", "")
            ts = j.get("created_at")
            out.append({
                "id": f"arbeitnow-{j['slug']}",
                "title": j["title"],
                "company": j.get("company_name", ""),
                "url": j.get("url", ""),
                "source": "Arbeitnow",
                "location": loc,
                "country": guess_country(loc) or "DE",
                "remote": bool(j.get("remote")),
                "posted": datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d") if ts else "",
                "description": html_to_text(j.get("description", "")),
            })
        if not data.get("links", {}).get("next"):
            break
    return out

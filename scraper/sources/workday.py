"""Workday (Airbus, Thales, Sanofi...) :
POST https://<tenant>.<wd>.myworkdayjobs.com/wday/cxs/<tenant>/<site>/jobs"""
import re
from datetime import date, timedelta

from ..geo import country_from_name, guess_country
from ..http import get_json, post_json
from ..text import html_to_text, is_internship

QUERIES = ["intern", "stage", "internship", "praktikum"]
PAGE = 20


def _posted(s: str) -> str:
    """'Posted 3 Days Ago' / 'Posted Today' -> date ISO approximative."""
    s = (s or "").lower()
    if "today" in s or "aujourd" in s:
        return date.today().isoformat()
    if "yesterday" in s or "hier" in s:
        return (date.today() - timedelta(days=1)).isoformat()
    m = re.search(r"(\d+)\+?\s*day", s)
    if m:
        return (date.today() - timedelta(days=int(m.group(1)))).isoformat()
    return ""


def fetch_company(c, ctx):
    host = f"https://{c['tenant']}.{c['wd']}.myworkdayjobs.com"
    api = f"{host}/wday/cxs/{c['tenant']}/{c['site']}"
    seen, hits = set(), []
    for q in QUERIES:
        offset = 0
        while offset < 400 and len(hits) < ctx["max_details"]:
            data = post_json(f"{api}/jobs", {"appliedFacets": {}, "limit": PAGE,
                                             "offset": offset, "searchText": q})
            posts = data.get("jobPostings", [])
            for p in posts:
                path = p.get("externalPath")
                if path and path not in seen and is_internship(p.get("title", "")):
                    seen.add(path)
                    hits.append(p)
            offset += PAGE
            if not posts or offset >= data.get("total", 0):
                break

    out = []
    for p in hits[: ctx["max_details"]]:
        path = p["externalPath"]
        info = {}
        try:
            info = get_json(f"{api}{path}").get("jobPostingInfo", {})
        except Exception:
            pass
        loc = info.get("location") or p.get("locationsText", "")
        country = country_from_name((info.get("country") or {}).get("descriptor", "")) \
            or guess_country(loc)
        out.append({
            "id": f"wd-{c['tenant']}-{path.rsplit('_', 1)[-1]}",
            "title": p["title"],
            "company": c["name"],
            "url": info.get("externalUrl") or f"{host}/{c['site']}{path}",
            "source": "Workday",
            "location": loc,
            "country": country,
            "remote": "remote" in (info.get("remoteType") or "").lower(),
            "posted": info.get("startDate") or _posted(p.get("postedOn")),
            "description": html_to_text(info.get("jobDescription", "")),
            "company_sector": c.get("sector", ""),
        })
    return out

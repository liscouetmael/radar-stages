"""Workday (Airbus, Thales, Sanofi...) :
POST https://<tenant>.<wd>.myworkdayjobs.com/wday/cxs/<tenant>/<site>/jobs"""
import re
import time
from datetime import date, timedelta

import requests

from ..geo import country_from_name, guess_country
from ..http import get_json, post_json
from ..text import html_to_text, is_internship

QUERIES = ["intern", "stage", "internship", "praktikum"]
PAGE = 20
# Workday limite le débit par adresse IP : on espace les requêtes et, en cas de
# 429, on patiente avant de réessayer.
PAUSE = 1.0
WAITS = (30, 90)


def _call(fn, *a):
    for wait in (*WAITS, None):
        time.sleep(PAUSE)
        try:
            return fn(*a)
        except requests.exceptions.RetryError:
            if wait is None:
                raise
        except requests.HTTPError as e:
            if wait is None or e.response is None or e.response.status_code != 429:
                raise
        time.sleep(wait)


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


_FACET_YES = re.compile(r"intern|trainee|stagi|thesis|praktik|student", re.I)
_FACET_NO = re.compile(r"apprenti|professional contract|graduate|alternan", re.I)


def _intern_facet(api):
    """Identifiants des valeurs « stage » de la facette workerSubType (Job Type)."""
    data = _call(post_json, f"{api}/jobs", {"appliedFacets": {}, "limit": 1, "offset": 0,
                                            "searchText": ""})
    for f in data.get("facets", []):
        if f.get("facetParameter") == "workerSubType":
            return [v["id"] for v in f.get("values", [])
                    if _FACET_YES.search(v.get("descriptor", ""))
                    and not _FACET_NO.search(v.get("descriptor", ""))]
    return []


def fetch_company(c, ctx):
    host = f"https://{c['tenant']}.{c['wd']}.myworkdayjobs.com"
    api = f"{host}/wday/cxs/{c['tenant']}/{c['site']}"
    seen, hits = set(), []

    def scan(facets, q, trust):
        offset, total = 0, None
        while offset < 1000 and len(hits) < ctx["max_details"]:
            data = _call(post_json, f"{api}/jobs", {"appliedFacets": facets, "limit": PAGE,
                                                    "offset": offset, "searchText": q})
            posts = data.get("jobPostings", [])
            for p in posts:
                path = p.get("externalPath")
                if path and path not in seen and (trust or is_internship(p.get("title", ""))):
                    seen.add(path)
                    hits.append(p)
            offset += PAGE
            if total is None:  # Workday ne renvoie le total que sur la première page
                total = data.get("total") or 0
            if not posts or offset >= total:
                break

    # 1) filtre natif « Job Type » = stage : peu de requêtes et rien de raté
    ids = _intern_facet(api)
    if ids:
        scan({"workerSubType": ids}, "", True)
    else:  # 2) à défaut, recherche par mots-clés
        for q in QUERIES:
            scan({}, q, False)

    out = []
    for p in hits[: ctx["max_details"]]:
        path = p["externalPath"]
        oid = f"wd-{c['tenant']}-{path.rsplit('_', 1)[-1]}"
        known = ctx.get("previous", {}).get(oid)
        if known and known.get("description") and not ctx.get("refresh"):
            out.append(dict(known, _cached=True))   # fiche déjà connue : pas de requête
            continue
        info = {}
        try:
            info = _call(get_json, f"{api}{path}").get("jobPostingInfo", {})
        except Exception:
            pass
        loc = info.get("location") or p.get("locationsText", "")
        country = country_from_name((info.get("country") or {}).get("descriptor", "")) \
            or guess_country(loc)
        out.append({
            "id": oid,
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

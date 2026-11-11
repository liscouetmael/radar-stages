"""Adzuna : moteur d'agrégation multi-pays (reprend des offres de nombreux job
boards). Clé gratuite sur https://developer.adzuna.com.
Secrets requis : ADZUNA_APP_ID, ADZUNA_APP_KEY.
Note : l'API ne renvoie qu'un extrait de description (~500 caractères)."""
import os
import time

from ..geo import ADZUNA_COUNTRY, guess_country
from ..http import get_json
from ..text import is_internship

FRENCH = {"fr", "be"}


def fetch(cfg, ctx):
    app_id, app_key = os.environ.get("ADZUNA_APP_ID"), os.environ.get("ADZUNA_APP_KEY")
    if not (app_id and app_key):
        print("  [adzuna] clés absentes, source ignorée")
        return []
    out, seen = [], set()
    for cc, words in cfg.get("countries", {}).items():
        terms = ctx["search_terms"] if cc in FRENCH else ctx["search_terms_en"]
        for w in words:
            # Avec des mots-clés métier, on n'interroge que "stage + mot-clé"
            # (quota gratuit limité) ; sinon la recherche générique.
            for q in ([f"{w} {t}" for t in terms] or [w]):
                for page in range(1, cfg.get("pages_per_query", 2) + 1):
                    time.sleep(2.5)  # quota Adzuna : 25 requêtes / minute
                    try:
                        data = get_json(f"https://api.adzuna.com/v1/api/jobs/{cc}/search/{page}", params={
                            "app_id": app_id, "app_key": app_key, "what": q,
                            "results_per_page": 50, "max_days_old": ctx["max_age_days"],
                            "content-type": "application/json"})
                    except Exception as e:
                        print(f"  [adzuna] {cc} '{q}' p{page}: {e}")
                        break
                    res = data.get("results", [])
                    for j in res:
                        if j["id"] in seen or not is_internship(j.get("title", ""), j.get("contract_type", "")):
                            continue
                        seen.add(j["id"])
                        loc = (j.get("location") or {}).get("display_name", "")
                        out.append({
                            "id": f"adz-{j['id']}",
                            "title": j.get("title", "").replace("<strong>", "").replace("</strong>", ""),
                            "company": (j.get("company") or {}).get("display_name", "") or "—",
                            "url": j.get("redirect_url", ""),
                            "source": "Adzuna",
                            "location": loc,
                            "country": ADZUNA_COUNTRY.get(cc) or guess_country(loc),
                            "remote": False,
                            "posted": (j.get("created") or "")[:10],
                            "description": j.get("description", ""),
                            "sector_hint": (j.get("category") or {}).get("label", ""),
                        })
                    if len(res) < 50:
                        break
    return out

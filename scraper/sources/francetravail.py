"""France Travail (ex Pôle emploi) - API "Offres d'emploi v2".
Agrège aussi des offres de sites partenaires. Inscription gratuite sur
https://francetravail.io -> créer une application -> API "Offres d'emploi v2".
Secrets requis : FT_CLIENT_ID, FT_CLIENT_SECRET."""
import os

from ..http import get_json, session
from ..text import is_internship

TOKEN_URL = "https://entreprise.francetravail.fr/connexion/oauth2/access_token?realm=%2Fpartenaire"
SEARCH_URL = "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search"


def _token():
    r = session().post(TOKEN_URL, data={
        "grant_type": "client_credentials",
        "client_id": os.environ["FT_CLIENT_ID"],
        "client_secret": os.environ["FT_CLIENT_SECRET"],
        "scope": "api_offresdemploiv2 o2dsoffre",
    }, timeout=25)
    r.raise_for_status()
    return r.json()["access_token"]


def fetch(cfg, ctx):
    if not (os.environ.get("FT_CLIENT_ID") and os.environ.get("FT_CLIENT_SECRET")):
        print("  [france travail] clés absentes, source ignorée")
        return []
    headers = {"Authorization": f"Bearer {_token()}"}
    queries = ["stage"] + [f"stage {t}" for t in ctx["search_terms"]]
    out, seen = [], set()
    for q in queries:
        for start in range(0, 1050, 150):  # l'API limite à 1150 résultats
            try:
                data = get_json(SEARCH_URL, headers=headers, params={
                    "motsCles": q, "range": f"{start}-{start + 149}", "publieeDepuis": 31})
            except Exception as e:  # 204 = plus de résultats, 206 = partiel
                print(f"  [france travail] {q} {start}: {e}")
                break
            res = data.get("resultats", []) if isinstance(data, dict) else []
            for o in res:
                if o["id"] in seen:
                    continue
                if not is_internship(o.get("intitule", ""), o.get("typeContratLibelle", "")) \
                        and "stage" not in (o.get("description", "") or "").lower()[:300]:
                    continue
                seen.add(o["id"])
                lieu = o.get("lieuTravail") or {}
                origine = o.get("origineOffre") or {}
                out.append({
                    "id": f"ft-{o['id']}",
                    "title": o.get("intitule", ""),
                    "company": (o.get("entreprise") or {}).get("nom") or "Entreprise non communiquée",
                    "url": origine.get("urlOrigine")
                    or f"https://candidat.francetravail.fr/offres/recherche/detail/{o['id']}",
                    "source": "France Travail",
                    "location": lieu.get("libelle", ""),
                    "country": "FR",
                    "remote": False,
                    "posted": (o.get("dateCreation") or "")[:10],
                    "description": o.get("description", ""),
                    "sector_hint": o.get("secteurActiviteLibelle", ""),
                })
            if len(res) < 150:
                break
    return out

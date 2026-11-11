"""Point d'entrée : collecte toutes les sources, enrichit, déduplique et écrit
docs/data/offers.json (lu par le site).

    python -m scraper.main                 # tout
    python -m scraper.main --only ashby    # une seule source (debug)
"""
import argparse
import json
import re
import sys
import traceback
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import yaml

from .enrich import enrich
from .sources import ALL
from .text import norm, truncate

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "data" / "offers.json"
COMPANY_SOURCES = ("talentsoft", "workday", "greenhouse", "lever", "ashby",
                   "smartrecruiters", "workable")
AGGREGATORS = ("francetravail", "adzuna", "arbeitnow")


def load_previous():
    """Offres de la collecte précédente, par identifiant."""
    try:
        return {o["id"]: o for o in json.loads(OUT.read_text(encoding="utf-8")).get("offers", [])}
    except Exception:
        return {}


def collect(cfg, only=None, previous=None, refresh=False):
    previous = previous or {}
    ctx = {
        "previous": previous,
        "refresh": refresh,
        "search_terms": [t for t in cfg.get("search_terms") or [] if t],
        "search_terms_en": [t for t in cfg.get("search_terms_en") or cfg.get("search_terms") or [] if t],
        "max_age_days": cfg.get("max_age_days", 120),
        "max_details": cfg.get("max_details_per_company", 120),
    }
    offers, stats, errors = [], {}, []

    def run(label, fn):
        try:
            got = fn()
            for o in got:
                o["src"] = label
            print(f"  {label:40s} {len(got):4d} stages")
            stats[label] = len(got)
        except Exception as e:
            # Source en panne : on garde ses offres de la veille plutôt que de
            # les faire disparaître du site.
            got = [dict(o, _cached=True) for o in previous.values() if o.get("src") == label]
            print(f"  {label:40s} ERREUR {e} ({len(got)} offres conservées)")
            errors.append(f"{label}: {e}")
        offers.extend(got)

    for name in COMPANY_SOURCES:
        if only and name not in only:
            continue
        for c in (cfg.get("companies") or {}).get(name, []) or []:
            run(f"{name}:{c.get('name')}", lambda: ALL[name].fetch_company(c, ctx))

    for name in AGGREGATORS:
        if only and name not in only:
            continue
        scfg = cfg.get(name) or {}
        if not scfg.get("enabled", True):
            continue
        run(name, lambda: ALL[name].fetch(scfg, ctx))
    return offers, stats, errors


_GENDER = re.compile(r"\((?:h/f|f/h|m/w/d|m/f/d|w/m/d|f/m/d|h/f/x|all gender|m/f|f/m|x/f/h)\)|"
                     r"\b(?:h/f|f/h|m/w/d|m/f/d|w/m/d)\b|all gender")


def dedupe(offers):
    seen, out = set(), []
    for o in offers:
        title = _GENDER.sub("", norm(o["title"]))
        key = (norm(o["company"]), re.sub(r"[^a-z0-9]", "", title), o.get("country", ""))
        if key in seen or o["id"] in seen:
            continue
        seen.add(key)
        seen.add(o["id"])
        out.append(o)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", help="sources à exécuter (debug)")
    ap.add_argument("--config", default=str(Path(__file__).parent / "config.yaml"))
    ap.add_argument("--refresh", action="store_true",
                    help="retélécharge aussi les fiches déjà connues (fait d'office le dimanche)")
    args = ap.parse_args(argv)

    cfg = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    home = cfg.get("home_country", "FR")
    previous = load_previous()
    refresh = args.refresh or date.today().weekday() == 6
    print("Collecte des offres…" + (" (rafraîchissement complet)" if refresh else ""))
    offers, stats, errors = collect(cfg, args.only, previous, refresh)

    today = date.today().isoformat()
    cutoff = (date.today() - timedelta(days=cfg.get("max_age_days", 120))).isoformat()
    maxlen = cfg.get("max_description_chars", 3500)
    excluded = {norm(c) for c in cfg.get("excluded_companies") or []}
    final = []
    for o in dedupe(offers):
        if norm(o["company"]) in excluded:
            continue
        if o.pop("_cached", False):
            # fiche reprise telle quelle de la collecte précédente (déjà enrichie)
            final.append(o)
            continue
        # Date de première apparition, pour les sources qui ne datent pas leurs offres.
        old = previous.get(o["id"]) or {}
        o["first_seen"] = old.get("first_seen") or old.get("posted") or today
        if not o.get("posted"):
            o["posted"] = o["first_seen"]
            o["posted_estimated"] = True
        elif o["posted"] < cutoff:
            continue  # une offre sans date réelle reste tant qu'elle est en ligne
        # On analyse le texte COMPLET (les conditions d'éligibilité sont souvent
        # tout en bas de l'offre), puis on tronque ce qui est stocké.
        o["description"] = (o.get("description") or "").strip()
        enrich(o, home)
        o["description"] = truncate(o["description"], maxlen)
        final.append(o)
    final.sort(key=lambda o: o.get("posted") or "", reverse=True)

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "home_country": home,
        "count": len(final),
        "stats": stats,
        "errors": errors,
        "offers": final,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"\n{len(final)} offres écrites dans {OUT.relative_to(ROOT)}")
    if errors:
        print(f"{len(errors)} source(s) en erreur :", *errors, sep="\n  - ")
    # On n'échoue que si absolument rien n'a été collecté.
    return 0 if final else 1


if __name__ == "__main__":
    sys.exit(main())

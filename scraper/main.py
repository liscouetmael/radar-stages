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


def collect(cfg, only=None):
    ctx = {
        "search_terms": [t for t in cfg.get("search_terms") or [] if t],
        "search_terms_en": [t for t in cfg.get("search_terms_en") or cfg.get("search_terms") or [] if t],
        "max_age_days": cfg.get("max_age_days", 120),
        "max_details": cfg.get("max_details_per_company", 120),
    }
    offers, stats, errors = [], {}, []

    for name in COMPANY_SOURCES:
        if only and name not in only:
            continue
        for c in (cfg.get("companies") or {}).get(name, []) or []:
            label = f"{name}:{c.get('name')}"
            try:
                got = ALL[name].fetch_company(c, ctx)
                print(f"  {label:40s} {len(got):4d} stages")
                offers += got
                stats[label] = len(got)
            except Exception as e:
                print(f"  {label:40s} ERREUR {e}")
                errors.append(f"{label}: {e}")

    for name in AGGREGATORS:
        if only and name not in only:
            continue
        scfg = cfg.get(name) or {}
        if not scfg.get("enabled", True):
            continue
        try:
            got = ALL[name].fetch(scfg, ctx)
            print(f"  {name:40s} {len(got):4d} stages")
            offers += got
            stats[name] = len(got)
        except Exception as e:
            traceback.print_exc()
            errors.append(f"{name}: {e}")
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
    args = ap.parse_args(argv)

    cfg = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    home = cfg.get("home_country", "FR")
    print("Collecte des offres…")
    offers, stats, errors = collect(cfg, args.only)

    # Date de première apparition, pour les sources qui ne datent pas leurs offres.
    previous = {}
    if OUT.exists():
        try:
            for o in json.loads(OUT.read_text(encoding="utf-8")).get("offers", []):
                previous[o["id"]] = o.get("first_seen") or o.get("posted") or ""
        except Exception:
            pass
    today = date.today().isoformat()

    cutoff = (date.today() - timedelta(days=cfg.get("max_age_days", 120))).isoformat()
    maxlen = cfg.get("max_description_chars", 3500)
    final = []
    for o in dedupe(offers):
        o["first_seen"] = previous.get(o["id"]) or today
        if not o.get("posted"):
            o["posted"] = o["first_seen"]
            o["posted_estimated"] = True
        if o["posted"] < cutoff:
            continue
        o["description"] = truncate((o.get("description") or "").strip(), maxlen)
        final.append(enrich(o, home))
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

"""Talentsoft / Cegid (CEA, IRSN…) : pages HTML publiques du site carrière.
Le filtre "Stage" est détecté automatiquement parmi les types de contrat.
Ces sites n'indiquent pas de date de publication : main.py utilise la date
de première apparition de l'offre."""
import html
import time
import re

from ..geo import guess_country
from ..http import session
from ..text import html_to_text

UA_HEADERS = {"Accept": "text/html,application/xhtml+xml"}
_LINK = re.compile(r'class="ts-offer-card__title-link[^"]*"\s+href="(/offre-de-emploi/emploi-[^"]+_(\d+)\.aspx)"'
                   r'\s+title="([^"]*)"')
_CARD_INFO = re.compile(r'<ul class="ts-offer-card-content__list[^"]*">(.*?)</ul>', re.S)
_STAGE_FACET = re.compile(r'(facet_\w*Contract=\d+)" title="[^"]*:\s*([^"(]*stage[^"(]*)\((\d+)\)"', re.I)


def _get(url, **params):
    time.sleep(0.3)
    r = session().get(url, params=params or None, headers=UA_HEADERS, timeout=30)
    r.raise_for_status()
    return r.text


def fetch_company(c, ctx):
    base = c["base"].rstrip("/")
    listing = f"{base}/offre-de-emploi/liste-offres.aspx"
    first = _get(listing)
    m = _STAGE_FACET.search(first)
    if not m:
        raise RuntimeError("filtre 'Stage' introuvable")
    facet_key, facet_val = m.group(1).split("=")
    page_html = _get(listing, changefacet=1, **{facet_key: facet_val})
    total = int(m.group(3))

    cards, page = {}, 1
    while True:
        found = 0
        links = _LINK.findall(page_html)
        infos = _CARD_INFO.findall(page_html)
        for i, (path, oid, title_attr) in enumerate(links):
            if oid in cards:
                continue
            info = [html.unescape(re.sub(r"<[^>]+>", "", x)).strip()
                    for x in re.findall(r"<li[^>]*>(.*?)</li>", infos[i] if i < len(infos) else "", re.S)]
            cards[oid] = (path, html.unescape(title_attr), info)
            found += 1
        page += 1
        if not found or len(cards) >= total or page > 80:
            break
        page_html = _get(listing, page=page, LCID=1036)

    out = []
    limit = c.get("max_offers", 600)
    for oid, (path, title_attr, info) in list(cards.items())[:limit]:
        # Fiche déjà connue : on ne retélécharge pas sa page (une requête par
        # offre), sauf lors du rafraîchissement complet hebdomadaire.
        known = ctx.get("previous", {}).get(f"ts-{c['name'].lower()}-{oid}")
        if known and not ctx.get("refresh"):
            out.append(dict(known, _cached=True))
            continue
        # title attr : "Intitulé (Réf. : 2026-42240) - Domaine"
        tm = re.match(r"\s*(.*?)\s*\(R[ée]f\.? : [^)]*\)\s*(?:-\s*(.*))?$", title_attr)
        title, domain = (tm.group(1), tm.group(2) or "") if tm else (title_attr, "")
        loc = " ".join(x for x in info[2:] if x) if len(info) > 2 else ""
        desc = ""
        try:
            d = _get(base + path)
            a = d.find("ts-offer-page__content-details")
            b = d.find("ts-offer-page__cta is-bottom", a)
            if a > 0:
                desc = html_to_text(d[a:b if b > a else a + 20000].split(">", 1)[-1])
                # saute la présentation générique de l'organisme
                k = desc.find("Description du poste")
                if k > 0:
                    desc = desc[k:]
        except Exception:
            pass
        out.append({
            "id": f"ts-{c['name'].lower()}-{oid}",
            "title": title,
            "company": c["name"],
            "url": base + path,
            "source": "Site carrière",
            "location": loc,
            "country": guess_country(loc) or c.get("country", "FR"),
            "remote": False,
            "posted": "",
            "description": (f"Domaine : {domain}\n\n" if domain else "") + desc,
            "company_sector": c.get("sector", ""),
        })
    return out

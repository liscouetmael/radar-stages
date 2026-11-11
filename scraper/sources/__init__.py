"""Chaque source expose `fetch(cfg, ctx) -> list[dict]`.

Format d'une offre brute :
    id, title, company, url, source, location, country (ISO-2 ou ""),
    remote (bool), posted ("YYYY-MM-DD" ou ""), description (texte brut),
    sector_hint (secteur fourni par la source), company_sector (secteur config)
"""
from . import (adzuna, arbeitnow, ashby, francetravail, greenhouse, lever,
               talentsoft, workable,
               smartrecruiters, workday)

ALL = {
    "workday": workday,
    "greenhouse": greenhouse,
    "lever": lever,
    "ashby": ashby,
    "smartrecruiters": smartrecruiters,
    "workable": workable,
    "talentsoft": talentsoft,
    "francetravail": francetravail,
    "adzuna": adzuna,
    "arbeitnow": arbeitnow,
}

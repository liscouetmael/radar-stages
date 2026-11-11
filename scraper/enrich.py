"""Enrichissement des offres : secteur, césure, éligibilité des étudiants
étrangers, durée. Tout est basé sur des règles transparentes : l'extrait de
texte qui a déclenché la décision est conservé pour que l'utilisateur puisse
vérifier lui-même."""
import re

from .text import norm

# ---------------------------------------------------------------------------
#  Secteurs
# ---------------------------------------------------------------------------
SECTORS = {
    "Recherche publique": ["recherche publique", "public research", "laboratoire",
                           "research institute", "organisme de recherche"],
    "Quantique": ["quantum", "quantique", "qubit"],
    "Nucléaire & Fusion": ["nucleaire", "nuclear", "fusion", "radioprotection",
                           "neutron", "reacteur"],
    "Spatial & Astrophysique": ["spatial", "space", " astro", "satellite", "lanceur",
                                "launcher", "rocket"],
    "Aéronautique & Défense": ["aero", "aeronaut", "aerospace", "defense", "defence",
                               "aviation", "luft- und raumfahrt"],
    "Tech & Logiciel": ["informatique", "logiciel", "software", "it ", "tech",
                        "internet", "saas", "numerique", "digital", "telecom",
                        "semiconductor", "cloud", "information technology",
                        "programmation", "edition de logiciel"],
    "Finance & Banque": ["banque", "bank", "finance", "financ", "assurance",
                         "insurance", "fintech", "accounting", "comptab", "audit"],
    "Conseil": ["conseil", "consulting", "consultancy", "strategy"],
    "Santé & Pharma": ["sante", "health", "pharma", "medical", "biotech",
                       "hopital", "hospital ", "life science"],
    "Énergie & Environnement": ["energie", "energy", "oil", "gas", "petrol",
                                "electricit", "renewable", "environnement",
                                "environment", "water"],
    "Industrie & Automobile": ["industrie", "industr", "automobile", "automotive",
                               "manufactur", "mecanique", "engineering",
                               "ingenierie", "chimie", "chemical", "construction",
                               "btp", "metallurg"],
    "Commerce & Distribution": ["commerce", "retail", "distribution", "e-commerce",
                                "vente", "sales", "grande distribution"],
    "Luxe, Mode & Cosmétique": ["luxe", "luxury", "mode", "fashion", "cosmet",
                                "beaute", "beauty"],
    "Agroalimentaire": ["agroalimentaire", "food", "alimentaire", "agricult",
                        "beverage", "boisson"],
    "Transport & Logistique": ["transport", "logisti", "supply chain", "ferroviaire",
                               "rail", "shipping", "maritime"],
    "Médias & Divertissement": ["media", "jeu video", "video game", "gaming",
                                "entertainment", "divertissement", "presse",
                                "publicite", "advertising"],
    "Tourisme & Hôtellerie": ["tourisme", "tourism", "hotel", "hospitality",
                              "restauration", "travel"],
    "Public, Recherche & ONG": ["public", "administration", "recherche", "research",
                                "ong", "ngo", "association", "education",
                                "enseignement", "government"],
    "Immobilier": ["immobilier", "real estate"],
    "RH & Recrutement": ["ressources humaines", "human resources", "recrutement",
                         "recruitment", "staffing", "interim"],
}


def normalize_sector(*hints: str) -> str:
    for h in hints:
        if not h:
            continue
        if h in SECTORS:
            return h
        n = " " + norm(h) + " "
        for sector, keys in SECTORS.items():
            if any(k in n for k in keys):
                return sector
    return "Autre"


# ---------------------------------------------------------------------------
#  Césure
# ---------------------------------------------------------------------------
_CESURE_YES = re.compile(
    r"(cesure|gap[- ]year|annee de cesure|stage de cesure|cesure acceptee|"
    r"pre[- ]?(?:final|last)[- ]year|cesure possible)")
_CESURE_NO = re.compile(
    r"(pas de cesure|hors cesure|cesure non|uniquement (?:en |un )?(?:stage de )?fin d.etudes|"
    r"exclusivement (?:en )?fin d.etudes|stage de fin d.etudes obligatoire|"
    r"final[- ]year students only|must be in (?:your|their) final year|"
    r"derniere annee (?:d.etudes )?(?:uniquement|obligatoire))")
_FIN_ETUDES = re.compile(r"(fin d.etudes|final[- ]year|end[- ]of[- ]studies|"
                         r"abschlussarbeit|masterarbeit|tfe|pfe)")


def detect_cesure(text_n: str):
    """Renvoie ('yes'|'no'|'unknown', extrait)."""
    m = _CESURE_NO.search(text_n)
    if m:
        return "no", _snippet(text_n, m)
    m = _CESURE_YES.search(text_n)
    if m:
        return "yes", _snippet(text_n, m)
    m = _FIN_ETUDES.search(text_n)
    if m:
        # Mentionne "fin d'études" sans parler de césure : probablement réservé
        # aux fins d'études, mais pas certain.
        return "fin_etudes", _snippet(text_n, m)
    return "unknown", ""


# ---------------------------------------------------------------------------
#  Éligibilité des étudiants inscrits dans une école étrangère
# ---------------------------------------------------------------------------
_LOCAL = (r"(?:u\.?s\.?|us|american|united states|uk|u\.k\.|british|canadian|"
          r"german|deutschen|dutch|spanish|italian|swiss|irish|australian|"
          r"singapore(?:an)?|local|chinese|japanese|indian|belgian)")

_FOREIGN_KO = [
    rf"(?:currently |actively )?enrolled (?:in|at) an? {_LOCAL}[a-z ]{{0,30}}(?:university|college|institution|school|programme|program)",
    rf"(?:student|enrolled|enrollment)[a-z ,]{{0,40}}(?:university|college|school) (?:in|within) the (?:u\.?s\.?|united states|uk|united kingdom|netherlands)",
    r"(?:must|need to|required to) (?:be )?(?:currently )?(?:enrolled|studying) (?:in|at) (?:a |an )?(?:university|college|school) (?:in|located in|based in) (?!any)",
    r"(?:authori[sz]ed|eligible|permitted|right) to work in the (?:u\.?s\.?|united states|uk|united kingdom|us)[a-z ,]{0,40}without[a-z ]{0,20}sponsorship",
    r"(?:will not|won.t|cannot|can.t|unable to|do not|does not|not able to) (?:provide |offer )?(?:visa |immigration )?sponsor",
    r"no (?:visa |immigration )?sponsorship",
    r"sponsorship (?:is )?not (?:available|provided|offered)",
    r"(?:must|need to) (?:have|hold) (?:the |a )?(?:valid )?(?:right|authori[sz]ation|permit) to work in",
    r"(?:u\.?s\.? citizen(?:ship)?|us person|green card|permanent resident(?:s|cy)?) (?:is |are )?required",
    r"must be a (?:u\.?s\.?|us|uk|canadian|australian) (?:citizen|national|resident)",
    r"security clearance",
    r"(?:immatrikuliert|eingeschrieben) an einer deutschen (?:hochschule|universitat|fachhochschule)",
    r"(?:student|studierende)[a-z ]{0,30}einer deutschen (?:hochschule|universitat)",
    r"ingeschreven (?:aan|bij) een nederlandse",
    r"\bcpt\b|\bopt eligib|\bf-1 (?:students|visa)",
    r"returning to (?:school|university) (?:in|after)[a-z ]{0,20}(?:fall|autumn)",
    r"canadian (?:post-secondary|university|college) (?:student|institution)",
    r"co-?op (?:program|student|term)",
]
_FOREIGN_OK = [
    r"international students? (?:are |is )?(?:welcome|encouraged|eligible|accepted)",
    r"(?:open|available) to (?:all |international )?students (?:from|of|at|in) (?:any|all|international|foreign|european)",
    r"students (?:from|of) (?:any|all) (?:universit|countr|nationalit|school)",
    r"(?:visa|immigration|work permit) (?:sponsorship|support|assistance) (?:is |will be |can be )?(?:available|provided|offered)",
    r"(?:we|will|can|able to) (?:provide |offer )?(?:visa )?sponsor(?:ship)?",
    r"relocation (?:support|assistance|package)",
    r"erasmus",
    r"internship agreement|convention de stage|tripartite agreement|learning agreement",
    r"(?:regardless|irrespective) of (?:your )?(?:nationality|country|university|school)",
    r"(?:any|foreign|international) (?:university|universities|school|business school|engineering school)",
    r"from (?:a |an )?(?:european|french|foreign|international) (?:university|school)",
    r"ecole francaise|french (?:engineering |business )?school|grande ecole",
    r"auslandische studierende|internationale studierende",
    r"pflichtpraktikum|mandatory internship|compulsory internship|internship as part of (?:your|their) (?:studies|curriculum|degree)",
]
# Statut étudiant exigé SANS restriction de pays : dans l'UE/EEE/Suisse, un
# étudiant d'une école française avec convention de stage est en général éligible.
_FOREIGN_PROBABLE = [
    r"(?:immatrikuliert|eingeschrieben)(?! an einer deutschen)",
    r"(?:currently |actively )?enrolled (?:as a student )?(?:in|at) (?:a |an )?(?:university|college|higher education|school|bachelor|master|degree|engineering|business)",
    r"(?:currently )?(?:pursuing|studying (?:for|towards)) (?:a |an |your )?(?:bachelor|master|degree|msc|bsc|engineering)",
    r"student status|statut (?:d.)?etudiant|studentenstatus|studierendenstatus",
    r"etudiant(?:e)?s? en (?:ecole|master|bac\s?\+|derniere annee|cursus)",
    r"inscrit(?:e)?s? dans un (?:etablissement|ecole|cursus)",
    r"you are (?:a |currently a )?(?:student|studying)",
    r"(?:university|engineering|business) (?:student|students)",
    r"student (?:in|of) (?:a |an )?(?:bachelor|master|engineering|business)",
]
EU_LIKE = {"AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GR",
           "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL", "PL", "PT", "RO", "SK",
           "SI", "ES", "SE", "IS", "LI", "NO", "CH"}
_FOREIGN_KO_RE = [re.compile(p) for p in _FOREIGN_KO]
_FOREIGN_OK_RE = [re.compile(p) for p in _FOREIGN_OK]
_FOREIGN_PROBABLE_RE = [re.compile(p) for p in _FOREIGN_PROBABLE]


def detect_foreign(text_n: str, country: str = ""):
    """Une offre à l'étranger accepte-t-elle un étudiant inscrit hors du pays ?
    Renvoie ('ok'|'probable'|'ko'|'unknown', extrait)."""
    for r in _FOREIGN_KO_RE:
        m = r.search(text_n)
        if m:
            return "ko", _snippet(text_n, m)
    for r in _FOREIGN_OK_RE:
        m = r.search(text_n)
        if m:
            return "ok", _snippet(text_n, m)
    if country in EU_LIKE:
        for r in _FOREIGN_PROBABLE_RE:
            m = r.search(text_n)
            if m:
                return "probable", _snippet(text_n, m)
    return "unknown", ""


# ---------------------------------------------------------------------------
#  Durée
# ---------------------------------------------------------------------------
_DURATION = re.compile(
    r"(\d{1,2})(?:\s?(?:a|-|to|bis|à)\s?(\d{1,2}))?\s?(mois|months?|monate?n?|mesi|meses|maanden|semaines|weeks|wochen)\b")


def detect_duration(text_n: str):
    for m in _DURATION.finditer(text_n):
        a, b, unit = int(m.group(1)), m.group(2), m.group(3)
        months = int(b) if b else a
        if unit.startswith(("sem", "week", "woch")):
            months = round(months / 4.3)
        if 1 <= months <= 12:
            return months
    return None


def _snippet(text_n: str, m, width=90) -> str:
    a = max(0, m.start() - width)
    b = min(len(text_n), m.end() + width)
    s = text_n[a:b].replace("\n", " ")
    return ("…" if a else "") + s + ("…" if b < len(text_n) else "")


def enrich(offer: dict, home_country: str) -> dict:
    text_n = norm(offer["title"] + "\n" + offer.get("description", ""))
    # Le secteur saisi dans la config (entreprise connue) prime sur celui de la source.
    offer["sector"] = normalize_sector(offer.get("company_sector", ""),
                                       offer.pop("sector_hint", ""))
    offer.pop("company_sector", None)
    offer["cesure"], offer["cesure_evidence"] = detect_cesure(text_n)
    offer["abroad"] = bool(offer.get("country")) and offer["country"] != home_country
    if offer["abroad"]:
        offer["foreign"], offer["foreign_evidence"] = detect_foreign(text_n, offer["country"])
    else:
        offer["foreign"], offer["foreign_evidence"] = "n/a", ""
    offer["duration_months"] = detect_duration(text_n)
    return offer

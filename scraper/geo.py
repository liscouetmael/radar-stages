"""Détection du pays (code ISO-2) à partir d'un texte de localisation libre."""
import re

from .text import norm

COUNTRIES = {
    "FR": ["france", "frankreich", "francia"],
    "DE": ["germany", "deutschland", "allemagne", "alemania", "germania"],
    "GB": ["united kingdom", "uk", "u.k.", "england", "scotland", "wales",
           "great britain", "royaume-uni", "royaume uni", "angleterre"],
    "IE": ["ireland", "irlande"],
    "US": ["united states", "usa", "u.s.", "us", "united states of america",
           "etats-unis", "etats unis"],
    "CA": ["canada"],
    "ES": ["spain", "espana", "espagne"],
    "IT": ["italy", "italia", "italie"],
    "NL": ["netherlands", "nederland", "pays-bas", "pays bas", "the netherlands"],
    "BE": ["belgium", "belgique", "belgie"],
    "CH": ["switzerland", "suisse", "schweiz", "svizzera"],
    "AT": ["austria", "osterreich", "autriche"],
    "LU": ["luxembourg"],
    "PT": ["portugal"],
    "SE": ["sweden", "suede", "sverige"],
    "DK": ["denmark", "danemark"],
    "NO": ["norway", "norvege"],
    "FI": ["finland", "finlande"],
    "PL": ["poland", "pologne", "polska"],
    "CZ": ["czech republic", "czechia", "republique tcheque"],
    "RO": ["romania", "roumanie"],
    "HU": ["hungary", "hongrie"],
    "GR": ["greece", "grece"],
    "SG": ["singapore", "singapour"],
    "JP": ["japan", "japon"],
    "CN": ["china", "chine"],
    "HK": ["hong kong"],
    "KR": ["south korea", "korea", "coree du sud"],
    "IN": ["india", "inde"],
    "AU": ["australia", "australie"],
    "NZ": ["new zealand", "nouvelle-zelande"],
    "AE": ["united arab emirates", "uae", "emirats arabes unis"],
    "MA": ["morocco", "maroc"],
    "BR": ["brazil", "brasil", "bresil"],
    "MX": ["mexico", "mexique"],
    "IL": ["israel"],
    "PH": ["philippines"],
    "CO": ["colombia", "colombie"],
    "TW": ["taiwan"],
    "VN": ["vietnam", "viet nam"],
    "SA": ["saudi arabia", "arabie saoudite"],
    "ID": ["indonesia", "indonesie"],
    "TH": ["thailand", "thailande"],
    "MY": ["malaysia", "malaisie"],
    "TR": ["turkey", "turkiye", "turquie"],
    "ZA": ["south africa", "afrique du sud"],
    "AR": ["argentina", "argentine"],
    "CL": ["chile", "chili"],
    "EE": ["estonia", "estonie"],
    "RS": ["serbia", "serbie"],
    "BG": ["bulgaria", "bulgarie"],
}

CITIES = {
    "FR": ["paris", "lyon", "marseille", "toulouse", "bordeaux", "lille", "nantes",
           "nice", "rennes", "grenoble", "montpellier", "strasbourg", "sophia antipolis",
           "saint-nazaire", "marignane", "elancourt", "velizy", "massy", "la defense",
           "boulogne-billancourt", "issy-les-moulineaux", "gennevilliers", "blagnac",
           "palaiseau", "brest", "sophia-antipolis", "ile-de-france", "puteaux",
           "courbevoie", "nanterre", "saclay", "aix-en-provence"],
    "DE": ["berlin", "munich", "munchen", "hamburg", "frankfurt", "stuttgart",
           "cologne", "koln", "dusseldorf", "bremen", "ottobrunn", "manching",
           "taufkirchen", "ulm", "immenstaad", "leipzig", "dresden", "karlsruhe",
           "hannover", "nurnberg", "renningen", "reutlingen", "bonn"],
    "GB": ["london", "manchester", "edinburgh", "cambridge", "oxford", "bristol",
           "stevenage", "filton", "broughton", "glasgow", "belfast", "leeds"],
    "US": ["new york", "san francisco", "boston", "seattle", "chicago", "austin",
           "los angeles", "denver", "atlanta", "santa clara", "mountain view",
           "palo alto", "washington", "miami", "dallas", "houston", "cambridge, ma",
           "framingham", "morristown", "bridgewater", "swiftwater"],
    "ES": ["madrid", "barcelona", "getafe", "sevilla", "seville", "valencia"],
    "IT": ["milan", "milano", "rome", "roma", "turin", "torino"],
    "NL": ["amsterdam", "rotterdam", "eindhoven", "utrecht", "the hague", "leiden",
           "delft"],
    "BE": ["brussels", "bruxelles", "antwerp", "anvers", "liege", "ghent", "gand"],
    "CH": ["zurich", "geneva", "geneve", "lausanne", "basel", "bale", "bern"],
    "IE": ["dublin", "cork"],
    "CA": ["toronto", "montreal", "vancouver", "ottawa", "quebec"],
    "SG": ["singapore"],
    "JP": ["tokyo", "osaka"],
    "CN": ["shanghai", "beijing", "shenzhen", "tianjin"],
    "IN": ["bangalore", "bengaluru", "noida", "pune", "hyderabad", "mumbai",
           "gurgaon", "gurugram", "chennai"],
    "AU": ["sydney", "melbourne", "brisbane"],
    "PT": ["lisbon", "lisboa", "porto"],
    "PL": ["warsaw", "warszawa", "krakow", "gdansk"],
    "SE": ["stockholm"],
    "DK": ["copenhagen"],
    "AE": ["dubai", "abu dhabi"],
    "PH": ["makati", "manila", "taguig"],
    "CO": ["bogota", "medellin"],
    "TW": ["taipei", "hsinchu"],
    "VN": ["hanoi", "ho chi minh"],
    "SA": ["riyadh", "jeddah"],
    "RO": ["bucharest", "bucuresti", "cluj"],
    "HU": ["budapest"],
    "CZ": ["prague", "praha", "brno"],
    "AT": ["vienna", "wien", "linz", "graz"],
    "TR": ["istanbul", "ankara"],
    "MX": ["mexico city", "guadalajara", "monterrey"],
    "BR": ["sao paulo", "rio de janeiro", "campinas"],
    "MA": ["casablanca", "rabat"],
    "KR": ["seoul"],
    "HK": ["hong kong"],
    "IL": ["tel aviv"],
}

US_STATES = {"al", "ak", "az", "ar", "ca", "co", "ct", "de", "fl", "ga", "hi", "id",
             "il", "in", "ia", "ks", "ky", "la", "me", "md", "ma", "mi", "mn", "ms",
             "mo", "mt", "ne", "nv", "nh", "nj", "nm", "ny", "nc", "nd", "oh", "ok",
             "or", "pa", "ri", "sc", "sd", "tn", "tx", "ut", "vt", "va", "wa", "wv",
             "wi", "wy", "dc"}
FR_REGIONS = {"ile-de-france", "occitanie", "nouvelle-aquitaine", "bretagne",
              "auvergne-rhone-alpes", "provence-alpes-cote d'azur", "grand est",
              "hauts-de-france", "normandie", "pays de la loire"}

_ALIAS = {}
for code, names in COUNTRIES.items():
    _ALIAS[code.lower()] = code
    for n in names:
        _ALIAS[n] = code
_CITY = {c: code for code, cities in CITIES.items() for c in cities}

ADZUNA_COUNTRY = {"gb": "GB", "us": "US", "de": "DE", "fr": "FR", "nl": "NL",
                  "be": "BE", "ch": "CH", "es": "ES", "it": "IT", "ca": "CA",
                  "sg": "SG", "au": "AU", "at": "AT", "in": "IN", "pl": "PL",
                  "br": "BR", "mx": "MX", "nz": "NZ"}


def country_from_name(name: str) -> str:
    n = norm(name).strip(" .")
    return _ALIAS.get(n, "")


def guess_country(location: str) -> str:
    """Devine le pays à partir de 'Paris, France', 'New York, NY', 'Munich'..."""
    if not location:
        return ""
    loc = norm(location)
    # Département français entre parenthèses ou code postal "75 - Paris"
    if re.match(r"^\d{2,3} - ", loc) or re.search(r"\(\d{2,3}\)", loc):
        return "FR"
    parts = [p.strip(" .()") for p in re.split(r"[,/|;\-–]\s|,", loc) if p.strip()]
    for p in reversed(parts):
        if p in _ALIAS and (len(p) > 2 or p.upper() in COUNTRIES):
            # Code ambigu ("ca" = Canada ou Californie, "de" = Allemagne ou
            # Delaware) : on tranche avec la ville, sinon on suppose un État US.
            if p in US_STATES and len(parts) > 1 and _CITY.get(parts[0]) != _ALIAS[p]:
                return "US"
            return _ALIAS[p]
        if p in US_STATES and len(parts) > 1:
            return "US"
        if p in FR_REGIONS:
            return "FR"
        if p in _CITY:
            return _CITY[p]
    for city, code in _CITY.items():
        if re.search(r"\b" + re.escape(city) + r"\b", loc):
            return code
    for alias, code in _ALIAS.items():
        if len(alias) > 3 and re.search(r"\b" + re.escape(alias) + r"\b", loc):
            return code
    return ""

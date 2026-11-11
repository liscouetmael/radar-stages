from scraper.enrich import detect_cesure, detect_duration, detect_foreign, normalize_sector
from scraper.geo import guess_country
from scraper.text import is_internship, norm


def f(text, country="DE"):
    return detect_foreign(norm(text), country)[0]


def test_internship_detection():
    assert is_internship("Stage - Ingénieur données (H/F)")
    assert is_internship("Software Engineering Intern - Summer 2027")
    assert is_internship("Praktikant (m/w/d) Marketing")
    assert is_internship("Data Analyst", "Intern")
    assert not is_internship("Internal Audit Manager")
    assert not is_internship("Early-stage Investor")
    assert not is_internship("Alternance - Chargé de communication")


def test_foreign_excluded():
    assert f("Must be currently enrolled in a U.S. university", "US") == "ko"
    assert f("You must be authorized to work in the United States without sponsorship", "US") == "ko"
    assert f("We are unable to sponsor visas for this role", "GB") == "ko"
    assert f("Immatrikuliert an einer deutschen Hochschule") == "ko"


def test_foreign_accepted():
    assert f("International students are welcome to apply", "US") == "ok"
    assert f("Your school must provide a convention de stage") == "ok"
    assert f("Erasmus+ traineeship possible", "ES") == "ok"
    assert f("Visa sponsorship is available", "GB") == "ok"


def test_foreign_probable_only_in_eu():
    assert f("You are currently enrolled in a university (Master)") == "probable"
    assert f("You are currently enrolled in a university (Master)", "US") == "unknown"
    assert f("Great team, nice office") == "unknown"


def test_cesure():
    assert detect_cesure(norm("Stage de césure de 6 mois"))[0] == "yes"
    assert detect_cesure(norm("Gap year internship"))[0] == "yes"
    assert detect_cesure(norm("Stage de fin d'études uniquement, pas de césure"))[0] == "no"
    assert detect_cesure(norm("Stage de fin d'études"))[0] == "fin_etudes"
    assert detect_cesure(norm("Stage de 6 mois"))[0] == "unknown"


def test_duration():
    assert detect_duration(norm("Stage de 6 mois à partir de janvier")) == 6
    assert detect_duration(norm("4 to 6 months internship")) == 6
    assert detect_duration(norm("12 weeks summer internship")) == 3
    assert detect_duration(norm("Since 2010, 300 employees")) is None


def test_country():
    assert guess_country("Paris, France") == "FR"
    assert guess_country("New York, NY") == "US"
    assert guess_country("Munich") == "DE"
    assert guess_country("75 - Paris 8e Arrondissement") == "FR"
    assert guess_country("London, United Kingdom") == "GB"
    assert guess_country("Taiwan, Taipei") == "TW"


def test_sector():
    assert normalize_sector("Aéronautique & Défense") == "Aéronautique & Défense"
    assert normalize_sector("Activités des banques centrales") == "Finance & Banque"
    assert normalize_sector("", "") == "Autre"
    assert normalize_sector("Quantum Computing") == "Quantique"
    assert normalize_sector("Nuclear Power") == "Nucléaire & Fusion"
    assert normalize_sector("Restauration et gastronomie") != "Spatial & Astrophysique"

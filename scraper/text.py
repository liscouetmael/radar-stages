"""Outils texte : HTML -> texte brut, normalisation, détection de stage."""
import html
import re
import unicodedata

_TAG = re.compile(r"<[^>]+>")
_BLOCK = re.compile(r"</?(p|div|br|li|ul|ol|h[1-6]|tr|section)[^>]*>", re.I)
_WS = re.compile(r"[ \t\r\f\v]+")
_NL = re.compile(r"\n\s*\n+")


def html_to_text(s: str) -> str:
    if not s:
        return ""
    s = html.unescape(s)
    if "&lt;" in s or "&amp;" in s:  # contenu doublement échappé (Greenhouse)
        s = html.unescape(s)
    s = _BLOCK.sub("\n", s)
    s = _TAG.sub(" ", s)
    s = html.unescape(s)
    s = _WS.sub(" ", s)
    s = _NL.sub("\n\n", s)
    return s.strip()


def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s)
                   if not unicodedata.combining(c))


def norm(s: str) -> str:
    """Minuscules, sans accents, espaces simples."""
    return re.sub(r"\s+", " ", strip_accents(s or "").lower()).strip()


# Mots qui signalent un stage, dans plusieurs langues.
_INTERN = re.compile(
    r"\b(stage|stages|stagiaire|intern|interns|internship|internships|praktikum|"
    r"praktikant(?:in)?|tirocinio|tirocinante|stagista|practicas|"
    r"becario|becaria|stagiair|afstudeerstage|estagio)\b"
)
# Faux positifs fréquents ("early stage", "stage manager", "internal"...).
_NOT_INTERN = re.compile(
    r"\b(early[- ]stage|late[- ]stage|stage manager|multi[- ]stage|"
    r"growth[- ]stage|senior|alternance|alternant|apprenti|apprentissage|"
    r"apprenticeship|ausbildung|duales studium)\b"
)


def is_internship(title: str, extra: str = "") -> bool:
    t = norm(title)
    if _INTERN.search(t) and not _NOT_INTERN.search(t):
        return True
    # Certaines sources indiquent le type de contrat à part (ex: "Intern").
    e = norm(extra)
    return bool(e and _INTERN.search(e) and not _NOT_INTERN.search(t))


def truncate(s: str, n: int) -> str:
    return s if len(s) <= n else s[:n].rsplit(" ", 1)[0] + " …"

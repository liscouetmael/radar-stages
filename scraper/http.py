"""Session HTTP partagée : retries, timeout, user-agent, politesse."""
import time

try:  # utilise le magasin de certificats du système (antivirus/proxy d'entreprise)
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

UA = "Mozilla/5.0 (compatible; RechercheStageBot/1.0)"
TIMEOUT = 25
DELAY = 0.25  # secondes entre deux requêtes vers un même service

_session = None


def session() -> requests.Session:
    global _session
    if _session is None:
        s = requests.Session()
        retry = Retry(total=3, backoff_factor=1.5,
                      status_forcelist=(429, 500, 502, 503, 504),
                      allowed_methods=("GET", "POST"))
        s.mount("https://", HTTPAdapter(max_retries=retry))
        s.headers.update({"User-Agent": UA, "Accept": "application/json"})
        _session = s
    return _session


def get_json(url, **kw):
    time.sleep(DELAY)
    r = session().get(url, timeout=TIMEOUT, **kw)
    r.raise_for_status()
    return r.json()


def post_json(url, payload=None, **kw):
    time.sleep(DELAY)
    r = session().post(url, json=payload, timeout=TIMEOUT, **kw)
    r.raise_for_status()
    return r.json()

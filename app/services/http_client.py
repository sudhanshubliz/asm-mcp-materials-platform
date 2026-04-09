from __future__ import annotations

import requests
from requests import Session
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.config import config


def build_retrying_session() -> Session:
    retry = Retry(
        total=config.REQUEST_RETRY_ATTEMPTS,
        connect=config.REQUEST_RETRY_ATTEMPTS,
        read=config.REQUEST_RETRY_ATTEMPTS,
        status=config.REQUEST_RETRY_ATTEMPTS,
        backoff_factor=config.REQUEST_RETRY_BACKOFF,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session = requests.Session()
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

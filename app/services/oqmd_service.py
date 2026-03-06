import requests

from app.config import config
from app.services.exceptions import ExternalServiceError


def search_oqmd(composition: str, limit: int = 20, offset: int = 0) -> dict:
    url = f"{config.OQMD_API.rstrip('/')}/{config.OQMD_RESOURCE.lstrip('/')}"
    params = {
        "composition": composition,
        "limit": limit,
        "offset": offset,
        "format": "json",
    }
    try:
        response = requests.get(url, params=params, timeout=config.REQUEST_TIMEOUT)
        response.raise_for_status()
        payload = response.json()
        data = payload.get("data") if isinstance(payload, dict) else payload
        return {
            "count": len(data) if isinstance(data, list) else 0,
            "data": data if isinstance(data, list) else [],
            "meta": payload.get("meta", {}) if isinstance(payload, dict) else {},
        }
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else 502
        detail = exc.response.text if exc.response is not None else str(exc)
        raise ExternalServiceError(
            service="oqmd",
            message=f"OQMD request failed ({status}): {detail[:300]}",
            status_code=502,
        ) from exc
    except requests.RequestException as exc:
        raise ExternalServiceError(
            service="oqmd",
            message=f"OQMD network error: {exc}",
            status_code=502,
        ) from exc

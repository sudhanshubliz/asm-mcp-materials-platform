from io import BytesIO
from unittest.mock import MagicMock, patch
import urllib.error

import pytest

from scripts.smoke_deployment import _request_json


def _json_response() -> MagicMock:
    response = MagicMock()
    response.__enter__.return_value = response
    return response


def test_request_json_retries_timeout_then_succeeds():
    response = _json_response()
    with (
        patch(
            "scripts.smoke_deployment.urllib.request.urlopen",
            side_effect=[TimeoutError("cold start"), response],
        ) as urlopen,
        patch("scripts.smoke_deployment.json.load", return_value={"status": "ok"}),
        patch("scripts.smoke_deployment.time.sleep") as sleep,
    ):
        result = _request_json("https://example.com", "/health", retry_delay_seconds=2)

    assert result == {"status": "ok"}
    assert urlopen.call_count == 2
    sleep.assert_called_once_with(2)


def test_request_json_retries_transient_http_error():
    response = _json_response()
    unavailable = urllib.error.HTTPError(
        "https://example.com/health",
        503,
        "Unavailable",
        {},
        BytesIO(b"starting"),
    )
    with (
        patch(
            "scripts.smoke_deployment.urllib.request.urlopen",
            side_effect=[unavailable, response],
        ) as urlopen,
        patch("scripts.smoke_deployment.json.load", return_value={"status": "ok"}),
        patch("scripts.smoke_deployment.time.sleep") as sleep,
    ):
        result = _request_json("https://example.com", "/health")

    assert result == {"status": "ok"}
    assert urlopen.call_count == 2
    sleep.assert_called_once_with(5)


def test_request_json_does_not_retry_permanent_http_error():
    not_found = urllib.error.HTTPError(
        "https://example.com/missing",
        404,
        "Not Found",
        {},
        BytesIO(b"missing"),
    )
    with (
        patch("scripts.smoke_deployment.urllib.request.urlopen", side_effect=not_found) as urlopen,
        patch("scripts.smoke_deployment.time.sleep") as sleep,
        pytest.raises(RuntimeError, match=r"HTTP 404 after 1 attempt\(s\): missing"),
    ):
        _request_json("https://example.com", "/missing")

    urlopen.assert_called_once()
    sleep.assert_not_called()

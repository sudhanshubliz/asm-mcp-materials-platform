from unittest.mock import patch

import pytest

from app.services.db_service import _validate_read_only_query
from app.tools.sql_tools import run_sql_query


def test_run_sql_query_delegates_to_service():
    with patch("app.tools.sql_tools.run_query", return_value=[{"id": 1}]) as run_query_mock:
        result = run_sql_query("SELECT 1")

    assert result == [{"id": 1}]
    run_query_mock.assert_called_once_with("SELECT 1", 100)


def test_validate_read_only_query_rejects_mutation():
    with pytest.raises(ValueError):
        _validate_read_only_query("DELETE FROM materials")


def test_validate_read_only_query_accepts_select():
    _validate_read_only_query("SELECT * FROM materials")

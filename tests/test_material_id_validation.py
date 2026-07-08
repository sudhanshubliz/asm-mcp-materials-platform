import pytest
from pydantic import ValidationError

from app.models.schemas import AdvancedMaterialSearchRequest, MaterialByIdRequest


def test_material_id_accepts_numeric_mp_identifier():
    request = MaterialByIdRequest(material_id="mp-149")

    assert request.material_id == "mp-149"


def test_material_id_rejects_non_numeric_mp_identifier():
    with pytest.raises(ValidationError):
        MaterialByIdRequest(material_id="mp-djqth")


def test_advanced_search_rejects_non_numeric_material_id():
    with pytest.raises(ValidationError):
        AdvancedMaterialSearchRequest(material_ids=["mp-djqth"])

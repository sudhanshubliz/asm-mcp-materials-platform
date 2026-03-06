from app.services.materials_service import search_material
from app.services.oqmd_service import search_oqmd


def get_material_bundle(formula: str) -> dict:
    return {
        "materials_project": search_material(formula),
        "oqmd": search_oqmd(formula),
    }

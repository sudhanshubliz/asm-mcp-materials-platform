from __future__ import annotations

from pydantic import BaseModel, Field, field_validator, model_validator


class MaterialSearchRequest(BaseModel):
    formula: str = Field(min_length=1, max_length=40)
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0, le=10000)

    @field_validator("formula")
    @classmethod
    def validate_formula(cls, value: str) -> str:
        allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789()+-.")
        if any(ch not in allowed for ch in value):
            raise ValueError("formula contains unsupported characters")
        return value


class MaterialByIdRequest(BaseModel):
    material_id: str = Field(min_length=3, max_length=40, pattern=r"^mp-[A-Za-z0-9-]+$")


class SQLQueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=10000)
    limit: int = Field(default=100, ge=1, le=1000)


class RagSearchRequest(BaseModel):
    question: str = Field(min_length=3, max_length=5000)
    top_k: int = Field(default=5, ge=1, le=20)


class NumericRange(BaseModel):
    min: float | None = None
    max: float | None = None

    @model_validator(mode="after")
    def validate_bounds(self) -> "NumericRange":
        if self.min is None and self.max is None:
            raise ValueError("at least one range bound is required")
        if self.min is not None and self.max is not None and self.min > self.max:
            raise ValueError("range min cannot be greater than range max")
        return self


class AdvancedMaterialSearchRequest(BaseModel):
    query: str | None = Field(default=None, max_length=5000)
    formula: str | None = Field(default=None, min_length=1, max_length=40)
    material_ids: list[str] = Field(default_factory=list)
    elements: list[str] = Field(default_factory=list)
    exclude_elements: list[str] = Field(default_factory=list)
    crystal_system: str | None = Field(default=None, min_length=3, max_length=32)
    is_stable: bool | None = None
    is_metal: bool | None = None
    num_elements: NumericRange | None = None
    band_gap: NumericRange | None = None
    density: NumericRange | None = None
    volume: NumericRange | None = None
    energy_above_hull: NumericRange | None = None
    bulk_modulus_vrh: NumericRange | None = None
    shear_modulus_vrh: NumericRange | None = None
    weighted_surface_energy: NumericRange | None = None
    work_function: NumericRange | None = None
    surface_anisotropy: NumericRange | None = None
    shape_factor: NumericRange | None = None
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0, le=10000)

    @field_validator("formula")
    @classmethod
    def validate_optional_formula(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return MaterialSearchRequest.validate_formula(value)

    @field_validator("elements", "exclude_elements", mode="before")
    @classmethod
    def normalize_elements(cls, value: list[str] | str | None) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            value = [part.strip() for part in value.split(",") if part.strip()]
        normalized = []
        for element in value:
            element = element.strip()
            if not element:
                continue
            normalized.append(element[0].upper() + element[1:].lower())
        return normalized

    @field_validator("material_ids", mode="before")
    @classmethod
    def normalize_material_ids(cls, value: list[str] | str | None) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            value = [part.strip() for part in value.split(",") if part.strip()]
        return list(value)

    @field_validator("material_ids")
    @classmethod
    def validate_material_ids(cls, value: list[str]) -> list[str]:
        for material_id in value:
            MaterialByIdRequest(material_id=material_id)
        return value

    @field_validator("crystal_system")
    @classmethod
    def normalize_crystal_system(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().lower()

    @model_validator(mode="after")
    def validate_has_criteria(self) -> "AdvancedMaterialSearchRequest":
        if any(
            (
                self.query,
                self.formula,
                self.material_ids,
                self.elements,
                self.exclude_elements,
                self.crystal_system,
                self.is_stable is not None,
                self.is_metal is not None,
                self.num_elements,
                self.band_gap,
                self.density,
                self.volume,
                self.energy_above_hull,
                self.bulk_modulus_vrh,
                self.shear_modulus_vrh,
                self.weighted_surface_energy,
                self.work_function,
                self.surface_anisotropy,
                self.shape_factor,
            )
        ):
            return self
        raise ValueError("at least one search criterion is required")

from pydantic import BaseModel, Field, field_validator


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

from fastapi_jsonapi.schema_base import BaseModel


class ChildBaseSchema(BaseModel):
    """Child base schema."""

    class Config:
        orm_mode = True

    name: str


class ChildPatchSchema(ChildBaseSchema):
    """Child PATCH schema."""


class ChildInSchema(ChildBaseSchema):
    """Child input schema."""


class ChildSchema(ChildInSchema):
    """Child item schema."""

    id: int

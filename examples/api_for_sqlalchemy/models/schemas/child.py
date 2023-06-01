from fastapi_jsonapi.schema_base import BaseModel


class ChildBaseSchema(BaseModel):
    """Child base schema."""

    class Config:
        """Pydantic schema config."""

        orm_mode = True

    name: str


class ChildPatchSchema(ChildBaseSchema):
    """Child PATCH schema."""


class ChildInSchema(ChildBaseSchema):
    """Child input schema."""


class ChildSchema(ChildInSchema):
    """PostComment item schema."""

    class Config:
        """Pydantic model config."""

        orm_mode = True

    id: int

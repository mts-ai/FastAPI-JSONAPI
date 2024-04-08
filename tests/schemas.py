from typing import Dict, List, Optional
from uuid import UUID

from pydantic import validator

from fastapi_jsonapi.schema_base import BaseModel, Field, RelationshipInfo


class UserAttributesBaseSchema(BaseModel):
    name: str
    age: Optional[int] = None
    email: Optional[str] = None

    class Config:
        """Pydantic schema config."""

        orm_mode = True


class UserBaseSchema(UserAttributesBaseSchema):
    """User base schema."""

    posts: Optional[List["PostSchema"]] = Field(
        relationship=RelationshipInfo(
            resource_type="post",
            many=True,
        ),
    )

    bio: Optional["UserBioSchema"] = Field(
        relationship=RelationshipInfo(
            resource_type="user_bio",
        ),
    )

    computers: Optional[List["ComputerSchema"]] = Field(
        relationship=RelationshipInfo(
            resource_type="computer",
            many=True,
        ),
    )
    workplace: Optional["WorkplaceSchema"] = Field(
        relationship=RelationshipInfo(
            resource_type="workplace",
        ),
    )


class UserPatchSchema(UserBaseSchema):
    """User PATCH schema."""


class UserInSchema(UserBaseSchema):
    """User input schema."""


class UserInSchemaAllowIdOnPost(UserBaseSchema):
    id: str = Field(client_can_set_id=True)


class UserSchema(UserInSchema):
    """User item schema."""

    class Config:
        """Pydantic model config."""

        orm_mode = True

    id: int


# User Bio Schemas ⬇️


class UserBioAttributesBaseSchema(BaseModel):
    """UserBio base schema."""

    class Config:
        """Pydantic schema config."""

        orm_mode = True

    birth_city: str
    favourite_movies: str
    keys_to_ids_list: Dict[str, List[int]] = None


class UserBioSchema(UserBioAttributesBaseSchema):
    """UserBio item schema."""

    id: int
    user: "UserSchema" = Field(
        relationship=RelationshipInfo(
            resource_type="user",
        ),
    )


# Post Schemas ⬇️


class PostAttributesBaseSchema(BaseModel):
    title: str
    body: str

    class Config:
        """Pydantic schema config."""

        orm_mode = True


class PostBaseSchema(PostAttributesBaseSchema):
    """Post base schema."""

    user: "UserSchema" = Field(
        relationship=RelationshipInfo(
            resource_type="user",
        ),
    )
    comments: Optional[List["PostCommentSchema"]] = Field(
        relationship=RelationshipInfo(
            resource_type="post_comment",
            many=True,
        ),
    )


class PostPatchSchema(PostBaseSchema):
    """Post PATCH schema."""


class PostInSchema(PostBaseSchema):
    """Post input schema."""


class PostSchema(PostInSchema):
    """Post item schema."""

    id: int


# Post Comment Schemas ⬇️


class PostCommentAttributesBaseSchema(BaseModel):
    text: str

    class Config:
        """Pydantic schema config."""

        orm_mode = True


class PostCommentBaseSchema(PostCommentAttributesBaseSchema):
    """PostComment base schema."""

    post: "PostSchema" = Field(
        relationship=RelationshipInfo(
            resource_type="post",
        ),
    )
    author: "UserSchema" = Field(
        relationship=RelationshipInfo(
            resource_type="user",
        ),
    )


class PostCommentSchema(PostCommentBaseSchema):
    """PostComment item schema."""

    id: int


# Parents and Children associations ⬇️⬇️


# Association Schemas ⬇️


class ParentToChildAssociationAttributesSchema(BaseModel):
    extra_data: str

    class Config:
        orm_mode = True


class ParentToChildAssociationSchema(ParentToChildAssociationAttributesSchema):
    parent: "ParentSchema" = Field(
        relationship=RelationshipInfo(
            resource_type="parent",
        ),
    )

    child: "ChildSchema" = Field(
        relationship=RelationshipInfo(
            resource_type="child",
        ),
    )


# Parent Schemas ⬇️


class ParentAttributesSchema(BaseModel):
    name: str

    class Config:
        """Pydantic schema config."""

        orm_mode = True


class ParentBaseSchema(ParentAttributesSchema):
    """Parent base schema."""

    children: List["ParentToChildAssociationSchema"] = Field(
        default=None,
        relationship=RelationshipInfo(
            resource_type="parent_child_association",
            many=True,
        ),
    )


class ParentPatchSchema(ParentBaseSchema):
    """Parent PATCH schema."""


class ParentInSchema(ParentBaseSchema):
    """Parent input schema."""


class ParentSchema(ParentInSchema):
    """Parent item schema."""

    id: int


# Child Schemas ⬇️


class ChildAttributesSchema(BaseModel):
    name: str

    class Config:
        """Pydantic schema config."""

        orm_mode = True


class ChildBaseSchema(ChildAttributesSchema):
    """Child base schema."""

    parents: List["ParentToChildAssociationSchema"] = Field(
        default=None,
        relationship=RelationshipInfo(
            resource_type="parent_child_association",
            many=True,
        ),
    )


class ChildPatchSchema(ChildBaseSchema):
    """Child PATCH schema."""


class ChildInSchema(ChildBaseSchema):
    """Child input schema."""


class ChildSchema(ChildInSchema):
    """Child item schema."""

    id: int


class ComputerAttributesBaseSchema(BaseModel):
    class Config:
        """Pydantic schema config."""

        orm_mode = True

    name: str


class ComputerBaseSchema(ComputerAttributesBaseSchema):
    """Computer base schema."""

    user: Optional["UserSchema"] = Field(
        relationship=RelationshipInfo(
            resource_type="user",
        ),
    )


class ComputerPatchSchema(ComputerBaseSchema):
    """Computer PATCH schema."""


class ComputerInSchema(ComputerBaseSchema):
    """Computer input schema."""


class ComputerSchema(ComputerInSchema):
    """Computer item schema."""

    class Config:
        """Pydantic model config."""

        orm_mode = True

    id: int

    # TODO: rename
    # owner: Optional["UserSchema"] = Field(
    user: Optional["UserSchema"] = Field(
        relationship=RelationshipInfo(
            resource_type="user",
        ),
    )


class WorkplaceBaseSchema(BaseModel):
    """Workplace base schema."""

    class Config:
        """Pydantic schema config."""

        orm_mode = True

    name: str
    user: Optional["UserSchema"] = Field(
        relationship=RelationshipInfo(
            resource_type="user",
        ),
    )


class WorkplacePatchSchema(ComputerBaseSchema):
    """Workplace PATCH schema."""


class WorkplaceInSchema(ComputerBaseSchema):
    """Workplace input schema."""


class WorkplaceSchema(ComputerInSchema):
    """Workplace item schema."""

    class Config:
        """Pydantic model config."""

        orm_mode = True

    id: int


# task
class TaskBaseSchema(BaseModel):
    class Config:
        orm_mode = True

    task_ids: Optional[list[str]] = None

    # noinspection PyMethodParameters
    @validator("task_ids", pre=True)
    def task_ids_validator(cls, value: Optional[list[str]]):
        """
        return `[]`, if value is None both on get and on create
        """
        return value or []


class TaskPatchSchema(TaskBaseSchema):
    """Task PATCH schema."""


class TaskInSchema(TaskBaseSchema):
    """Task create schema."""


class TaskSchema(TaskBaseSchema):
    """Task item schema."""

    id: int


# uuid below


class CustomUUIDItemAttributesSchema(BaseModel):
    extra_id: Optional[UUID] = None

    class Config:
        orm_mode = True


class CustomUUIDItemSchema(CustomUUIDItemAttributesSchema):
    id: UUID = Field(client_can_set_id=True)


class SelfRelationshipAttributesSchema(BaseModel):
    name: str

    class Config:
        orm_mode = True


class SelfRelationshipSchema(SelfRelationshipAttributesSchema):
    self_relationship: Optional["SelfRelationshipSchema"] = Field(
        relationship=RelationshipInfo(
            resource_type="self_relationship",
        ),
    )


class CascadeCaseSchema(BaseModel):
    parent_item: Optional["CascadeCaseSchema"] = Field(
        relationship=RelationshipInfo(
            resource_type="cascade_case",
        ),
    )
    sub_items: Optional[list["CascadeCaseSchema"]] = Field(
        relationship=RelationshipInfo(
            resource_type="cascade_case",
            many=True,
        ),
    )


class CustomUserAttributesSchema(UserBaseSchema):
    spam: str
    eggs: str


class AlphaSchema(BaseModel):
    beta: Optional["BetaSchema"] = Field(
        relationship=RelationshipInfo(
            resource_type="beta",
        ),
    )
    gamma: Optional["GammaSchema"] = Field(
        relationship=RelationshipInfo(
            resource_type="gamma",
        ),
    )


class BetaSchema(BaseModel):
    alphas: Optional["AlphaSchema"] = Field(
        relationship=RelationshipInfo(
            resource_type="alpha",
        ),
    )
    gammas: Optional["GammaSchema"] = Field(
        None,
        relationship=RelationshipInfo(
            resource_type="gamma",
            many=True,
        ),
    )
    deltas: Optional["DeltaSchema"] = Field(
        None,
        relationship=RelationshipInfo(
            resource_type="delta",
            many=True,
        ),
    )


class GammaSchema(BaseModel):
    betas: Optional["BetaSchema"] = Field(
        None,
        relationship=RelationshipInfo(
            resource_type="beta",
            many=True,
        ),
    )
    delta: Optional["DeltaSchema"] = Field(
        None,
        relationship=RelationshipInfo(
            resource_type="Delta",
        ),
    )


class DeltaSchema(BaseModel):
    name: str
    gammas: Optional["GammaSchema"] = Field(
        None,
        relationship=RelationshipInfo(
            resource_type="gamma",
            many=True,
        ),
    )
    betas: Optional["BetaSchema"] = Field(
        None,
        relationship=RelationshipInfo(
            resource_type="beta",
            many=True,
        ),
    )

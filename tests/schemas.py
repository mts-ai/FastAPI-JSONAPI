from typing import List, Optional
from uuid import UUID

from pydantic import ConfigDict, field_validator

from fastapi_jsonapi.schema_base import BaseModel, Field, RelationshipInfo


class UserAttributesBaseSchema(BaseModel):
    name: str
    age: Optional[int] = None
    email: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class UserBaseSchema(UserAttributesBaseSchema):
    """User base schema."""

    posts: Optional[List["PostSchema"]] = Field(
        json_schema_extra={
            "relationship": RelationshipInfo(
                resource_type="post",
                many=True,
            ),
        },
    )

    bio: Optional["UserBioSchema"] = Field(
        json_schema_extra={
            "relationship": RelationshipInfo(
                resource_type="user_bio",
            ),
        },
    )

    computers: Optional[List["ComputerSchema"]] = Field(
        json_schema_extra={
            "relationship": RelationshipInfo(
                resource_type="computer",
                many=True,
            ),
        },
    )
    workplace: Optional["WorkplaceSchema"] = Field(
        json_schema_extra={"relationship": RelationshipInfo(resource_type="workplace")},
    )


class UserPatchSchema(UserBaseSchema):
    """User PATCH schema."""


class UserInSchema(UserBaseSchema):
    """User input schema."""


class UserInSchemaAllowIdOnPost(UserBaseSchema):
    id: str = Field(json_schema_extra={"client_can_set_id": True})


class UserSchema(UserInSchema):
    """User item schema."""

    model_config = ConfigDict(from_attributes=True)

    id: int


# User Bio Schemas ⬇️


class UserBioAttributesBaseSchema(BaseModel):
    """UserBio base schema."""

    model_config = ConfigDict(from_attributes=True)

    birth_city: str
    favourite_movies: str
    # keys_to_ids_list: Optional[Dict[str, List[int]]] = None


class UserBioSchema(UserBioAttributesBaseSchema):
    """UserBio item schema."""

    id: int
    user: "UserSchema" = Field(
        json_schema_extra={
            "relationship": RelationshipInfo(
                resource_type="user",
            ),
        },
    )


# Post Schemas ⬇️


class PostAttributesBaseSchema(BaseModel):
    title: str
    body: str
    model_config = ConfigDict(from_attributes=True)


class PostBaseSchema(PostAttributesBaseSchema):
    """Post base schema."""

    user: "UserSchema" = Field(
        json_schema_extra={
            "relationship": RelationshipInfo(
                resource_type="user",
            ),
        },
    )
    comments: Optional[List["PostCommentSchema"]] = Field(
        json_schema_extra={
            "relationship": RelationshipInfo(
                resource_type="post_comment",
                many=True,
            ),
        },
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
    model_config = ConfigDict(from_attributes=True)


class PostCommentBaseSchema(PostCommentAttributesBaseSchema):
    """PostComment base schema."""

    post: "PostSchema" = Field(
        json_schema_extra={
            "relationship": RelationshipInfo(
                resource_type="post",
            ),
        },
    )
    author: "UserSchema" = Field(
        json_schema_extra={
            "relationship": RelationshipInfo(
                resource_type="user",
            ),
        },
    )


class PostCommentSchema(PostCommentBaseSchema):
    """PostComment item schema."""

    id: int


# Parents and Children associations ⬇️⬇️


# Association Schemas ⬇️


class ParentToChildAssociationAttributesSchema(BaseModel):
    extra_data: str
    model_config = ConfigDict(from_attributes=True)


class ParentToChildAssociationSchema(ParentToChildAssociationAttributesSchema):
    parent: "ParentSchema" = Field(
        json_schema_extra={
            "relationship": RelationshipInfo(
                resource_type="parent",
            ),
        },
    )

    child: "ChildSchema" = Field(
        json_schema_extra={
            "relationship": RelationshipInfo(
                resource_type="child",
            ),
        },
    )


# Parent Schemas ⬇️


class ParentAttributesSchema(BaseModel):
    name: str
    model_config = ConfigDict(from_attributes=True)


class ParentBaseSchema(ParentAttributesSchema):
    """Parent base schema."""

    children: List["ParentToChildAssociationSchema"] = Field(
        default=None,
        json_schema_extra={
            "relationship": RelationshipInfo(
                resource_type="parent_child_association",
                many=True,
            ),
        },
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
    model_config = ConfigDict(from_attributes=True)


class ChildBaseSchema(ChildAttributesSchema):
    """Child base schema."""

    parents: List["ParentToChildAssociationSchema"] = Field(
        default=None,
        json_schema_extra={
            "relationship": RelationshipInfo(
                resource_type="parent_child_association",
                many=True,
            ),
        },
    )


class ChildPatchSchema(ChildBaseSchema):
    """Child PATCH schema."""


class ChildInSchema(ChildBaseSchema):
    """Child input schema."""


class ChildSchema(ChildInSchema):
    """Child item schema."""

    id: int


class ComputerAttributesBaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str


class ComputerBaseSchema(ComputerAttributesBaseSchema):
    """Computer base schema."""

    user: Optional["UserSchema"] = Field(
        json_schema_extra={
            "relationship": RelationshipInfo(
                resource_type="user",
            ),
        },
    )


class ComputerPatchSchema(ComputerBaseSchema):
    """Computer PATCH schema."""


class ComputerInSchema(ComputerBaseSchema):
    """Computer input schema."""


class ComputerSchema(ComputerInSchema):
    """Computer item schema."""

    model_config = ConfigDict(from_attributes=True)

    id: int

    # TODO: rename
    # owner: Optional["UserSchema"] = Field(
    user: Optional["UserSchema"] = Field(
        json_schema_extra={
            "relationship": RelationshipInfo(
                resource_type="user",
            ),
        },
    )


class WorkplaceBaseSchema(BaseModel):
    """Workplace base schema."""

    model_config = ConfigDict(from_attributes=True)

    name: str
    user: Optional["UserSchema"] = Field(
        json_schema_extra={
            "relationship": RelationshipInfo(
                resource_type="user",
            ),
        },
    )


class WorkplacePatchSchema(ComputerBaseSchema):
    """Workplace PATCH schema."""


class WorkplaceInSchema(ComputerBaseSchema):
    """Workplace input schema."""


class WorkplaceSchema(ComputerInSchema):
    """Workplace item schema."""

    model_config = ConfigDict(from_attributes=True)

    id: int


# task
class TaskBaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    task_ids: Optional[list[str]] = None

    # noinspection PyMethodParameters
    @field_validator("task_ids", mode="before", check_fields=False)
    @classmethod
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
    model_config = ConfigDict(from_attributes=True)


class CustomUUIDItemSchema(CustomUUIDItemAttributesSchema):
    id: UUID = Field(json_schema_extra={"client_can_set_id": True})


class SelfRelationshipAttributesSchema(BaseModel):
    name: str
    self_relationship: Optional["SelfRelationshipAttributesSchema"] = Field(
        json_schema_extra={
            "relationship": RelationshipInfo(
                resource_type="self_relationship",
            ),
        },
    )
    children_objects: Optional["SelfRelationshipAttributesSchema"] = Field(
        json_schema_extra={
            "relationship": RelationshipInfo(
                resource_type="self_relationship",
                many=True,
            ),
        },
    )


class CascadeCaseSchema(BaseModel):
    parent_item: Optional["CascadeCaseSchema"] = Field(
        json_schema_extra={
            "relationship": RelationshipInfo(
                resource_type="cascade_case",
            ),
        },
    )
    sub_items: Optional[list["CascadeCaseSchema"]] = Field(
        json_schema_extra={
            "relationship": RelationshipInfo(
                resource_type="cascade_case",
                many=True,
            ),
        },
    )


class CustomUserAttributesSchema(UserBaseSchema):
    spam: str
    eggs: str


class AlphaSchema(BaseModel):
    beta: Optional["BetaSchema"] = Field(
        json_schema_extra={
            "relationship": RelationshipInfo(
                resource_type="beta",
            ),
        },
    )
    gamma: Optional["BetaSchema"] = Field(
        json_schema_extra={
            "relationship": RelationshipInfo(
                resource_type="gamma",
            ),
        },
    )


class BetaSchema(BaseModel):
    alphas: Optional["AlphaSchema"] = Field(
        json_schema_extra={
            "relationship": RelationshipInfo(
                resource_type="alpha",
            ),
        },
    )
    gammas: Optional["GammaSchema"] = Field(
        default=None,
        json_schema_extra={
            "relationship": RelationshipInfo(
                resource_type="gamma",
                many=True,
            ),
        },
    )
    deltas: Optional["DeltaSchema"] = Field(
        default=None,
        json_schema_extra={
            "relationship": RelationshipInfo(
                resource_type="delta",
                many=True,
            ),
        },
    )


class GammaSchema(BaseModel):
    betas: Optional["BetaSchema"] = Field(
        default=None,
        json_schema_extra={
            "relationship": RelationshipInfo(
                resource_type="beta",
                many=True,
            ),
        },
    )
    delta: Optional["DeltaSchema"] = Field(
        default=None,
        json_schema_extra={
            "relationship": RelationshipInfo(
                resource_type="Delta",
            ),
        },
    )


class DeltaSchema(BaseModel):
    name: str
    gammas: Optional["GammaSchema"] = Field(
        default=None,
        json_schema_extra={
            "relationship": RelationshipInfo(
                resource_type="gamma",
                many=True,
            ),
        },
    )
    betas: Optional["BetaSchema"] = Field(
        default=None,
        json_schema_extra={
            "relationship": RelationshipInfo(
                resource_type="beta",
                many=True,
            ),
        },
    )

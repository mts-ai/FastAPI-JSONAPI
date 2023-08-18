from typing import Dict, List, Optional
from uuid import UUID

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


class UserBioBaseSchema(BaseModel):
    """UserBio base schema."""

    class Config:
        """Pydantic schema config."""

        orm_mode = True

    birth_city: str
    favourite_movies: str
    keys_to_ids_list: Dict[str, List[int]] = None


class UserBioSchema(UserBioBaseSchema):
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


class ParentToChildAssociationSchema(BaseModel):
    id: int
    extra_data: str
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


class ParentBaseSchema(BaseModel):
    """Parent base schema."""

    class Config:
        """Pydantic schema config."""

        orm_mode = True

    name: str

    children: List["ParentToChildAssociationSchema"] = Field(
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


class ChildBaseSchema(BaseModel):
    """Child base schema."""

    class Config:
        """Pydantic schema config."""

        orm_mode = True

    name: str

    parents: List["ParentToChildAssociationSchema"] = Field(
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


class ComputerBaseSchema(BaseModel):
    """Computer base schema."""

    class Config:
        """Pydantic schema config."""

        orm_mode = True

    name: str
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


class IdCastSchema(BaseModel):
    id: UUID = Field(client_can_set_id=True)


class SelfRelationshipSchema(BaseModel):
    name: str
    self_relationship: Optional["SelfRelationshipSchema"] = Field(
        relationship=RelationshipInfo(
            resource_type="self_relationship",
        ),
    )

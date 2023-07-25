from typing import Dict, List, Optional

from fastapi_jsonapi.schema_base import BaseModel, Field, RelationshipInfo


class UserBaseSchema(BaseModel):
    """User base schema."""

    class Config:
        """Pydantic schema config."""

        orm_mode = True

    name: str
    age: Optional[int] = None
    email: Optional[str] = None


class UserPatchSchema(UserBaseSchema):
    """User PATCH schema."""


class UserInSchema(UserBaseSchema):
    """User input schema."""


class UserSchema(UserInSchema):
    """User item schema."""

    id: int
    posts: List["PostSchema"] = Field(
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

    computers: Optional["ComputerSchema"] = Field(
        relationship=RelationshipInfo(
            resource_type="computer",
            many=True,
        ),
    )


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


class PostBaseSchema(BaseModel):
    """Post base schema."""

    class Config:
        """Pydantic schema config."""

        orm_mode = True

    title: str
    body: str


class PostPatchSchema(PostBaseSchema):
    """Post PATCH schema."""


class PostInSchema(PostBaseSchema):
    """Post input schema."""


class PostSchema(PostInSchema):
    """Post item schema."""

    id: int
    user: "UserSchema" = Field(
        relationship=RelationshipInfo(
            resource_type="user",
        ),
    )
    comments: List["PostCommentSchema"] = Field(
        relationship=RelationshipInfo(
            resource_type="post_comment",
            many=True,
        ),
    )


# Post Comment Schemas ⬇️


class PostCommentBaseSchema(BaseModel):
    """PostComment base schema."""

    class Config:
        """Pydantic schema config."""

        orm_mode = True

    text: str


class PostCommentPatchSchema(PostCommentBaseSchema):
    """PostComment PATCH schema."""


class PostCommentInSchema(PostCommentBaseSchema):
    """PostComment input schema."""


class PostCommentSchema(PostCommentInSchema):
    """PostComment item schema."""

    id: int
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


class ParentPatchSchema(ParentBaseSchema):
    """Parent PATCH schema."""


class ParentInSchema(ParentBaseSchema):
    """Parent input schema."""


class ParentSchema(ParentInSchema):
    """Parent item schema."""

    id: int
    children: List["ParentToChildAssociationSchema"] = Field(
        relationship=RelationshipInfo(
            resource_type="parent_child_association",
            many=True,
        ),
    )


# Child Schemas ⬇️


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

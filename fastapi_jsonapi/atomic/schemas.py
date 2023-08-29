from typing import List, Literal, Optional, Union

from pydantic import BaseModel, Field, root_validator
from starlette.datastructures import URLPath


class OperationRelationshipSchema(BaseModel):
    id: str = Field(default=..., description="Related object ID")
    type: str = Field(default=..., description="Type of the related resource object")


class OperationItemInSchema(BaseModel):
    """
    add/update
    """

    type: str = Field(default=..., description="Resource type")
    id: Optional[str] = Field(default=None, description="Resource object ID")
    attributes: Optional[dict] = Field(None, description="Resource object attributes")
    relationships: Optional[dict] = Field(None, description="Resource object relationships")


class AtomicOperationRef(BaseModel):
    """

    ref: an object that MUST contain one of the following combinations of members:
        type and id: to target an individual resource.
        type and lid: to target an individual resource
            that has been assigned a local identity (lid) in a prior operation object.
        type, id, and relationship: to target the relationship of an individual resource.
        type, lid, and relationship: to target the relationship of an individual resource
            that has been assigned a local identity (lid) in a prior operation object.
    """

    type: str = Field(default=...)
    id: Optional[str] = Field(default=None)
    lid: Optional[str] = Field(default=None)
    relationship: Optional[str] = Field(default=None)

    @root_validator
    def validate_atomic_operation_ref(cls, values: dict):
        """
        type is required on schema
        so id or lid has to be present

        :param values:
        :return:
        """
        if (
            # XOR
            bool(values.get("lid"))
            != bool(values.get("id"))
        ):
            # if one of id/lid is present, ref is ok
            return values

        msg = (
            "invalid operation ref. has to be one of:\n"
            "- (type, id)\n"
            "- (type, lid)\n"
            "- (type, id, relationship)\n"
            "- (type, lid, relationship)"
        )
        # TODO: pydantic V2
        raise ValueError(msg)


class AtomicOperation(BaseModel):
    """
    An operation object MUST contain the following member: op

    An operation object MAY contain either of the following members: (ref, href),
    but not both, to specify the target of the operation:

    An operation object MAY also contain any of the following members: (data, meta),
    data: the operation’s “primary data”.
    meta: a meta object that contains non-standard meta-information about the operation.

    https://jsonapi.org/ext/atomic/#operation-objects
    """

    op: Literal["add", "update", "remove"] = Field(
        default=...,
        description="an operation code, expressed as a string, that indicates the type of operation to perform.",
    )
    ref: Optional[AtomicOperationRef] = Field(default=None)
    href: Optional[URLPath] = Field(
        default=None,
        description="a string that contains a URI-reference that identifies the target of the operation.",
    )

    data: Union[
        # from biggest to smallest!
        # any object creation
        OperationItemInSchema,
        # to-many relationship
        List[OperationRelationshipSchema],
        # to-one relationship
        OperationRelationshipSchema,
        # not required
        None,
    ] = Field(default=None, description="the operation’s “primary data”.")

    meta: Optional[dict] = Field(
        default=None,
        description="a meta object that contains non-standard meta-information about the operation",
    )

    @root_validator
    def validate_operation(cls, values: dict):
        """
        An operation object MAY contain either of the following members,
        but not both, to specify the target of the operation: (ref, href)

        :param values:
        :return:
        """
        ref = values.get("ref")
        href = values.get("href")
        if not ref and not href:
            # if no one is passed, it's OK
            return values

        # XOR
        if bool(ref) != bool(href):
            # if one of ref/href is present, it's ok
            return values

        msg = (
            "An operation object MAY contain either of the following members,"
            "but not both, to specify the target of the operation (ref, href)"
        )
        # TODO: pydantic V2
        raise ValueError(msg)


class AtomicOperationRequest(BaseModel):
    operations: List[AtomicOperation] = Field(
        alias="atomic:operations",
        min_items=1,
    )


class AtomicResult(BaseModel):
    data: Optional[dict] = Field(
        default=None,
        description="the “primary data” resulting from the operation.",
    )
    meta: Optional[dict] = Field(
        default=None,
        description="a meta object that contains non-standard meta-information about the result.",
    )


class AtomicResultResponse(BaseModel):
    """
    https://jsonapi.org/ext/atomic/#auto-id-responses-4
    """

    results: List[AtomicResult] = Field(
        alias="atomic:results",
        min_items=1,
    )

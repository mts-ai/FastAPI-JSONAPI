from __future__ import annotations

from enum import Enum
from typing import Any, Union

from pydantic import BaseModel, Field, model_validator

from fastapi_jsonapi.utils import logical_xor


class OperationRelationshipSchema(BaseModel):
    id: str = Field(default=..., description="Related object ID")
    type: str = Field(default=..., description="Type of the related resource object")


class OperationItemInSchema(BaseModel):
    """
    add/update
    """

    type: str = Field(default=..., description="Resource type")
    id: str | None = Field(default=None, description="Resource object ID")
    lid: str | None = Field(default=None, description="Resource object local ID")
    attributes: dict | None = Field(None, description="Resource object attributes")
    relationships: dict | None = Field(None, description="Resource object relationships")


OperationDataType = Union[
    # from biggest to smallest!
    # any object creation
    OperationItemInSchema,
    # to-many relationship
    list[OperationRelationshipSchema],
    # to-one relationship
    OperationRelationshipSchema,
    # not required
    None,
]


class AtomicOperationRef(BaseModel):
    """
    This schema represents operation ref - reference to a resource

    ref: an object that MUST contain one of the following combinations of members:
        type and id: to target an individual resource.
        type and lid: to target an individual resource
            that has been assigned a local identity (lid) in a prior operation object.
        type, id, and relationship: to target the relationship of an individual resource.
        type, lid, and relationship: to target the relationship of an individual resource
            that has been assigned a local identity (lid) in a prior operation object.
    """

    type: str = Field(default=...)
    id: str | None = Field(default=None)
    lid: str | None = Field(default=None)
    relationship: str | None = Field(default=None)

    @model_validator(mode="before")
    def validate_atomic_operation_ref(cls, values: dict):
        """
        type is required on schema, so id or lid has to be present

        :param values:
        :return:
        """
        if logical_xor(values.get("lid"), values.get("id")):
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


class AtomicOperationAction(str, Enum):
    add = "add"
    update = "update"
    remove = "remove"


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

    op: AtomicOperationAction = Field(
        default=...,
        description="an operation code, expressed as a string, that indicates the type of operation to perform.",
    )
    ref: AtomicOperationRef | None = Field(default=None)
    href: str | None = Field(
        default=None,
        description="a string that contains a URI-reference that identifies the target of the operation.",
    )

    data: OperationDataType = Field(
        default=None,
        description="the operation’s “primary data”.",
    )

    meta: dict | None = Field(
        default=None,
        description="a meta object that contains non-standard meta-information about the operation",
    )

    @classmethod
    def _validate_one_of_ref_or_href(cls, values: dict):
        """
        Make sure ref confirms spec

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

    @classmethod
    def _get_value_from_dict_or_obj(cls, obj: Any, key: str):
        if hasattr(obj, key):
            return getattr(obj, key)
        if isinstance(obj, dict) and key in obj:
            return obj[key]
        return None

    @model_validator(mode="before")
    def validate_operation(cls, values: dict):
        """
        Make sure atomic operation request conforms the spec

        :param values:
        :return:
        """
        cls._validate_one_of_ref_or_href(values=values)
        op = values.get("op")
        ref: AtomicOperationRef | None = values.get("ref")
        if op == AtomicOperationAction.remove:
            if not ref:
                msg = f"ref should be present for action {op!r}"
                raise ValueError(msg)
            # when updating / removing item, ref [l]id has to be present
            id_value = cls._get_value_from_dict_or_obj(ref, "id")
            lid_value = cls._get_value_from_dict_or_obj(ref, "lid")

            if not id_value and not lid_value:
                msg = f"id or local id has to be present for action {op!r}"
                raise ValueError(msg)

        data: OperationDataType = values.get("data")
        operation_type = (
            # take from ref
            cls._get_value_from_dict_or_obj(ref, "type")
            or
            # or take from data
            cls._get_value_from_dict_or_obj(data, "type")
        )
        if not operation_type:
            msg = "Operation has to be in ref or in data"
            raise ValueError(msg)

        return values


class AtomicOperationRequest(BaseModel):
    operations: list[AtomicOperation] = Field(
        alias="atomic:operations",
        min_length=1,
    )


class AtomicResult(BaseModel):
    data: dict | None = Field(
        default=None,
        description="the “primary data” resulting from the operation.",
    )
    meta: dict | None = Field(
        default=None,
        description="a meta object that contains non-standard meta-information about the result.",
    )


class AtomicResultResponse(BaseModel):
    """
    https://jsonapi.org/ext/atomic/#auto-id-responses-4
    """

    results: list[AtomicResult] = Field(
        alias="atomic:results",
        min_length=1,
    )

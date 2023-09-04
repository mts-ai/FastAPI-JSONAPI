from dataclasses import dataclass
from typing import List, Literal, Union

from fastapi_jsonapi import RoutersJSONAPI
from fastapi_jsonapi.atomic.schemas import OperationItemInSchema, OperationRelationshipSchema
from fastapi_jsonapi.data_layers.base import BaseDataLayer
from fastapi_jsonapi.views.view_base import ViewBase


@dataclass
class PreparedOperation:
    action: Literal["add", "update", "remove"]
    data_layer: "BaseDataLayer"
    view: "ViewBase"
    jsonapi: RoutersJSONAPI
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
    ] = None

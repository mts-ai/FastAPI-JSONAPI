from typing import Iterable, Optional, Type, Union

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

from fastapi_jsonapi.data_typing import TypeModel, TypeSchema
from fastapi_jsonapi.views import Operation, ViewBase


class ResourceData(BaseModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
    )

    path: Union[str, list[str]]
    router: Optional[APIRouter]
    tags: list[str]
    view: Type[ViewBase]
    model: Type[TypeModel]
    source_schema: Type[TypeSchema]
    schema_in_post: Optional[Type[BaseModel]]
    schema_in_post_data: Type[BaseModel]
    schema_in_patch: Optional[Type[BaseModel]]
    schema_in_patch_data: Type[BaseModel]
    detail_response_schema: Type[BaseModel]
    list_response_schema: Type[BaseModel]
    pagination_default_size: Optional[int] = 25
    pagination_default_number: Optional[int] = 1
    pagination_default_offset: Optional[int] = None
    pagination_default_limit: Optional[int] = None
    operations: Iterable[Operation] = ()
    ending_slash: bool = True

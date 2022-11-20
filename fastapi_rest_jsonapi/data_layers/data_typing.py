from typing import TypeVar

from pydantic import BaseModel

TypeQuery = TypeVar("TypeQuery")
TypeModel = TypeVar("TypeModel")
TypeSchema = TypeVar("TypeSchema", bound=BaseModel)

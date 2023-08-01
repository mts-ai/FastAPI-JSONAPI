from typing import TypeVar

from pydantic import BaseModel

TypeModel = TypeVar("TypeModel")
TypeSchema = TypeVar("TypeSchema", bound=BaseModel)

from fastapi import FastAPI
from pydantic import BaseModel, Field

from fastapi_jsonapi import RoutersJSONAPI


class PersonAttributesSchema(BaseModel):
    name: str


class PersonSchemaIn(BaseModel):
    id: int = Field(client_can_set_id=True)


app = FastAPI()

RoutersJSONAPI(
    app,
    # ...
    schema_in_post=PersonSchemaIn,
    # ...
)

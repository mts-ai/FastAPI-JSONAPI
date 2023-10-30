from typing import Type

# from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm.attributes import InstrumentedAttribute

# from sqlalchemy import JSON
from sqlalchemy.sql.sqltypes import JSON

from fastapi_jsonapi.data_typing import TypeModel


def get_related_model_cls(cls: Type[TypeModel], relation_name: str) -> Type[TypeModel]:
    """

    SQLA Get related model class
    User.computers -> Computer

    # todo: use alias (custom names)?
       For example:

    class Computer(sqla_base):
        user = relationship(User)

    class ComputerSchema(pydantic_base):
        owner = Field(alias="user", relationship=...)

    :param cls:
    :param relation_name:
    :return:
    """
    related_column: InstrumentedAttribute = getattr(cls, relation_name)
    # TODO: any flags for JSON / JSONB?
    # TODO: or any plugins to add support for JSON / JSONB, etc?
    # TODO: https://github.com/AdCombo/combojsonapi/blob/45a43cf28c6496195c6e6762955db16f9a813b2f/combojsonapi/postgresql_jsonb/plugin.py#L103-L120
    # todo: check for json[b]
    # if isinstance(related_column.type) in (JSON, ...):  # TODO!!
    if isinstance(related_column.type, JSON):
        # return related_column.op("->>")
        return related_column

    related_property = related_column.property
    return related_property.mapper.class_

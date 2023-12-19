from typing import Type

from fastapi_jsonapi.data_typing import TypeModel


def get_related_model_cls(cls: Type[TypeModel], relation_name: str) -> Type[TypeModel]:
    """
    Get related model from SQLAlchemy model

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
    return getattr(cls, relation_name).property.mapper.class_

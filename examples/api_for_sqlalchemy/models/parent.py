from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from examples.api_for_sqlalchemy.extensions.sqlalchemy import Base
from examples.api_for_sqlalchemy.utils.sqlalchemy.base_model_mixin import BaseModelMixin


class Parent(Base, BaseModelMixin):
    __tablename__ = "left_table_parents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    children = relationship(
        "ParentToChildAssociation",
        back_populates="parent",
    )

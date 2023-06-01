from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from examples.api_for_sqlalchemy.extensions.sqlalchemy import Base
from examples.api_for_sqlalchemy.utils.sqlalchemy.base_model_mixin import BaseModelMixin


class Child(Base, BaseModelMixin):
    __tablename__ = "right_table_children"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    parents = relationship(
        "ParentToChildAssociation",
        back_populates="child",
    )

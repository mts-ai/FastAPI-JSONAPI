from sqlalchemy.orm import Mapped, mapped_column, relationship

from examples.api_for_sqlalchemy.extensions.sqlalchemy import Base
from examples.api_for_sqlalchemy.models import ParentToChildAssociation
from examples.api_for_sqlalchemy.utils.sqlalchemy.base_model_mixin import BaseModelMixin


class Child(Base, BaseModelMixin):
    __tablename__ = "right_table_children"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(nullable=False)
    parents: Mapped["ParentToChildAssociation"] = relationship(
        "ParentToChildAssociation",
        back_populates="child",
    )

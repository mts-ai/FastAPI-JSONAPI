from sqlalchemy import Column, ForeignKey, Index, Integer, String
from sqlalchemy.orm import relationship

from examples.api_for_sqlalchemy.extensions.sqlalchemy import Base
from examples.api_for_sqlalchemy.utils.sqlalchemy.base_model_mixin import BaseModelMixin


class ParentToChildAssociation(Base, BaseModelMixin):
    __table_args__ = (
        # JSON:API requires `id` field on any model,
        # so we can't create a composite PK here
        # that's why we need to create this index
        Index(
            "ix_parent_child_association_unique",
            "parent_left_id",
            "child_right_id",
            unique=True,
        ),
    )

    __tablename__ = "parent_to_child_association_table"

    id = Column(Integer, primary_key=True, autoincrement=True)

    parent_left_id = Column(
        ForeignKey("left_table_parents.id"),
        nullable=False,
    )
    child_right_id = Column(
        ForeignKey("right_table_children.id"),
        nullable=False,
    )
    extra_data = Column(String(50))
    parent = relationship(
        "Parent",
        back_populates="children",
        # primaryjoin="ParentToChildAssociation.parent_left_id == Parent.id",
    )
    child = relationship(
        "Child",
        back_populates="parents",
        # primaryjoin="ParentToChildAssociation.child_right_id == Child.id",
    )

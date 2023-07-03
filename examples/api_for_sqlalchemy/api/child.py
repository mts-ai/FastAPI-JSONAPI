from fastapi import Depends

from examples.api_for_sqlalchemy.extensions.sqlalchemy import Connector
from fastapi_jsonapi.misc.sqla.generics.base import DetailViewBaseGeneric, ListViewBaseGeneric


class ChildDetail(DetailViewBaseGeneric):
    session_dependency = Depends(Connector.get_session)


class ChildList(ListViewBaseGeneric):
    session_dependency = Depends(Connector.get_session)

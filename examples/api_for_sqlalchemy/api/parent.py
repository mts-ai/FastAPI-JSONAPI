from fastapi import Depends

from examples.api_for_sqlalchemy.extensions.sqlalchemy import Connector
from fastapi_jsonapi.misc.sqla.generics.base import DetailViewBaseGeneric, ListViewBaseGeneric


class ParentDetail(DetailViewBaseGeneric):
    session_dependency = Depends(Connector.get_session)


class ParentList(ListViewBaseGeneric):
    session_dependency = Depends(Connector.get_session)

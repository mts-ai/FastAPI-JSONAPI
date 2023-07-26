from fastapi import Depends
from pytest import fixture  # noqa
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi_jsonapi.misc.sqla.generics.base import (
    DetailViewBaseGeneric as DetailViewBaseGenericHelper,
)
from fastapi_jsonapi.misc.sqla.generics.base import (
    ListViewBaseGeneric as ListViewBaseGenericHelper,
)


@fixture(scope="class")
def detail_view_base_generic(async_session_dependency):
    class DetailViewBaseGeneric(DetailViewBaseGenericHelper):
        async def init_dependencies(self, session: AsyncSession = Depends(async_session_dependency)):
            self.session = session

    return DetailViewBaseGeneric


@fixture(scope="class")
def list_view_base_generic(async_session_dependency):
    class ListViewBaseGeneric(ListViewBaseGenericHelper):
        async def init_dependencies(self, session: AsyncSession = Depends(async_session_dependency)):
            self.session = session

    return ListViewBaseGeneric


@fixture(scope="class")
def list_view_base_generic_helper_for_sqla(async_session_dependency):
    class ListViewBaseGeneric(ListViewBaseGenericHelper):
        async def init_dependencies(self, session: AsyncSession = Depends(async_session_dependency)):
            self.session = session

    return ListViewBaseGeneric


# User ⬇️


@fixture(scope="class")
def user_detail_view(detail_view_base_generic):
    """
    :param detail_view_base_generic:
    :return:
    """

    class UserDetail(detail_view_base_generic):
        ...

    return UserDetail


@fixture(scope="class")
def user_list_view(list_view_base_generic_helper_for_sqla):
    """
    :param list_view_base_generic_helper_for_sqla:
    :return:
    """

    class UserList(list_view_base_generic_helper_for_sqla):
        ...

    return UserList


# User Bio ⬇️


@fixture(scope="class")
def user_bio_detail_view(detail_view_base_generic):
    """
    :param detail_view_base_generic:
    :return:
    """

    class UserBioDetail(detail_view_base_generic):
        ...

    return UserBioDetail


@fixture(scope="class")
def user_bio_list_view(list_view_base_generic):
    """
    :param list_view_base_generic:
    :return:
    """

    class UserBioList(list_view_base_generic):
        ...

    return UserBioList


# Post ⬇️


@fixture(scope="class")
def post_detail_view(detail_view_base_generic):
    """
    :param detail_view_base_generic:
    :return:
    """

    class PostDetail(detail_view_base_generic):
        ...

    return PostDetail


@fixture(scope="class")
def post_list_view(list_view_base_generic):
    """
    :param list_view_base_generic:
    :return:
    """

    class PostList(list_view_base_generic):
        ...

    return PostList


# Parent ⬇️


@fixture(scope="class")
def parent_detail_view(detail_view_base_generic):
    """
    :param detail_view_base_generic:
    :return:
    """

    class ParentDetail(detail_view_base_generic):
        ...

    return ParentDetail


@fixture(scope="class")
def parent_list_view(list_view_base_generic):
    """
    :param list_view_base_generic:
    :return:
    """

    class ParentList(list_view_base_generic):
        ...

    return ParentList


# Child ⬇️


@fixture(scope="class")
def child_detail_view(detail_view_base_generic):
    """
    :param detail_view_base_generic:
    :return:
    """

    class ChildDetail(detail_view_base_generic):
        ...

    return ChildDetail


@fixture(scope="class")
def child_list_view(list_view_base_generic):
    """
    :param list_view_base_generic:
    :return:
    """

    class ChildList(list_view_base_generic):
        ...

    return ChildList


@fixture(scope="class")
def computer_detail_view(detail_view_base_generic):
    """
    :param detail_view_base_generic:
    :return:
    """

    class ComputerDetail(detail_view_base_generic):
        ...

    return ComputerDetail


@fixture(scope="class")
def computer_list_view(list_view_base_generic):
    """
    :param detail_view_base_generic:
    :return:
    """

    class ComputerList(list_view_base_generic):
        ...

    return ComputerList

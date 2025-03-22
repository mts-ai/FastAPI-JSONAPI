import logging
from typing import Any, Iterable, Literal, Optional, Type, Union

from sqlalchemy import and_, delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select, column, distinct
from sqlalchemy.sql.elements import UnaryExpression
from sqlalchemy.sql.expression import BinaryExpression

from fastapi_jsonapi.data_layers.sqla.query_building import RelationshipInfo
from fastapi_jsonapi.data_typing import TypeModel
from fastapi_jsonapi.exceptions import BadRequest, InternalServerError, ObjectNotFound

log = logging.getLogger(__name__)


class BaseSQLA:
    @classmethod
    def _check_field_exists(
        cls,
        model: TypeModel,
        key: str,
    ) -> None:
        try:
            getattr(model, key)
        except AttributeError as ex:
            err_message = f"No fields `{key}` on `{type(model).__name__}`. Make sure schema conforms model."
            log.exception(err_message, exc_info=ex)
            raise InternalServerError(
                detail=err_message,
                pointer="/data",
            )

    @classmethod
    def _fill(
        cls,
        model: TypeModel,
        **kwargs,
    ) -> None:
        for key, value in kwargs.items():
            cls._check_field_exists(model, key)
            setattr(model, key, value)

    @classmethod
    async def _save(
        cls,
        session: AsyncSession,
        model: TypeModel,
        action_trigger: Literal["update", "create", "delete"],
        resource_type: str,
        commit: bool = True,
        id_: Optional[str] = None,
        **kwargs,
    ) -> TypeModel:
        try:
            if not commit:
                await session.flush()
                return model

            await session.commit()
            return model
        except IntegrityError as ex:
            err_message = f"Could not {action_trigger} object"
            log.exception("%s with data %s", err_message, kwargs, exc_info=ex)
            raise BadRequest(
                detail=err_message,
                pointer="/data",
                meta={
                    "type": resource_type,
                    "id": id_,
                },
            )
        except Exception as ex:
            err_message = f"Got an error {ex.__class__.__name__} during updating obj {kwargs} data in DB"
            log.exception(err_message, exc_info=ex)
            await session.rollback()
            raise InternalServerError(
                detail=err_message,
                pointer="/data",
                meta={
                    "type": resource_type,
                    "id": id_,
                },
            )

    @classmethod
    async def all(
        cls,
        session: AsyncSession,
        stmt: Select,
    ) -> Union[Type[TypeModel], Any]:
        return (await session.execute(stmt)).unique().scalars().all()

    @classmethod
    async def count(
        cls,
        session: AsyncSession,
        stmt: Select,
        id_field_name: str = "id",
    ) -> int:
        stmt = select(func.count(distinct(column(id_field_name)))).select_from(stmt.subquery())
        return (await session.execute(stmt)).scalar_one()

    @classmethod
    async def create(
        cls,
        session: AsyncSession,
        model: TypeModel,
        resource_type: str,
        commit: bool = True,
        id_: Optional[str] = None,
        **kwargs,
    ) -> TypeModel:
        cls._fill(model, **kwargs)
        session.add(model)
        return await cls._save(
            session=session,
            model=model,
            action_trigger="create",
            resource_type=resource_type,
            commit=commit,
            id_=id_,
            **kwargs,
        )

    @classmethod
    async def delete(
        cls,
        session: AsyncSession,
        model: TypeModel,
        filters: list[Union[BinaryExpression, bool]],
        resource_type: str,
        commit: bool = True,
        id_: Optional[str] = None,
        **kwargs,
    ) -> None:
        await session.execute(delete(model).where(*filters))
        await cls._save(
            session=session,
            model=model,
            action_trigger="delete",
            resource_type=resource_type,
            commit=commit,
            id_=id_,
            **kwargs,
        )

    @classmethod
    async def one_or_raise(
        cls,
        session: AsyncSession,
        model: TypeModel,
        filters: list[Union[BinaryExpression, bool]],
        stmt: Select,
    ) -> Union[TypeModel, Any]:
        result = (await session.execute(stmt)).scalar_one_or_none()
        if result is None:
            compiled_conditions = and_(*filters).compile(
                dialect=session.bind.dialect,
                compile_kwargs={"literal_binds": True},
            )
            raise ObjectNotFound(
                detail=f"Resource {model.__name__} `{compiled_conditions}` not found",
            )
        return result

    @classmethod
    def query(
        cls,
        model: TypeModel,
        fields: Optional[list] = None,
        select_from: Optional[TypeModel] = None,
        distinct_: bool = False,
        filters: Optional[list[Union[BinaryExpression, bool]]] = None,
        for_update: Optional[dict] = None,
        join: Optional[list[tuple[TypeModel, Any]]] = None,
        jsonapi_join: Optional[list[RelationshipInfo]] = None,
        number: Optional[int] = None,
        options: Iterable = (),
        order: Optional[Union[str, UnaryExpression]] = None,
        size: Optional[int] = None,
        stmt: Optional[Select] = None,
    ) -> Select:
        if stmt is None:
            stmt = select(model) if fields is None else select(*fields)

        if select_from is not None:
            stmt = stmt.select_from(select_from)

        if filters is not None:
            stmt = stmt.where(*filters)

        if options:
            stmt = stmt.options(*options)

        if for_update is not None:
            stmt = stmt.with_for_update(**for_update)

        if order is not None:
            stmt = stmt.order_by(*order)

        if jsonapi_join:
            for relationship_info in jsonapi_join:
                stmt = stmt.join(relationship_info.aliased_model, relationship_info.join_column)

        if size not in [0, None]:
            stmt = stmt.limit(size)
            number = number or 1
            stmt = stmt.offset((number - 1) * size)

        if distinct_:
            stmt = stmt.distinct()

        if join is not None:
            for join_model, predicate in join:
                stmt = stmt.join(join_model, predicate)

        return stmt

    @classmethod
    async def update(
        cls,
        session: AsyncSession,
        model: TypeModel,
        resource_type: str,
        commit: bool = True,
        id_: Optional[str] = None,
        **kwargs,
    ) -> TypeModel:
        cls._fill(model, **kwargs)
        session.add(model)
        return await cls._save(
            session=session,
            model=model,
            action_trigger="update",
            resource_type=resource_type,
            commit=commit,
            id_=id_,
            **kwargs,
        )

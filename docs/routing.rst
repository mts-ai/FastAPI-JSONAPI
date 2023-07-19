.. _routing:

Routing
=======

.. currentmodule:: fastapi_jsonapi

Example:

.. code-block:: python

    TODO!

    def add_routes(app: FastAPI) -> List[Dict[str, Any]]:
        tags = [
            {
                "name": "User",
                "description": "",
            },
        ]

        routers: APIRouter = APIRouter()
        RoutersJSONAPI(
            routers=routers,
            path="/user",
            tags=["User"],
            class_detail=UserDetail,
            class_list=UserList,
            schema=UserSchema,
            resource_type="user",
            schema_in_patch=UserPatchSchema,
            schema_in_post=UserInSchema,
            model=User,
        )

        app.include_router(routers, prefix="")
        return tags

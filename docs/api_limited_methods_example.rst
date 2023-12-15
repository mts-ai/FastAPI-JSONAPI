.. _api_limited_methods_example:

Limit API methods
#################

Sometimes you won't need all the CRUD methods.
For example, you want to create only GET, POST and GET LIST methods,
so user can't update or delete any items.


Set ``methods`` on Routers registration:

.. code-block:: python

    RoutersJSONAPI(
        router=router,
        path="/user",
        tags=["User"],
        class_detail=UserDetailView,
        class_list=UserListView,
        schema=UserSchema,
        model=User,
        resource_type="user",
        methods=[
            RoutersJSONAPI.Methods.GET_LIST,
            RoutersJSONAPI.Methods.POST,
            RoutersJSONAPI.Methods.GET,
        ],
    )


Full code example:

.. literalinclude:: ../examples/api_limited_methods.py
    :language: python

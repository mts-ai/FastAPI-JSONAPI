.. _api_limited_methods_example:

Limit API methods
#################

Sometimes you won't need all the CRUD methods.
For example, you want to create only GET, POST and GET LIST methods,
so user can't update or delete any items.


Set ``operations`` on Routers registration:

.. code-block:: python

    builder = ApplicationBuilder(app)
    builder.add_resource(
        router=router,
        path="/users",
        tags=["User"],
        view=UserView,
        schema=UserSchema,
        model=User,
        resource_type="user",
        operations=[
            Operation.GET_LIST,
            Operation.POST,
            Operation.GET,
        ],
    )


This will limit generated views to:

========================  ======  =============  ===========================
URL                       method  endpoint       Usage
========================  ======  =============  ===========================
/users                    GET     user_list      Get a collection of users
/users                    POST    user_list      Create a user
/users/{user_id}          GET     user_detail    Get user details
========================  ======  =============  ===========================


Full code example (should run "as is"):

.. literalinclude:: ../examples/api_limited_methods.py
    :language: python

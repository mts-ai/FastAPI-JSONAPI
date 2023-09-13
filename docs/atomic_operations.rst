.. _atomic_operations:

Atomic Operations
=================

.. currentmodule:: fastapi_jsonapi


Atomic Operations allows to perform multiple “operations” in a linear and atomic manner.
Operations are a serialized form of the mutations allowed in the base JSON:API specification.

Clients can send an array of operations in a single request.
This extension guarantees that those operations will be processed in order and will either completely succeed or fail together.


What can I do?
--------------

Atomic operations extension supports these three actions:

* ``add`` - create a new object
* ``update`` - update any existing object
* ``remove`` - delete any existing object

You can send one or more atomic operations in one request.

If anything fails in one of the operations, everything will be rolled back.

.. note::
    Only SQLAlchemy data layer supports atomic operations right now.
    Feel free to send PRs to add support for other data layers.


Configuration
-------------

You need to include atomic router:

.. code-block:: python

    from fastapi import FastAPI
    from fastapi_jsonapi.atomic import AtomicOperations


    def add_routes(app: FastAPI):
        atomic = AtomicOperations()
        app.include_router(atomic.router)

Default path for atomic operations is ``/operations``


There's a way to customize url path, you can also pass your custom APIRouter:

.. code-block:: python

    from fastapi import APIRouter
    from fastapi_jsonapi.atomic import AtomicOperations

    my_router = APIRouter(prefix="/qwerty", tags=["Atomic Operations"])

    AtomicOperations(
        # you can pass custom url path
        url_path="/atomic",
        # also you can pass your custom router
        router=my_router,
    )


Create some objects
-------------------

Create two objects, they are not linked anyhow:

Request:

.. literalinclude:: ./http_snippets/snippets/example_atomic_one__create_computer_and_separate_user
  :language: HTTP

Response:

.. literalinclude:: ./http_snippets/snippets/example_atomic_one__create_computer_and_separate_user_result
  :language: HTTP



Update object
-------------

Update details
^^^^^^^^^^^^^^

Atomic operations array has to contain at least one operation.
Body in each atomic action has to be as in other regular requests.
For example, update any existing object:


.. literalinclude:: ./http_snippets/snippets/example_atomic_two__update_user
  :language: HTTP

Response:

.. literalinclude:: ./http_snippets/snippets/example_atomic_two__update_user_result
  :language: HTTP


Update details and relationships
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. warning::
    There may be issues when updating to-many relationships. This feature is not fully-tested yet.

Update already any existing computer and link it to any existing user:


Request:

.. literalinclude:: ./http_snippets/snippets/example_atomic_two__update_computer
  :language: HTTP

Response:

.. literalinclude:: ./http_snippets/snippets/example_atomic_two__update_computer_result
  :language: HTTP


You can check that details and relationships are updated by fetching the object and related objects:


Request:

.. literalinclude:: ./http_snippets/snippets/example_atomic_two__after_update_computer_check_details
  :language: HTTP

Response:

.. literalinclude:: ./http_snippets/snippets/example_atomic_two__after_update_computer_check_details_result
  :language: HTTP



Remove object
-------------


Operations include remove object action
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

You can mix any actions, for example you can create, update, remove at the same time:

Request:

.. literalinclude:: ./http_snippets/snippets/example_atomic_five__mixed_actions
  :language: HTTP

Response:

.. literalinclude:: ./http_snippets/snippets/example_atomic_five__mixed_actions_result
  :language: HTTP


All operations remove objects
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If all actions are to delete objects, empty response will be returned:


Request:

.. literalinclude:: ./http_snippets/snippets/example_atomic_five__only_remove_actions
  :language: HTTP

Response:

.. literalinclude:: ./http_snippets/snippets/example_atomic_five__only_remove_actions_result
  :language: HTTP



Local identifier
----------------

Sometimes you need to create an object, create another object and link it to the first one:

Create user and create bio for this user:

Request:

.. literalinclude:: ./http_snippets/snippets/example_atomic_three__create_user_and_user_bio
  :language: HTTP

Response:

.. literalinclude:: ./http_snippets/snippets/example_atomic_three__create_user_and_user_bio_result
  :language: HTTP



Many to many with local identifier
----------------------------------

If you have many-to-many association (:ref:`examples with many-to-many <include_many_to_many>`),
atomic operations should look like this:


Request:

.. literalinclude:: ./http_snippets/snippets/example_atomic_four__create_many-to-many
  :language: HTTP

Response:

.. literalinclude:: ./http_snippets/snippets/example_atomic_four__create_many-to-many_result
  :language: HTTP


Check that objects and relationships were created. Pass includes in the url path, like this
``/parent-to-child-association/1?include=parent,child``


Request:

.. literalinclude:: ./http_snippets/snippets/example_atomic_four__get-many-to-many_with_includes
  :language: HTTP

Response:

.. literalinclude:: ./http_snippets/snippets/example_atomic_four__get-many-to-many_with_includes_result
  :language: HTTP




Errors
------

If any action on the operations list fails, everything will be rolled back
and an error will be returned. Example:


Request:

.. literalinclude:: ./http_snippets/snippets/example_atomic_fail__create_computer_and_update_user_bio
  :language: HTTP

Response:

.. literalinclude:: ./http_snippets/snippets/example_atomic_fail__create_computer_and_update_user_bio_result
  :language: HTTP


Since ``update`` action requires ``id`` field and user-bio update schema requires ``birth_city`` field,
the app rollbacks all actions and computer is not saved in DB (and user-bio is not updated).

Error is not in JSON:API style yet, PRs are welcome.


Notes
-----


.. note::
    See `examples for SQLAlchemy <SQLA_examples>`_ in the repo, all examples are based on it.


.. warning::
    Field "href" is not supported yet. Resource can be referenced only by the "type" field.

    Relationships resources are not implemented yet,
    so updating relationships directly through atomic operations
    is not supported too (see skipped tests).

    Includes in the response body are not supported (and not planned, until you PR it)

.. _SQLA_examples: https://github.com/mts-ai/FastAPI-JSONAPI/tree/main/examples/api_for_sqlalchemy

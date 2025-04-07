.. _client_generated_id:

Client generated id
===================

.. currentmodule:: fastapi_jsonapi

According to the specification `JSON:API doc <https://jsonapi.org/format/#crud-creating-client-ids>`_
it is possible to create an ``id`` on the client and pass
it to the server. Let's define the id type as a UUID.

Request:

.. literalinclude:: ./http_snippets/snippets/client_generated_id__create_user
  :language: http

Response:

.. literalinclude:: ./http_snippets/snippets/client_generated_id__create_user_result
  :language: http


In order to do this you need to define an ``id`` with the Field keyword **client_can_set_id** in the
``schema`` or ``schema_in_post``.

Example:

.. literalinclude:: ./python_snippets/client_generated_id/schematic_example.py
  :language: python

In case the key **client_can_set_id** is not set, the ``id`` field will be ignored in post requests.

In fact, the library deviates slightly from the specification and allows you to use any type, not just UUID.
Just define the one you need in the Pydantic model to do it.

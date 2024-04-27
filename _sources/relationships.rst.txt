.. _relationships:

Define relationships
====================

.. currentmodule:: fastapi_jsonapi

As noted in quickstart, objects can accept a relationships. In order to make it technically
possible to create, update, and modify relationships, you must declare a **RelationShipInfo** when
creating a schema.

As an example, let's say you have a user model, their biography, and the computers they own. The user
and biographies are connected by To-One relationship, the user and computers are connected by To-Many
relationship

Models:

.. literalinclude:: ./python_snippets/relationships/models.py
  :language: python


Schemas:

.. literalinclude:: ./python_snippets/relationships/relationships_info_example.py
  :language: python

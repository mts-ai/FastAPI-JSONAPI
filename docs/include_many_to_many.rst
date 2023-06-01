.. _include_many_to_many:

Include nested and related Many-to-Many
#######################################

.. currentmodule:: fastapi_jsonapi

The same as usual includes. Here's an example with an association object.

Example (sources `here <https://github.com/mts-ai/FastAPI-JSONAPI/tree/main/examples/api_for_sqlalchemy>`_):

Prepare models and schemas
==========================


Define SQLAlchemy models
------------------------


Parent model
^^^^^^^^^^^^

``models/parent.py``:

.. literalinclude:: ../examples/api_for_sqlalchemy/models/parent.py
    :language: python



Child model
^^^^^^^^^^^

``models/child.py``:

.. literalinclude:: ../examples/api_for_sqlalchemy/models/child.py
    :language: python



Parent to Child Association model
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``models/parent_child_association.py``:

.. literalinclude:: ../examples/api_for_sqlalchemy/models/parent_child_association.py
    :language: python




Define pydantic schemas
-----------------------


Parent Schema
^^^^^^^^^^^^^

``schemas/parent.py``:

.. literalinclude:: ../examples/api_for_sqlalchemy/models/schemas/parent.py
    :language: python


Child Schema
^^^^^^^^^^^^

``schemas/child.py``:

.. literalinclude:: ../examples/api_for_sqlalchemy/models/schemas/child.py
    :language: python


Parent to Child Association Schema
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``schemas/parent_child_association.py``:

.. literalinclude:: ../examples/api_for_sqlalchemy/models/schemas/parent_child_association.py
    :language: python




Define view classes
-------------------


Base Views
^^^^^^^^^^

``api/base.py``:

.. literalinclude:: ../examples/api_for_sqlalchemy/api/base.py
    :language: python


Parent Views
^^^^^^^^^^^^

``schemas/child.py``:

.. literalinclude:: ../examples/api_for_sqlalchemy/api/parent.py
    :language: python


Child Views
^^^^^^^^^^^

``schemas/child.py``:

.. literalinclude:: ../examples/api_for_sqlalchemy/api/child.py
    :language: python



List Parent objects with Children through an Association object
---------------------------------------------------------------

Request:

.. literalinclude:: ./http_snippets/snippets/includes__many_to_many
  :language: HTTP

Response:

.. literalinclude:: ./http_snippets/snippets/includes__many_to_many_result
  :language: HTTP

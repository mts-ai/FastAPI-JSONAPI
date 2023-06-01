.. _include_many_to_many:

Include related M2M
===================

.. currentmodule:: fastapi_jsonapi

The same as usual includes. Here's an example with an association object:

Example (sources `here <https://github.com/mts-ai/FastAPI-JSONAPI/tree/main/examples/api_for_sqlalchemy>`_):


Define SQLAlchemy models
~~~~~~~~~~~~~~~~~~~~~~~~

Parent:

.. literalinclude:: ../examples/api_for_sqlalchemy/models/parent.py
    :language: python


Child:

.. literalinclude:: ../examples/api_for_sqlalchemy/models/child.py
    :language: python


Parent to Child Association object:

.. literalinclude:: ../examples/api_for_sqlalchemy/models/parent_child_association.py
    :language: python



Define pydantic schemas
~~~~~~~~~~~~~~~~~~~~~~~


Parent Schema:

.. literalinclude:: ../examples/api_for_sqlalchemy/models/schemas/parent.py
    :language: python


Child Schema:

.. literalinclude:: ../examples/api_for_sqlalchemy/models/schemas/child.py
    :language: python


Parent to Child Association Schema:

.. literalinclude:: ../examples/api_for_sqlalchemy/models/schemas/parent_child_association.py
    :language: python




List Parent objects with Children through an Association object
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Request:

.. literalinclude:: ./http_snippets/snippets/includes__many_to_many
  :language: HTTP

Response:

.. literalinclude:: ./http_snippets/snippets/includes__many_to_many_result
  :language: HTTP

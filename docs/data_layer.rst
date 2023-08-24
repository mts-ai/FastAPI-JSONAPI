.. _data_layer:

Data layer
==========

.. currentmodule:: fastapi_jsonapi

| The data layer is a CRUD interface between resource manager and data. It is a very flexible system to use any ORM or data storage. You can even create a data layer that uses multiple ORMs and data storage to manage your own objects. The data layer implements a CRUD interface for objects and relationships. It also manages pagination, filtering and sorting.
|
| FastAPI-JSONAPI has a full-featured data layer that uses the popular ORM `SQLAlchemy <https://www.sqlalchemy.org/>`_.

To configure the data layer you have to set its required parameters in the resource manager.

Example:

.. literalinclude:: ./python_snippets/data_layer/custom_data_layer.py

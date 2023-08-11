FastAPI-JSONAPI
==================
.. image:: https://img.shields.io/pypi/v/fastapi-jsonapi.svg
   :alt: PyPI
   :target: http://pypi.org/p/fastapi-jsonapi


**FastAPI-JSONAPI** is an extension for FastAPI that adds support for quickly building REST APIs
with huge flexibility around the JSON:API 1.0 specification.
It is designed to fit the complexity of real life environments
so FastAPI-JSONAPI helps you to create a logical abstraction of your data
called "resource". It can interface any kind of ORMs or data storage
through the concept of data layers.

Main concepts
-------------

.. image:: img/schema.png
   :width: 900px
   :alt: Architecture

| * `JSON:API 1.0 specification <http://jsonapi.org/>`_: this is a very popular specification for client-server interactions through a JSON-based REST API. It helps you work in a team because it is very precise and sharable. Thanks to this specification your API can offer a lot of features such as a strong structure of request and response, filtering, pagination, sparse fieldsets, including related objects, great error formatting, etc.
|
| * **Logical data abstraction**: you usually need to expose resources to clients that don't fit your data table architecture. For example sometimes you don't want to expose all attributes of a table, compute additional attributes or create a resource that uses data from multiple data storages.
|
| * **Data layer**: the data layer is a CRUD interface between your resource manager and your data. Thanks to this you can use any data storage or ORM. There is an already full-featured data layer that uses the SQLAlchemy ORM but you can create and use your own custom data layer to use data from your data storage. You can even create a data layer that uses multiple data storage systems and ORMs, send notifications or perform custom actions during CRUD operations.

Features
--------

FastAPI-JSONAPI has many features:

* Relationship management - in developing
* Powerful filtering
* Include related objects - in developing
* Sparse fieldsets - in developing
* Pagination
* Sorting
* Permission management - in developing
* OAuth support - in developing


User's Guide
------------

This part of the documentation will show you how to get started using
FastAPI-JSONAPI with FastAPI.

.. toctree::
   :maxdepth: 3

   installation
   minimal_api_example
   api_filtering_example
   quickstart
   routing
   view_dependencies
   filtering
   include_related_objects
   include_many_to_many
   custom_sql_filtering
   client_generated_id
   logical_data_abstraction
   resource_manager
   data_layer
   relationships
   sparse_fieldsets
   pagination
   sorting
   errors
   api
   permission
   oauth
   configuration

.. toctree::
   :maxdepth: 2

   changelog


.. include:: ./minimal_api_example.rst


API Reference
-------------

If you are looking for information on a specific function, class or
method, this part of the documentation is for you.

* :ref:`genindex`
* :ref:`modindex`

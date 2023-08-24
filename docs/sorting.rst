.. _sorting:

Sorting
=======

.. currentmodule:: fastapi_jsonapi

You can sort results using the query string parameter named "sort"

.. note::

    Examples are not URL encoded for better readability

Example:

.. sourcecode:: http

    GET /users?sort=name HTTP/1.1
    Accept: application/vnd.api+json

Multiple sort
-------------

You can sort on multiple fields like this:

.. sourcecode:: http

    GET /users?sort=name,birth_date HTTP/1.1
    Accept: application/vnd.api+json

Descending sort
---------------

You can in descending order using a minus symbol, "-", like this:

.. sourcecode:: http

    GET /users?sort=-name HTTP/1.1
    Accept: application/vnd.api+json

Multiple sort + Descending sort
-------------------------------

Of course, you can combine both like this:

.. sourcecode:: http

    GET /users?sort=-name,birth_date HTTP/1.1
    Accept: application/vnd.api+json

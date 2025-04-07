.. _updated_includes_example:

Create and include related objects (updated example)
####################################################

.. currentmodule:: fastapi_jsonapi

You can include related object(s) details in responses with the query string parameter named "include". You can use the "include" parameter on any kind of route (classical CRUD route or relationships route) and any kind of HTTP methods as long as the method returns data.

This feature will add an additional key in the result named "included"

Example
=======


Create user
-----------

Request:

.. literalinclude:: ./http_snippets/snippets/example_one_api__create_user
  :language: HTTP

Response:

.. literalinclude:: ./http_snippets/snippets/example_one_api__create_user_result
  :language: HTTP


Create computer for user and fetch related user
-----------------------------------------------

Request:

.. literalinclude:: ./http_snippets/snippets/example_one_api__create_computer_for_user
  :language: HTTP

Response:

.. literalinclude:: ./http_snippets/snippets/example_one_api__create_computer_for_user_result
  :language: HTTP


Get user
--------

Request:

.. literalinclude:: ./http_snippets/snippets/example_one_api__get_user
  :language: HTTP

Response:

.. literalinclude:: ./http_snippets/snippets/example_one_api__get_user_result
  :language: HTTP


Get user with related computers
-------------------------------

Request:

.. literalinclude:: ./http_snippets/snippets/example_one_api__get_user_with_computers
  :language: HTTP

Response:

.. literalinclude:: ./http_snippets/snippets/example_one_api__get_user_with_computers_result
  :language: HTTP


Get users
---------

Request:

.. literalinclude:: ./http_snippets/snippets/example_one_api__get_users
  :language: HTTP

Response:

.. literalinclude:: ./http_snippets/snippets/example_one_api__get_users_result
  :language: HTTP


Get users with related computers
--------------------------------

Request:

.. literalinclude:: ./http_snippets/snippets/example_one_api__get_users_with_computers
  :language: HTTP

Response:

.. literalinclude:: ./http_snippets/snippets/example_one_api__get_users_with_computers_result
  :language: HTTP

.. _errors:

Errors
======

.. currentmodule:: fastapi_jsonapi

The JSON:API 1.0 specification recommends to return errors like this:

.. sourcecode:: http

    HTTP/1.1 422 Unprocessable Entity
    Content-Type: application/vnd.api+json

    {
      "errors": [
        {
          "status": "422",
          "source": {
            "pointer":"/data/attributes/first-name"
          },
          "title":  "Invalid Attribute",
          "detail": "First name must contain at least three characters."
        }
      ],
      "jsonapi": {
        "version": "1.0"
      }
    }

The "source" field gives information about the error if it is located in data provided or in a query string parameter.

The previous example shows an error located in data provided. The following example shows error in the query string parameter "include":

.. sourcecode:: http

    HTTP/1.1 400 Bad Request
    Content-Type: application/vnd.api+json

    {
      "errors": [
        {
          "status": "400",
          "source": {
            "parameter": "include"
          },
          "title":  "BadRequest",
          "detail": "Include parameter is invalid"
        }
      ],
      "jsonapi": {
        "version": "1.0"
      }
    }

FastAPI-JSONAPI provides two kinds of helpers for displaying errors:


| * **the exceptions module**: you can import a lot of exceptions from this `module <https://github.com/mts-ai/FastAPI-JSONAPI/blob/main/fastapi_jsonapi/exceptions/json_api.py>`_ that helps you to raise exceptions that will be well-formatted according to the JSON:API 1.0 specification

When you create custom code for your API I recommand using exceptions from the FastAPI-JSONAPI's exceptions module to raise errors because HTTPException-based exceptions are caught and rendered according to the JSON:API 1.0 specification.

Example:

.. code-block:: python

    TODO

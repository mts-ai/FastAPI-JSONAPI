.. _custom_sql_filtering:

Custom SQL filtering
####################

.. currentmodule:: fastapi_jsonapi

Sometimes you need custom filtering that's not supported natively.
You can define new filtering rules as in this example:



Prepare pydantic schema which is used in RoutersJSONAPI as schema
-----------------------------------------------------------------


``schemas/picture.py``:

.. literalinclude:: ../examples/custom_filter_example.py
    :language: python


Declare models as usual, create routes as usual.

Search for objects
------------------


.. note::
    Note that url has to be quoted. It's unquoted only for an example

Request:

.. sourcecode:: http

    GET /pictures?filter=[{"name":"picture.meta","op":"jsonb_contains","val":{"location":"Moscow"}}]
    Accept: application/vnd.api+json

Filter value has to be a valid JSON:

.. sourcecode:: JSON
    [
       {
          "name":"picture.meta",
          "op":"jsonb_contains",
          "val":{
             "location":"Moscow"
          }
       }
    ]

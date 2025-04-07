Filtering API example
======================

.. literalinclude:: ../examples/custom_filter_example.py
    :language: python



Filter by jsonb contains. Before using the filter, you must define it and apply it
to the schema as shown here :ref:`custom_sql_filtering`. Some useful  filters are
defined in module **fastapi_jsonapi.types_metadata.custom_filter_sql.py**

.. code-block:: json

    [
      {
        "name": "words",
        "op": "sqlite_json_contains",
        "val": {"location": "Moscow", "spam": "eggs"}
      }
    ]

Request:

.. literalinclude:: ./http_snippets/snippets/api_filtering__get_users__filter_word_contains_in_array
  :language: HTTP

Response:

.. literalinclude:: ./http_snippets/snippets/api_filtering__get_users__filter_word_contains_in_array_result
  :language: HTTP


Other examples
--------------

.. code-block:: python

    # pseudo-code

    class User:
        name: str = ...
        words: list[str] = ...


Filter by word

.. code-block:: json

    [
      {
        "name": "words",
        "op": "in",
        "val": "spam"
      }
    ]

Request:

.. literalinclude:: ./http_snippets/snippets/api_filtering__get_users__filter_word_in_array
  :language: HTTP

Response:

.. literalinclude:: ./http_snippets/snippets/api_filtering__get_users__filter_word_in_array_result
  :language: HTTP


Filter by words

.. code-block:: json

    [
      {
        "name": "words",
        "op": "in",
        "val": ["bar", "eggs"]
      }
    ]

Request:

.. literalinclude:: ./http_snippets/snippets/api_filtering__get_users__filter_words_in_array
  :language: HTTP

Response:

.. literalinclude:: ./http_snippets/snippets/api_filtering__get_users__filter_words_in_array_result
  :language: HTTP

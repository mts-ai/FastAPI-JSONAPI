Filtering API example
======================

.. literalinclude:: ../examples/custom_filter_example.py
    :language: python



Filter by jsonb contains

.. code-block:: json

    [
      {
        "name": "words",
        "op": "jsonb_contains",
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

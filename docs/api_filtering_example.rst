Filtering API example
======================

.. literalinclude:: ../examples/api_complex_filtering.py
    :language: python


Check existing users

Request:

.. literalinclude:: ./http_snippets/snippets/api_filtering__get_users
  :language: HTTP

Response:

.. literalinclude:: ./http_snippets/snippets/api_filtering__get_users_result
  :language: HTTP



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


Filter by any word containing value

.. code-block:: json

    [
      {
        "name": "words",
        "op": "ilike_in_str_array",
        "val": "green"
      }
    ]

Request:

.. literalinclude:: ./http_snippets/snippets/api_filtering__get_users__filter_word_contains_in_array
  :language: HTTP

Response:

.. literalinclude:: ./http_snippets/snippets/api_filtering__get_users__filter_word_contains_in_array_result
  :language: HTTP

A minimal API
=============

.. literalinclude:: ../examples/api_minimal.py
    :language: python


This example provides the following API structure:

========================  ======  =============  ===========================
URL                       method  endpoint       Usage
========================  ======  =============  ===========================
/users                    GET     user_list      Get a collection of users
/users                    POST    user_list      Create a user
/users                    DELETE  user_list      Delete users
/users/{user_id}          GET     user_detail    Get user details
/users/{user_id}          PATCH   user_detail    Update a user
/users/{user_id}          DELETE  user_detail    Delete a user
========================  ======  =============  ===========================

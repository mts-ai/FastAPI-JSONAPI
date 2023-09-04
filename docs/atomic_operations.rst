.. _atomic_operations:

Atomic Operations
=================

.. currentmodule:: fastapi_jsonapi


Atomic Operations allows to perform multiple “operations” in a linear and atomic manner.
Operations are a serialized form of the mutations allowed in the base JSON:API specification.

Clients can send an array of operations in a single request.
This extension guarantees that those operations will be processed in order and will either completely succeed or fail together.

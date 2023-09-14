Changelog
#########


**2.2.0**
*********

Support for pydantic validators
===============================

* Pydantic validators are applied to generated schemas now

Authors
"""""""

* `@CosmoV`_


**2.1.0**
*********

Atomic Operations
=================

* Atomic Operations (see :ref:`example <atomic_operations>`, `JSON:API doc <https://jsonapi.org/ext/atomic/>`_)
* Create view now accepts ``BaseJSONAPIItemInSchema`` as update view does

Authors
"""""""

* `@mahenzon`_


**2.0.0**
*********

Generic views, process relationships
====================================

Backward-incompatible changes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* Automatically create all CRUD views based on schemas (see :ref:`example <minimal_api_example>`)
* Allow to pass Client-Generated IDs (see :ref:`example <client_generated_id>`, `JSON:API doc <https://jsonapi.org/format/#crud-creating-client-ids>`_)
* Process relationships on create / update (see :ref:`example <relationships>`, `JSON:API doc <https://jsonapi.org/format/#crud-updating-resource-relationships>`_)
* Accept pydantic model with any dependencies on it (see :ref:`example <view_dependencies>`)
* handle exceptions (return errors, `JSON:API doc <https://jsonapi.org/format/#errors>`_)
* refactor data layers
* tests coverage

Authors
"""""""

* `@mahenzon`_
* `@CosmoV`_
* `@tpynio`_


**1.1.0**
*********

Generic views
=============

* Create generic view classes `#28 <https://github.com/mts-ai/FastAPI-JSONAPI/pull/28>`_

`@CosmoV`_


**1.0.0**
*********

Backward-incompatible changes, improvements, bug fixes
======================================================

* Includes (see :ref:`example with many-to-many <include_many_to_many>`) - any level of includes is now supported (tested with 4);
* View Classes generics (Detail View and List View);
* View Classes now use instance-level methods (breaking change, previously ``classmethods`` were used);
* Pydantic schemas now have to be inherited from custom BaseModel methods (breaking change, previously all schemas were supported). It uses custom `registry class <https://github.com/mts-ai/FastAPI-JSONAPI/blob/188093e967bb80b7a1f0a86e754a52e47f252044/fastapi_jsonapi/schema_base.py#L33>`_, so we can collect and resolve all schemas. Maybe there's some workaround to collect all known schemas;
* Improved interactive docs, request and response examples now have more info, more schemas appear in docs;
* Reworked schemas resolving and building;
* Fixed filtering (schemas resolving fix);
* Create custom sql filters :ref:`example <custom_sql_filtering>`;
* Add linters: black, ruff;
* Add pre-commit;
* Add autotests with pytest;
* Add poetry, configure dependencies groups;
* Add GitHub Action with linting and testing;
* Upgrade examples;
* Update docs.

`@mahenzon`_


**0.2.1**
*********

Enhancements and bug fixes
==========================

* Fix setup.py for docs in PYPI - `@znbiz`_


**0.2.0**
*********

Enhancements and bug fixes
==========================

* Rename `from fastapi_rest_jsonapi import...` to `from fastapi_jsonapi import ...` - `@znbiz`_
* Add documentation - `@znbiz`_


.. _`@znbiz`: https://github.com/znbiz
.. _`@mahenzon`: https://github.com/mahenzon
.. _`@CosmoV`: https://github.com/CosmoV
.. _`@tpynio`: https://github.com/tpynio

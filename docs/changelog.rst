Changelog
#########


**0.4.0**
*********

Backward-incompatible changes, improvements, bug fixes
======================================================

* Includes (see :ref:`example with many-to-many <include_many_to_many>`:) - any level of includes is now supported (tested with 4);
* View Classes generics (Detail View and List View);
* View Classes now use instance-level methods (breaking change, previously ``classmethods`` were used);
* Pydantic schemas now have to be inherited from custom BaseModel methods (breaking change, previously all schemas were supported). It uses custom :ref:`registry class <https://github.com/mts-ai/FastAPI-JSONAPI/blob/188093e967bb80b7a1f0a86e754a52e47f252044/fastapi_jsonapi/schema_base.py#L33>`:, so we can collect and resolve all schemas. Maybe there's some workaround to collect all known schemas;
* Improved docs, request and response examples have more info, more schemas appear in docs;
* Reworked schemas resolving and building;
* Fixed filtering (schemas resolving fix);
* Fixed filtering (schemas resolving fix);
* Create custom sql filters :ref:`example <custom_sql_filtering>`:;
* Add linters: black, ruff;
* Add pre-commit;
* Add autotests with pytest;
* Add poetry, configure dependencies groups;
* Add GitHub Action with linting and testing;
* Upgrade examples;
* Update docs.

- `@mahenzon`_


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

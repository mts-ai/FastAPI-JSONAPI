.. _logical_data_abstraction:

Logical data abstraction
========================

.. currentmodule:: fastapi_jsonapi

The first thing to do in FastAPI-JSONAPI is to create a logical data abstraction.
This part of the API describes schemas of resources exposed by the API
that are not an exact mapping of the data architecture.
Pydantic is a very popular serialization/deserialization library
that offers a lot of features to abstract your data architecture.
Moreover there is another library called pydantic
that fits the JSON:API 1.0 specification and provides FastAPI integration.

Example:

In this example, let's assume that we have two legacy models, User and Computer, and we want to create an abstraction on top of them.

.. code-block:: python

    from sqlalchemy import Column, String, Integer, ForeignKey
    from sqlalchemy.orm import relationship, backref
    from sqlalchemy.ext.declarative import declarative_base

    Base = declarative_base()

    class User(Base):
        id = Column(Integer, primary_key=True)
        name = Column(String)
        email = Column(String)
        birth_date = Column(String)
        password = Column(String)


    class Computer(Base):
        computer_id = Column(Integer, primary_key=True)
        serial = Column(String)
        user_id = Column(Integer, ForeignKey('user.id'))
        user = relationship('User', backref=backref('computers'))

Now let's create the logical abstraction to illustrate this concept.

.. code-block:: python

    from pydantic import (
        BaseModel,
        Field,
    )
    from typing import List
    from datetime import datetime


    class UserSchema(BaseModel):
        class Config:
            orm_mode = True

        id: int
        name: str
        email: str
        birth_date: datetime
        computers: List['ComputerSchema']


    class ComputerSchema(BaseModel):
        class Config:
            orm_mode = True

        id: int
        serial: str
        owner: UserSchema

You can see several differences between models and schemas exposed by the API.

First, take a look at the User compared to UserSchema:

* We can see that User has an attribute named "password" and we don't want to expose it through the api so it is not set in UserSchema
* UserSchema has an attribute named "display_name" that is the result of concatenation of name and email
* In the "computers" Relationship() defined on UserSchema we have set the id_field to "computer_id" as that is the primary key on the Computer(db.model). Without setting id_field the relationship looks for a field called "id".

Second, take a look at the Computer compared to ComputerSchema:

* The attribute computer_id is exposed as id for consistency of the api
* The user relationship between Computer and User is exposed in ComputerSchema as owner because it is more explicit

As a result you can see that you can expose your data in a very flexible way to create the API of your choice on top of your data architecture.

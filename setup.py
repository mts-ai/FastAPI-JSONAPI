import os
from setuptools import setup, find_packages

__version__ = "0.2.0"


requirements_filepath = os.path.join(os.path.dirname(__name__), "requirements.txt")
readme_filepath = os.path.join(os.path.dirname(__name__), "README.md")
with open(requirements_filepath) as fp:
    install_requires = fp.read()

extra_packages = {
    "tests": ["pytest"],
    "docs": ["sphinx"],
    "tortoise-orm": ["tortoise-orm>=0.19.2"],
    "sqlalchemy": ["SQLAlchemy>=1.4.39,<2.0.0"],
}
all_packages = []
for value in extra_packages.values():
    all_packages.extend(value)

EXTRAS_REQUIRE = {
    "all": all_packages,
}
EXTRAS_REQUIRE.update(extra_packages)

setup(
    name="FastAPI-JSONAPI",
    version=__version__,
    description="FastAPI extension to create REST web api according to JSON:API 1.0 specification "
                "with FastAPI, Pydantic and data provider of your choice (SQLAlchemy, Tortoise ORM)",
    url="https://github.com/mts-ai/FastAPI-JSONAPI",
    author="Team MTS AI",
    author_email="a.nekrasov@mts.ru",
    license="MIT",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: Utilities",
    ],
    keywords="pycore mts digital",
    packages=find_packages(exclude=["tests"]),
    zip_safe=False,
    platforms="any",
    install_requires=install_requires,
    extras_require=EXTRAS_REQUIRE,
    tests_require=["pytest"],
    long_description=readme_filepath,
    long_description_content_type='text/markdown',
)

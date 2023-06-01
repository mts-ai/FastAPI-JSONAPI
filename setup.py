from pathlib import Path

from setuptools import find_packages, setup

__version__ = "1.0.0"

base_dir = Path(__file__).parent
requirements_filepath = base_dir / "requirements.txt"
readme_filepath = base_dir / "README.md"
install_requires = requirements_filepath.read_text()

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


def get_description():
    """
    Read full description from 'README.md'
    """
    return Path("README.md").read_text(encoding="utf-8")


setup(
    name="FastAPI-JSONAPI",
    version=__version__,
    description="FastAPI extension to create REST web api according to JSON:API 1.0 specification "
    "with FastAPI, Pydantic and data provider of your choice (SQLAlchemy, Tortoise ORM)",
    long_description=get_description(),
    long_description_content_type="text/markdown",
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
    keywords="fastapi jsonapi mts ai",
    packages=find_packages(exclude=["tests"]),
    zip_safe=False,
    platforms="any",
    install_requires=install_requires,
    extras_require=EXTRAS_REQUIRE,
    tests_require=["pytest"],
)

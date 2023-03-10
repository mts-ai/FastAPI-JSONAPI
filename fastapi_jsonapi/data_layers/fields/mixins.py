"""Enum mixin module."""

from enum import (
    Enum,
    IntEnum,
)


class MixinEnum(Enum):
    """Extension over enum class from standard library."""

    @classmethod
    def names(cls):
        """Get all field names."""
        return ",".join(field.name for field in cls)

    @classmethod
    def values(cls):
        """Get all values from Enum."""
        return [value for _, value in cls._member_map_.items()]

    @classmethod
    def keys(cls):
        """Get all field keys from Enum."""
        return [key for key, _ in cls._member_map_.items()]

    @classmethod
    def inverse(cls):
        """Return all inverted items sequence."""
        return {value: key for key, value in cls._member_map_.items()}

    @classmethod
    def value_to_enum(cls, value):
        """Convert value to enum."""
        val_to_enum = {value.value: value for _, value in cls._member_map_.items()}
        return val_to_enum.get(value)


class MixinIntEnum(IntEnum):
    """
    Здесь пришлось дублировать код, чтобы обеспечить совместимость с FastAPI и Pydantic.

    Основная проблема - данные либы определяют валидаторы для стандартной библиотеки enum, используя вызов issubclass.
    И для стандартного IntEnum есть отдельная ветка issubclass(IntEnum), в которой происходят
    специальные преобразования, например, аргументы из запроса конвертируются в тип int.
    Поэтому OurEnum(int, Enum) не срабатывает по условию issubclass(obj, IntEnum) и выбираются
    неверные валидаторы и конверторы.
    А код ниже пришлось задублировать, так как у стандартного Enum есть метакласс, который разрешает только
    такую цепочку наследования:
    NewEnum(клас_тип, миксин_без_типа_1, ..., миксин_без_типа_n, Enum)
    По этому правилу нельзя построить наследование, добавляющее миксин без типа к стандартному IntEnum:
    NewEnum(our_mixin, IntEnum), так как IntEnum = (int, Enum)
    Поэтому пока остается такое решение до каких-либо исправлений со стороны разработчиков либы,
    либо появления более гениальных идей
    """

    @classmethod
    def names(cls):
        """Get all field names."""
        return ",".join(field.name for field in cls)

    @classmethod
    def values(cls):
        """Get all values from Enum."""
        return [value for _, value in cls._member_map_.items()]

    @classmethod
    def keys(cls):
        """Get all field keys from Enum."""
        return [key for key, _ in cls._member_map_.items()]

    @classmethod
    def inverse(cls):
        """Return all inverted items sequence."""
        return {value: key for key, value in cls._member_map_.items()}

    @classmethod
    def value_to_enum(cls, value):
        """Convert value to enum."""
        val_to_enum = {value.value: value for _, value in cls._member_map_.items()}
        return val_to_enum.get(value)

import enum


class EnumCls(enum.Enum):
    """
    this is enum class
    """

    #: doc for val1
    val1 = 12
    val2 = 23  #: doc for val2
    val3 = 34
    """doc for val3"""
    val4 = 34

    def say_hello(self):
        """a method says hello to you."""
        pass

    @classmethod
    def say_goodbye(cls):
        """a classmethod says good-bye to you."""
        pass


class MyEnum(enum.Enum):
    ValueA = 10


class MyIntEnum(enum.IntEnum):
    ValueB = 20


class MyStringEnum(str, enum.Enum):
    ValueC = 'value'


def ugly_enum_func(e: MyEnum = MyEnum.ValueA) -> None:
    """Function with an Enum default."""


def unannotated_enum_func(e=MyEnum.ValueA):
    """Function with an unannotated Enum default."""


def keyword_only_enum_func(*, e: MyEnum = MyEnum.ValueA) -> None:
    """Function with a keyword-only Enum default."""


ENUM_VALUE = MyEnum.ValueA

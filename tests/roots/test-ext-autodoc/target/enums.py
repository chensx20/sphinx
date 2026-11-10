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


def enum_func(e: EnumCls = EnumCls.val1) -> None:
    pass


def enum_defaults(e=EnumCls.val4, *, keyword=EnumCls.val2):
    pass


enum_value = EnumCls.val1

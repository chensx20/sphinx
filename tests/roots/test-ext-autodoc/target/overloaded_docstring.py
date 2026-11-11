from functools import singledispatch


def func(*args):
    """func(value: int) -> int
    func(value: str, count=1) -> str
    func()

    Function body::

        func('example')

    :param value: a value
    """


class Example:
    """Example(value: int)
    Example(value: str)

    Class body.
    """

    def __init__(self, *args):
        """__init__(self, value: bytes)
        __init__(self)

        Constructor body.
        """

    def method(self, *args):
        """Example.method(self, value: int) -> int
        target.overloaded_docstring.Example.method(self, value: str) -> str
        method(self)

        Method body::

            method('example')

        :param value: a value
        """

    @staticmethod
    def static(*args):
        """static(value: int) -> int
        static()
        """

    @classmethod
    def classmethod(cls, *args):
        """classmethod(cls, value: int) -> int
        classmethod(cls)
        """

    @property
    def prop(self):
        """prop(self) -> int
        prop(self, value) -> str

        Property body.
        """


class Inherited(Example):
    """Example(value: int)
    Example(value: str)

    Class body.
    """


class Descriptor:
    """attr(self) -> int
    attr(self, value) -> str

    Attribute body.
    """

    def __get__(self, obj, cls):
        return self

    def __set__(self, obj, value):
        pass


Example.attr = Descriptor()
Alias = Example


@singledispatch
def dispatch(*args):
    """dispatch(value: str) -> str
    dispatch(value: bytes)

    Dispatch body.
    """


@dispatch.register(int)
def dispatch_int(value):
    pass

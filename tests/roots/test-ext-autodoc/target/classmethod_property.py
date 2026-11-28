import abc
import sys

if sys.version_info >= (3, 8):
    from functools import cached_property


class Concrete:
    @classmethod
    @property
    def prop(cls) -> int:
        """concrete property"""
        raise AssertionError('property getter should not be called')


class Abstract(metaclass=abc.ABCMeta):
    @classmethod
    @property
    @abc.abstractmethod
    def prop(cls) -> int:
        """abstract property"""
        raise AssertionError('property getter should not be called')


if sys.version_info >= (3, 8):
    class Cached:
        @classmethod
        @cached_property
        def prop(cls) -> int:
            """cached property"""
            raise AssertionError('cached property getter should not be called')

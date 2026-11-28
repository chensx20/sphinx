import abc


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

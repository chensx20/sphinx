from abc import abstractmethod


getter_calls = []


class Foo:
    """docstring"""

    @property
    def prop(self) -> int:
        """docstring"""


class ClassProperties:
    """A class with class properties."""

    @classmethod
    @property
    def concrete(cls) -> int:
        """The concrete descriptor summary."""
        getter_calls.append('concrete')
        return 42

    @classmethod
    @property
    @abstractmethod
    def abstract(cls) -> str:
        """The abstract descriptor summary."""
        getter_calls.append('abstract')
        raise NotImplementedError


class InheritedProperties(ClassProperties):
    """A class inheriting class properties."""


class SubclassProperties(ClassProperties):
    """A class defining its own class properties."""

    @classmethod
    @property
    def concrete(cls) -> float:
        """The overridden descriptor summary."""
        getter_calls.append('override')
        return 3.14

    @classmethod
    @property
    @abstractmethod
    def abstract(cls) -> bytes:
        """The subclass abstract descriptor summary."""
        getter_calls.append('subclass abstract')
        raise NotImplementedError


class ReplacedProperties(ClassProperties):
    """A class replacing class properties with ordinary members."""

    def concrete(self):
        """An ordinary method."""

    @property
    def abstract(self) -> bool:
        """An ordinary property."""


class MetaProperties(type):
    """A metaclass defining class properties."""

    @classmethod
    @property
    def concrete(cls) -> int:
        """The metaclass descriptor summary."""
        getter_calls.append('metaclass')
        return 24

    @classmethod
    @property
    @abstractmethod
    def abstract(cls) -> str:
        """The metaclass abstract descriptor summary."""
        getter_calls.append('metaclass abstract')
        raise NotImplementedError


class InheritedMetaProperties(MetaProperties):
    """A metaclass inheriting class properties."""


class WithMetaProperties(metaclass=InheritedMetaProperties):
    """A class using the metaclass."""

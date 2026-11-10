"""Members used to exercise private-member selections."""

from target.private import private_function as _imported


def public():
    """A public function."""


def _first():
    """The first private function."""


def _second():
    """The second private function."""


def _undocumented():
    pass


def hidden():
    """A function classified as private.

    :meta private:
    """


def _visible():
    """A function classified as public.

    :meta public:
    """


class Base:
    """A base class."""

    def _inherited(self):
        """An inherited private method."""

    def inherited(self):
        """An inherited public method."""


class Sample(Base):
    """A class with private methods and attributes."""

    #: A source-documented private class attribute.
    _class_attr = None
    #: Another source-documented private class attribute.
    _other_class_attr = None
    _undoc_attr = None

    def __init__(self):
        #: A source-documented private instance attribute.
        self._instance_attr = None
        #: Another source-documented private instance attribute.
        self._other_instance_attr = None

    def public(self):
        """A public method."""

    def _second(self):
        """The second private method."""

    def _first(self):
        """The first private method."""

    def _undocumented(self):
        pass

    def hidden(self):
        """A method classified as private.

        :meta private:
        """

    def _visible(self):
        """A method classified as public.

        :meta public:
        """

    def __special__(self):
        """A special method."""

    def __local(self):
        """A name-mangled private method."""


class Problem(Exception):
    """An exception with private methods."""

    def public(self):
        """A public exception method."""

    def _first(self):
        """The first private exception method."""

    def _second(self):
        """The second private exception method."""

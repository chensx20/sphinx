class Base(object):
    def __init__(self):
        self.base_attr = None  #: Documented base instance attribute.
        #: Base comment instance attribute.
        self.base_comment = None

    def inheritedmeth(self):
        """Inherited function."""

    @classmethod
    def inheritedclassmeth(cls):
        """Inherited class method."""

    @staticmethod
    def inheritedstaticmeth(cls):
        """Inherited static method."""


class Derived(Base):
    def inheritedmeth(self):
        # no docstring here
        pass

class Container:
    class Base:
        #: Cross-module class data.
        data: int = 10
        #: Cross-module annotated data.
        annotated: str
        #: Base documentation for the shared attribute.
        shared = 1
        #: Private inherited data.
        _private = 2
        #: Special inherited data.
        __special__ = 3

        def __init__(self):
            #: Cross-module constructor data.
            self.instance = 4

        def method(self):
            """Inherited method documentation."""

        @property
        def prop(self):
            """Inherited property documentation."""
            return 5


class Right(Container.Base):
    #: Right documentation for the shared attribute.
    shared = 6


#: Module data documentation.
module_data = 7

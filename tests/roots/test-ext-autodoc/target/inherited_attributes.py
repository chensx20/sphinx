from target.descriptor import Class as DescriptorBase
from target.inherited_attributes_base import Container, Right


class Left(Container.Base):
    #: Left documentation for the shared attribute.
    shared = 8
    #: Same-module class data.
    local_data = 9

    def __init__(self):
        #: Same-module constructor data.
        self.local_instance = 10


class Child(Left, Right):
    #: Subclass documentation.
    own = 11


class Override(Child):
    #: Subclass documentation for the shared attribute.
    shared = 12


class UndocumentedOverride(Child):
    shared = 13


class DescriptorChild(DescriptorBase):
    pass

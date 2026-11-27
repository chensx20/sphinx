def overloaded(value):
    """target.docstring_overloads.overloaded(value: int) -> int
    target.docstring_overloads.overloaded(value: str) -> str

    Shared body.
    """


def legacy_bare_name(value):
    """legacy_bare_name(value: int)
    legacy_bare_name(value: str)

    Body after the legacy signature.
    """


class Overloaded:
    def method(self, value):
        """Overloaded.method(value: int) -> int
        Overloaded.method(value: str) -> str

        Method body.
        """

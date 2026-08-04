class OverloadedClass:
    """OverloadedClass(foo)
OverloadedClass(foo, bar)

Class docstring.
"""


class OverloadedInit:
    def __init__(self):
        """OverloadedInit(foo)
OverloadedInit(foo, bar)

Init docstring.
"""


class OverloadedBoth:
    """OverloadedBoth(foo)
OverloadedBoth(foo, bar)

Class docstring.
"""

    def __init__(self):
        """OverloadedBoth(foo, bar, baz)
OverloadedBoth(foo, bar, baz, qux)

Init docstring.
"""

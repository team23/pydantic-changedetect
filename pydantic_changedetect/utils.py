from typing import Any


def safe_issubclass(cls: Any, type_: Any) -> bool:
    """
    Return True if the first argument is a subclass of the second argument.

    This is a safe version of issubclass() that returns False if the first
    argument is not a valid class. We are checking whether the first argument
    is a class first by doing a `isinstance(cls, type_)` check. But this still can
    raise issues with Python 3.9+ as we are allowed to use normal types as type
    definitions there. And somehow `isinstance(list[str], type)` returns True
    while `isinstance(List[str], type)` (List from typing here) returns False.

    This would not be an issue with `issubclass(cls, type_)` as `list[str]` is
    normally handled correctly. But if the `type_` is a child class of `abc.ABC`
    the method will fail with a `TypeError: issubclass() arg 2 must be a class` as
    `abc.ABC` overrides the `__subclasscheck__` magic method.

    This function will catch the `TypeError` and return False in that case.
    """

    if not isinstance(cls, type):
        return False

    try:
        return issubclass(cls, type_)
    except TypeError:
        return False

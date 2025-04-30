import warnings
from collections.abc import Mapping
from typing import Any, Dict, List, Optional, Set, Tuple, Union, get_args, get_origin

import pydantic_changedetect


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

    warnings.warn(
        "safe_issubclass() is deprecated and will be removed",
        DeprecationWarning,
        stacklevel=2,
    )

    if not isinstance(cls, type):
        return False

    try:
        return issubclass(cls, type_)
    except TypeError:
        return False


def is_class_type(annotation: Any) -> bool:
    # If the origin is None, it's likely a concrete class
    return get_origin(annotation) is None


def is_pydantic_change_detect_annotation(annotation: Optional[type[Any]]) -> bool:
    """
    Return True if the given annotation is a ChangeDetectionMixin annotation.
    """

    if annotation is None:
        return False

    # if annotation is an ChangeDetectionMixin everything is easy
    if (
        is_class_type(annotation)
        and isinstance(annotation, type)
        and issubclass(annotation, pydantic_changedetect.ChangeDetectionMixin)
    ):
        return True

    # Otherwise we may need to handle typing arguments
    origin = get_origin(annotation)
    if (
        origin is List
        or origin is list
        or origin is Set
        or origin is set
        or origin is Tuple
        or origin is tuple
    ):
        return is_pydantic_change_detect_annotation(get_args(annotation)[0])
    elif (
        origin is Dict
        or origin is dict
        or origin is Mapping
    ):
        return is_pydantic_change_detect_annotation(get_args(annotation)[1])
    elif origin is Union:
        # Note: This includes Optional, as Optional[...] is just Union[..., None]
        return any(
            is_pydantic_change_detect_annotation(arg)
            for arg in get_args(annotation)
        )

    # If we did not detect an ChangeDetectionMixin annotation, return False
    return False

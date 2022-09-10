import abc
import sys
from typing import Dict, List

import pytest

from pydantic_changedetect.utils import safe_issubclass


class BaseClass:
    pass


class NormalClass(BaseClass):
    pass


class AbstractClass(BaseClass, abc.ABC):
    pass


def test_safe_issubclass():
    assert safe_issubclass(NormalClass, BaseClass)
    assert safe_issubclass(AbstractClass, BaseClass)


def test_safe_issubclass_for_type_definitions():
    assert safe_issubclass(List[str], BaseClass) is False
    assert safe_issubclass(Dict[str, str], BaseClass) is False

    if sys.version_info >= (3, 9):
        assert safe_issubclass(list[str], BaseClass) is False
        assert safe_issubclass(dict[str, str], BaseClass) is False


def test_ensure_normal_issubclass_raises_an_issue():
    with pytest.raises(TypeError):
        issubclass(list[str], AbstractClass)


def test_safe_issubclass_for_type_definitions_for_abstract():
    assert safe_issubclass(List[str], AbstractClass) is False
    assert safe_issubclass(Dict[str, str], AbstractClass) is False

    if sys.version_info >= (3, 9):
        assert safe_issubclass(list[str], AbstractClass) is False
        assert safe_issubclass(dict[str, str], AbstractClass) is False

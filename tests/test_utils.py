import abc
import sys
from typing import Dict, List, Optional, Tuple, Union

import pydantic
import pytest

from pydantic_changedetect import ChangeDetectionMixin
from pydantic_changedetect.utils import is_pydantic_change_detect_annotation, safe_issubclass


class BaseClass:
    pass


class NormalClass(BaseClass):
    pass


class AbstractClass(BaseClass, abc.ABC):
    pass


def test_safe_issubclass():
    with pytest.warns(DeprecationWarning):
        assert safe_issubclass(NormalClass, BaseClass)
    with pytest.warns(DeprecationWarning):
        assert safe_issubclass(AbstractClass, BaseClass)


def test_safe_issubclass_for_type_definitions():
    with pytest.warns(DeprecationWarning):
        assert safe_issubclass(list[str], BaseClass) is False
    with pytest.warns(DeprecationWarning):
        assert safe_issubclass(dict[str, str], BaseClass) is False

    with pytest.warns(DeprecationWarning):
        assert safe_issubclass(list[str], BaseClass) is False
    with pytest.warns(DeprecationWarning):
        assert safe_issubclass(dict[str, str], BaseClass) is False


def test_ensure_normal_issubclass_raises_an_issue():
    with pytest.raises(TypeError):
        issubclass(list[str], AbstractClass)


def test_safe_issubclass_for_type_definitions_for_abstract():
    with pytest.warns(DeprecationWarning):
        assert safe_issubclass(list[str], AbstractClass) is False
    with pytest.warns(DeprecationWarning):
        assert safe_issubclass(dict[str, str], AbstractClass) is False

    with pytest.warns(DeprecationWarning):
        assert safe_issubclass(list[str], AbstractClass) is False
    with pytest.warns(DeprecationWarning):
        assert safe_issubclass(dict[str, str], AbstractClass) is False


class SomeModel(ChangeDetectionMixin, pydantic.BaseModel):
    pass


class OtherModel(pydantic.BaseModel):
    pass


def test_is_pydantic_change_detect_annotation_direct_types():
    assert is_pydantic_change_detect_annotation(int) is False
    assert is_pydantic_change_detect_annotation(str) is False
    assert is_pydantic_change_detect_annotation(Union[int, str]) is False
    assert is_pydantic_change_detect_annotation(OtherModel) is False

    assert is_pydantic_change_detect_annotation(ChangeDetectionMixin) is True
    assert is_pydantic_change_detect_annotation(SomeModel) is True


def test_is_pydantic_change_detect_annotation_optional_types():
    assert is_pydantic_change_detect_annotation(Optional[int]) is False
    assert is_pydantic_change_detect_annotation(Optional[OtherModel]) is False

    assert is_pydantic_change_detect_annotation(Optional[SomeModel]) is True


def test_is_pydantic_change_detect_annotation_union_types():
    assert is_pydantic_change_detect_annotation(Union[int, None]) is False
    assert is_pydantic_change_detect_annotation(Union[OtherModel, int]) is False
    assert is_pydantic_change_detect_annotation(Union[OtherModel, None]) is False

    assert is_pydantic_change_detect_annotation(Union[SomeModel, None]) is True
    assert is_pydantic_change_detect_annotation(Union[SomeModel, int]) is True
    assert is_pydantic_change_detect_annotation(Union[SomeModel, OtherModel]) is True


def test_is_pydantic_change_detect_annotation_list_types():
    assert is_pydantic_change_detect_annotation(list[int]) is False
    assert is_pydantic_change_detect_annotation(list[OtherModel]) is False
    assert is_pydantic_change_detect_annotation(tuple[int]) is False
    assert is_pydantic_change_detect_annotation(tuple[OtherModel]) is False

    assert is_pydantic_change_detect_annotation(list[SomeModel]) is True
    assert is_pydantic_change_detect_annotation(tuple[SomeModel]) is True


def test_is_pydantic_change_detect_annotation_dict_types():
    assert is_pydantic_change_detect_annotation(dict[str, int]) is False
    assert is_pydantic_change_detect_annotation(dict[str, OtherModel]) is False

    assert is_pydantic_change_detect_annotation(dict[str, SomeModel]) is True

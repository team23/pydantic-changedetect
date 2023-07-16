import pickle
from typing import Any, Dict, List, Optional, Tuple

import pydantic
import pytest

from pydantic_changedetect import ChangeDetectionMixin
from pydantic_changedetect._compat import PYDANTIC_V1, PYDANTIC_V2


class Something(ChangeDetectionMixin, pydantic.BaseModel):
    id: int


class Nested(ChangeDetectionMixin, pydantic.BaseModel):
    sub: Something


class NestedList(ChangeDetectionMixin, pydantic.BaseModel):
    sub: List[Something]


class NestedTuple(ChangeDetectionMixin, pydantic.BaseModel):
    sub: Tuple[Something, ...]


class NestedDict(ChangeDetectionMixin, pydantic.BaseModel):
    sub: Dict[str, Something]


class SomethingWithBrokenPickleState(Something):
    def __getstate__(self) -> Dict[str, Any]:
        # Skip adding changed state in ChangedDetectionMixin.__getstate__
        return super(ChangeDetectionMixin, self).__getstate__()


def test_initial_state():
    obj = Something(id=1)

    assert not obj.model_has_changed
    assert obj.model_original == {}
    assert obj.model_changed_fields == set()


def test_changed_state():
    obj = Something(id=1)

    obj.id = 2

    assert obj.model_has_changed
    assert obj.model_original == {"id": 1}
    assert obj.model_changed_fields == {"id"}


def test_set_changed_state():
    obj = Something(id=1)

    obj.model_set_changed("id")

    assert obj.model_has_changed
    assert obj.model_original == {"id": 1}
    assert obj.model_changed_fields == {"id"}


def test_set_changed_state_with_fixed_original():
    obj = Something(id=1)

    obj.model_set_changed("id", original=7)

    assert obj.model_has_changed
    assert obj.model_original == {"id": 7}
    assert obj.model_changed_fields == {"id"}


def test_set_changed_will_disallow_invalid_parameters():
    obj = Something(id=1)

    with pytest.raises(RuntimeError):
        obj.model_set_changed("id", "id", original=7)  # type: ignore


def test_set_changed_will_disallow_invalid_field_names():
    obj = Something(id=1)

    with pytest.raises(AttributeError):
        obj.model_set_changed("invalid_field_name")


@pytest.mark.skipif(PYDANTIC_V1, reason="pydantic v1 does not support model_copy()")
def test_copy_keeps_state():
    obj = Something(id=1)

    assert not obj.model_copy().model_has_changed
    assert obj.model_copy().model_changed_fields == set()

    obj.id = 2

    assert obj.model_copy().model_has_changed
    assert obj.model_copy().model_changed_fields == {"id"}


# Test on pydantic v2, too - pydantic has a compatibility layer for this
def test_copy_keeps_state_with_v1_api():
    obj = Something(id=1)

    assert not obj.copy().model_has_changed
    assert obj.copy().model_changed_fields == set()

    obj.id = 2

    assert obj.copy().model_has_changed
    assert obj.copy().model_changed_fields == {"id"}


@pytest.mark.skipif(PYDANTIC_V1, reason="pydantic v1 does not support model_dump()")
def test_export_as_dict():
    obj = Something(id=1)

    assert obj.model_dump() == {"id": 1}
    assert obj.model_dump(exclude_unchanged=True) == {}

    obj.id = 2

    assert obj.model_dump(exclude_unchanged=True) == {"id": 2}


# Test on pydantic v2, too - pydantic has a compatibility layer for this
def test_export_as_dict_with_v1_api():
    obj = Something(id=1)

    assert obj.dict() == {"id": 1}
    assert obj.dict(exclude_unchanged=True) == {}

    obj.id = 2

    assert obj.dict(exclude_unchanged=True) == {"id": 2}


@pytest.mark.skipif(PYDANTIC_V1, reason="pydantic v1 does not support model_dump_json()")
def test_export_as_json():
    obj = Something(id=1)

    assert obj.model_dump_json() == '{"id":1}'
    assert obj.model_dump_json(exclude_unchanged=True) == '{}'

    obj.id = 2

    assert obj.model_dump_json(exclude_unchanged=True) == '{"id":2}'


@pytest.mark.skipif(PYDANTIC_V1, reason="pydantic v1 does have a slightly different result")
def test_export_as_json_with_v1_api_on_v2():
    obj = Something(id=1)

    assert obj.json() == '{"id":1}'
    assert obj.json(exclude_unchanged=True) == '{}'

    obj.id = 2

    assert obj.json(exclude_unchanged=True) == '{"id":2}'


@pytest.mark.skipif(PYDANTIC_V2, reason="pydantic v2 does have a slightly different result")
def test_export_as_json_with_v1_api():
    obj = Something(id=1)

    assert obj.json() == '{"id": 1}'
    assert obj.json(exclude_unchanged=True) == '{}'

    obj.id = 2

    assert obj.json(exclude_unchanged=True) == '{"id": 2}'


@pytest.mark.skipif(PYDANTIC_V1, reason="pydantic v1 does not support model_dump_json()")
def test_export_include_is_intersect():
    something = Something(id=1)

    assert something.model_dump(exclude_unchanged=True, include={'name'}) == {}

    something.id = 2

    assert something.model_dump(exclude_unchanged=True, include=set()) == {}
    assert something.model_dump(exclude_unchanged=True, include={'id'}) == {"id": 2}


# Test on pydantic v2, too - pydantic has a compatibility layer for this
def test_export_include_is_intersect_with_v1_api():
    something = Something(id=1)

    assert something.dict(exclude_unchanged=True, include={'name'}) == {}

    something.id = 2

    assert something.dict(exclude_unchanged=True, include=set()) == {}
    assert something.dict(exclude_unchanged=True, include={'id'}) == {"id": 2}


@pytest.mark.skipif(PYDANTIC_V1, reason="pydantic v1 does not support model_dump_json()")
def test_changed_base_is_resetable():
    something = Something(id=1)
    something.id = 2

    assert something.model_dump(exclude_unchanged=True) == {"id": 2}

    something.model_reset_changed()

    assert something.model_dump(exclude_unchanged=True) == {}


# Test on pydantic v2, too - pydantic has a compatibility layer for this
def test_changed_base_is_resetable_with_v1_api():
    something = Something(id=1)
    something.id = 2

    assert something.dict(exclude_unchanged=True) == {"id": 2}

    something.model_reset_changed()

    assert something.dict(exclude_unchanged=True) == {}


def test_pickle_keeps_state():
    obj = Something(id=1)

    assert not pickle.loads(pickle.dumps(obj)).has_changed
    assert pickle.loads(pickle.dumps(obj)).__changed_fields__ == set()

    obj.id = 2

    assert pickle.loads(pickle.dumps(obj)).has_changed
    assert pickle.loads(pickle.dumps(obj)).__changed_fields__ == {"id"}


def test_pickle_even_works_when_changed_state_is_missing():
    obj = SomethingWithBrokenPickleState(id=1)
    obj.id = 2

    # Now we cannot use the changed state, but nothing fails
    assert not pickle.loads(pickle.dumps(obj)).has_changed
    assert pickle.loads(pickle.dumps(obj)).__changed_fields__ == set()


def test_stores_original():
    something = Something(id=1)

    assert something.model_original == {}

    something.id = 2

    assert something.model_original == {"id": 1}


def test_nested_changed_state():
    parent = Nested(sub=Something(id=1))

    parent.sub.id = 2

    assert parent.model_has_changed
    assert "sub" not in parent.model_original
    assert parent.model_self_changed_fields == set()
    assert parent.model_changed_fields == {"sub"}
    assert parent.model_changed_fields_recursive == {"sub", "sub.id"}

    assert parent.sub.model_has_changed
    assert "id" in parent.sub.model_original
    assert parent.sub.model_original == {"id": 1}
    assert parent.model_self_changed_fields == set()
    assert parent.sub.model_changed_fields == {"id"}
    assert parent.sub.model_changed_fields_recursive == {"id"}


@pytest.mark.parametrize(
    "parent_class, list_type", [
        (NestedList, list),
        (NestedTuple, tuple),
    ],
)
def test_nested_list(parent_class, list_type):
    something = Something(id=1)
    parent = parent_class(sub=list_type([something]))

    # Nothing changed so far
    assert something.model_has_changed is False
    assert parent.model_has_changed is False

    # Change something inside parent
    parent.sub[0].id = 2
    assert parent.sub[0].model_has_changed is True
    assert parent.model_has_changed is True
    assert parent.model_self_changed_fields == set()
    assert parent.model_changed_fields == {'sub'}
    assert parent.model_changed_fields_recursive == {'sub', 'sub.0', 'sub.0.id'}


def test_nested_dict():
    something = Something(id=1)
    parent = NestedDict(sub={"something": something})

    # Nothing changed so far
    assert something.model_has_changed is False
    assert parent.model_has_changed is False

    # Change something inside parent
    parent.sub["something"].id = 2
    assert parent.sub["something"].model_has_changed is True
    assert parent.model_has_changed is True
    assert parent.model_self_changed_fields == set()
    assert parent.model_changed_fields == {'sub'}
    assert parent.model_changed_fields_recursive == {'sub', 'sub.something', 'sub.something.id'}


def test_use_private_attributes_works():
    class SomethingPrivate(Something):
        _private: Optional[int] = pydantic.PrivateAttr(None)

    something = SomethingPrivate(id=1)

    assert something.model_has_changed is False

    something._private = 1

    assert something.model_has_changed is False


def test_construct_works():
    something = Something.construct(id=1)

    assert something.model_has_changed is False

    something.id = 2

    assert something.model_has_changed is True


# TODO: Test old version compatibility

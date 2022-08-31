from typing import Dict, List

import pydantic

from pydantic_changedetect import ChangeDetectionMixin


class Something(ChangeDetectionMixin, pydantic.BaseModel):
    id: int


class Nested(ChangeDetectionMixin, pydantic.BaseModel):
    sub: Something


class NestedList(ChangeDetectionMixin, pydantic.BaseModel):
    sub: List[Something]


class NestedDict(ChangeDetectionMixin, pydantic.BaseModel):
    sub: Dict[str, Something]


class UndetectableChange(ChangeDetectionMixin, pydantic.BaseModel):
    sub: List[str]


def test_initial_state():
    obj = Something(id=1)

    assert not obj.has_changed
    assert obj.__original__ == {}
    assert obj.__changed_fields__ == set()


def test_changed_state():
    obj = Something(id=1)

    obj.id = 2

    assert obj.has_changed
    assert obj.__original__ == {"id": 1}
    assert obj.__changed_fields__ == {"id"}


def test_set_changed_state():
    obj = Something(id=1)

    obj.set_changed("id")

    assert obj.has_changed
    assert obj.__original__ == {"id": 1}
    assert obj.__changed_fields__ == {"id"}


def test_set_changed_state_with_fixed_original():
    obj = Something(id=1)

    obj.set_changed("id", original=7)

    assert obj.has_changed
    assert obj.__original__ == {"id": 7}
    assert obj.__changed_fields__ == {"id"}


def test_copy_keeps_state():
    obj = Something(id=1)

    assert not obj.copy().has_changed
    assert obj.copy().__changed_fields__ == set()

    obj.id = 2

    assert obj.copy().has_changed
    assert obj.copy().__changed_fields__ == {"id"}


def test_export_as_dict():
    obj = Something(id=1)

    assert obj.dict() == {"id": 1}
    assert obj.dict(exclude_unchanged=True) == {}

    obj.id = 2

    assert obj.dict(exclude_unchanged=True) == {"id": 2}


def test_export_as_json():
    obj = Something(id=1)

    assert obj.json() == '{"id": 1}'
    assert obj.json(exclude_unchanged=True) == '{}'

    obj.id = 2

    assert obj.json(exclude_unchanged=True) == '{"id": 2}'


def test_export_include_is_intersect():
    something = Something(id=1)

    assert something.dict(exclude_unchanged=True, include={'name'}) == {}

    something.id = 2

    assert something.dict(exclude_unchanged=True, include=set()) == {}
    assert something.dict(exclude_unchanged=True, include={'id'}) == {"id": 2}


def test_changed_base_is_resetable():
    something = Something(id=1)
    something.id = 2

    assert something.dict(exclude_unchanged=True) == {"id": 2}

    something.reset_changed_state()

    assert something.dict(exclude_unchanged=True) == {}


def test_pickle_keeps_state():
    import pickle

    obj = Something(id=1)

    assert not pickle.loads(pickle.dumps(obj)).has_changed
    assert pickle.loads(pickle.dumps(obj)).__changed_fields__ == set()

    obj.id = 2

    assert pickle.loads(pickle.dumps(obj)).has_changed
    assert pickle.loads(pickle.dumps(obj)).__changed_fields__ == {"id"}


def test_stores_original():
    something = Something(id=1)

    assert something.__original__ == {}

    something.id = 2

    assert something.__original__ == {"id": 1}


def test_nested_changed_state():
    parent = Nested(sub=Something(id=1))

    parent.sub.id = 2

    assert parent.has_changed
    assert "obj" not in parent.__original__
    assert parent.__self_changed_fields__ == set()
    assert parent.__changed_fields__ == {"sub"}
    assert parent.__changed_fields_recursive__ == {"sub", "sub.id"}

    assert parent.sub.has_changed
    assert "id" in parent.sub.__original__
    assert parent.sub.__original__ == {"id": 1}
    assert parent.sub.__changed_fields__ == {"id"}
    assert parent.sub.__changed_fields_recursive__ == {"id"}
    assert parent.sub.__changed_fields_recursive__ == {"id"}


def test_nested_list():
    something = Something(id=1)
    parent = NestedList(sub=[something])

    # Nothing changed so far
    assert something.has_changed is False
    assert parent.has_changed is False

    # Only change something, this will not change the copy inside parent
    something.id = 2
    assert something.has_changed is True
    assert parent.has_changed is False

    # Change something inside parent
    parent.sub[0].id = 2
    assert parent.sub[0].has_changed is True
    assert parent.has_changed is True
    assert parent.__changed_fields__ == {'sub'}
    assert parent.__changed_fields_recursive__ == {'sub', 'sub.0', 'sub.0.id'}
    assert parent.__self_changed_fields__ == set()


def test_nested_dict():
    something = Something(id=1)
    parent = NestedDict(sub={"something": something})

    # Nothing changed so far
    assert something.has_changed is False
    assert parent.has_changed is False

    # Only change something, this will not change the copy inside parent
    something.id = 2
    assert something.has_changed is True
    assert parent.has_changed is False

    # Change something inside parent
    parent.sub["something"].id = 2
    assert parent.sub["something"].has_changed is True
    assert parent.has_changed is True
    assert parent.__changed_fields__ == {'sub'}
    assert parent.__changed_fields_recursive__ == {'sub', 'sub.something', 'sub.something.id'}
    assert parent.__self_changed_fields__ == set()

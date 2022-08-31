import pydantic

from pydantic_changedetect import ChangeDetectionMixin


class MyTestObj(ChangeDetectionMixin, pydantic.BaseModel):
    id: int


def test_initial_state():
    obj = MyTestObj(id=1)

    assert not obj.has_changed
    assert obj.__original__ == {}
    assert obj.__changed_fields__ == set()


def test_changed_state():
    obj = MyTestObj(id=1)

    obj.id = 2

    assert obj.has_changed
    assert obj.__original__ == {"id": 1}
    assert obj.__changed_fields__ == {"id"}


def test_set_changed_state():
    obj = MyTestObj(id=1)

    obj.set_changed("id")

    assert obj.has_changed
    assert obj.__original__ == {"id": 1}
    assert obj.__changed_fields__ == {"id"}


def test_copy_keeps_state():
    obj = MyTestObj(id=1)

    assert not obj.copy().has_changed
    assert obj.copy().__changed_fields__ == set()

    obj.id = 2

    assert obj.copy().has_changed
    assert obj.copy().__changed_fields__ == {"id"}


def test_export_as_dict():
    obj = MyTestObj(id=1)

    assert obj.dict() == {"id": 1}
    assert obj.dict(exclude_unchanged=True) == {}

    obj.id = 2

    assert obj.dict(exclude_unchanged=True) == {"id": 2}


def test_export_as_json():
    obj = MyTestObj(id=1)

    assert obj.json() == '{"id": 1}'
    assert obj.json(exclude_unchanged=True) == '{}'

    obj.id = 2

    assert obj.json(exclude_unchanged=True) == '{"id": 2}'


def test_pickle_keeps_state():
    import pickle

    obj = MyTestObj(id=1)

    assert not pickle.loads(pickle.dumps(obj)).has_changed
    assert pickle.loads(pickle.dumps(obj)).__changed_fields__ == set()

    obj.id = 2

    assert pickle.loads(pickle.dumps(obj)).has_changed
    assert pickle.loads(pickle.dumps(obj)).__changed_fields__ == {"id"}


class MyTestParent(ChangeDetectionMixin, pydantic.BaseModel):
    obj: MyTestObj


def test_child_changed_state():
    parent = MyTestParent(obj=MyTestObj(id=1))

    parent.obj.id = 2

    assert parent.has_changed
    assert "obj" not in parent.__original__
    assert parent.__self_changed_fields__ == set()
    assert parent.__changed_fields__ == {"obj"}
    assert parent.__changed_fields_recursive__ == {"obj", "obj.id"}

    assert parent.obj.has_changed
    assert "id" in parent.obj.__original__
    assert parent.obj.__original__ == {"id": 1}
    assert parent.obj.__changed_fields__ == {"id"}
    assert parent.obj.__changed_fields_recursive__ == {"id"}

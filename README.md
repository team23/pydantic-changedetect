# Pydantic change detection

## Installation

Just use `pip install pydantic-changedetect` to install the library.

**Note:** `pydantic-changedetect` is compatible with `pydantic` version `2.x` on Python `3.9`, `3.10`, `3.11`,
`3.12` and `3.13`. This is also ensured running all tests on all those versions using `tox`.

## About

When working with database models it is pretty common to want to detect changes
to the model attributes. The `ChangeDetectionMixin` just provides this mechanism
to any pydantic models. Changes will be detected and stored after the model
was constructed.

Using the `ChangeDetectionMixin` the pydantic models are extended, so:
* `obj.model_changed_fields` contains a list of all changed fields
  - `obj.model_self_changed_fields` contains a list of all changed fields for the
    current object, ignoring all nested models.
  - `obj.model_changed_fields_recursive` contains a list of all changed fields and
    also include the named of the fields changed in nested models using a
    dotted field name syntax (like `nested.field`).
* `obj.model_original` will include the original values of all changed fields in
  a dict.
* `obj.model_has_changed` returns True if any field has changed.
* `obj.model_set_changed()` manually sets fields as changed.
  - `obj.model_set_changed("field_a", "field_b")` will set multiple fields as changed.
  - `obj.model_set_changed("field_a", original="old")` will set a single field as
    changed and also store its original value.
* `obj.model_reset_changed()` resets all changed fields.
* `obj.model_dump()` and `obj.model_dump_json()` accept an additional parameter
  `exclude_unchanged`, which - when set to True - will only export the
  changed fields.  
  **Note:** When using pydantic 1.x you need to use `obj.dict()` and `obj.json()`. Both
  also accept `exclude_unchanged`.
* `obj.model_restore_original()` will create a new instance of the model containing its
  original state.
* `obj.model_get_original_field_value("field_name")` will return the original value for
  just one field. It will call `model_restore_original()` on the current field value if
  the field is set to a `ChangeDetectionMixin` instance (or list/dict of those).
* `obj.model_mark_changed("marker_name")` and `obj.model_unmark_changed("marker_name")`
  allow to add arbitrary change markers. An instance with a marker will be seen as changed
  (`obj.model_has_changed == True`). Markers are stored in `obj.model_changed_markers`
  as a set.

### Example

```python
import pydantic
from pydantic_changedetect import ChangeDetectionMixin

class Something(ChangeDetectionMixin, pydantic.BaseModel):
    name: str


something = Something(name="something")
something.model_has_changed  # = False
something.model_changed_fields  # = set()
something.name = "something else"
something.model_has_changed  # = True
something.model_changed_fields  # = {"name"}

original = something.model_restore_original()
original.name  # = "something"
original.model_has_changed  # = False
```

### When will a change be detected

`pydantic-changedetect` will see changes when an attribute value is changes using an
attribute assignment like `something.name = "something else"` in the example above. Such
an assignment will be seen as a change unless the new value is the same and the type of
the value is `None` or of type `str`, `int`, `float`, `bool` or `decimal.Decimal`.

#### Restrictions

`ChangeDetectionMixin` currently cannot detect changes inside lists, dicts and
other structured objects. In those cases you are required to set the changed
state yourself using `model_set_changed()`. It is recommended to pass the original
value to `model_set_changed()` when you want to also keep track of the actual changes
compared to the original value. Be advised to `.copy()` the original value
as lists/dicts will always be changed in place.

```python
import pydantic
from pydantic_changedetect import ChangeDetectionMixin

class TodoList(ChangeDetectionMixin, pydantic.BaseModel):
    items: list[str]


todos = TodoList(items=["release new version"])
original_items = todos.items.copy()
todos.items.append("create better docs")  # This change will NOT be seen yet
todos.model_has_changed  # = False
todos.model_set_changed("items", original=original_items)  # Mark field as changed and store original value
todos.model_has_changed  # = True
```

### Changed markers

You may also just mark the model as changed. This can be done using changed markers.
A change marker is just a string that is added as the marker, models with such an marker
will also be seen as changed. Changed markers also allow to mark models as changed when
related data was changed - for example to also update a parent object in the database
when some children were changed.

```python
import pydantic
from pydantic_changedetect import ChangeDetectionMixin

class Something(ChangeDetectionMixin, pydantic.BaseModel):
  name: str


something = Something(name="something")
something.model_has_changed  # = False
something.model_mark_changed("mood")
something.model_has_changed  # = True
something.model_changed_markers  # {"mood"}
something.model_unmark_changed("mood")  # also will be reset on something.model_reset_changed()
something.model_has_changed  # = False
```

# Contributing

If you want to contribute to this project, feel free to just fork the project,
create a dev branch in your fork and then create a pull request (PR). If you
are unsure about whether your changes really suit the project please create an
issue first, to talk about this.

# Pydantic change detection

## Installation

Just use `pip install pydantic-changedetect` to install the library.

**Note:** `pydantic-changedetect` is compatible with `pydantic` versions `1.9`, `1.10` and even `2.x` (🥳) on
Python `3.8`, `3.9`, `3.10` and `3.11`. This is also ensured running all tests on all those versions
using `tox`.

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

### Restrictions

`ChangeDetectionMixin` currently cannot detect changes inside lists, dicts and
other structured objects. In those cases you are required to set the changed
state yourself using `model_set_changed()`. It is recommended to pass the original
value to `model_set_changed()` when you want to also keep track of the actual changes
compared to the original value. Be advised to `.copy()` the original value
as lists/dicts will always be changed in place.

# Contributing

If you want to contribute to this project, feel free to just fork the project,
create a dev branch in your fork and then create a pull request (PR). If you
are unsure about whether your changes really suit the project please create an
issue first, to talk about this.

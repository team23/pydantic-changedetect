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
* `obj.__changed_fields__` contains a list of all changed fields
  - `obj.__self_changed_fields__` contains a list of all changed fields for the
    current object, ignoring all nested models.
  - `obj.__changed_fields_recursive__` contains a list of all changed fields and
    also include the named of the fields changed in nested models using a
    dotted field name syntax (like `nested.field`).
* `obj.__original__` will include the original values of all changed fields in
  a dict.
* `obj.has_changed()` returns True if any field has changed.
* `obj.set_changed()` manually sets fields as changed.
  - `obj.set_changed("field_a", "field_b")` will set multiple fields as changed.
  - `obj.set_changed("field_a", original="old")` will set a single field as
    changed and also store its original value.
* `obj.reset_changed()` resets all changed fields.
* `obj.dict()` and `obj.json()` accept an additional parameter
  `exclude_unchanged`, which - when set to True - will only export the
  changed fields

### Example

```python
import pydantic
from pydantic_changedetect import ChangeDetectionMixin

class Something(ChangeDetectionMixin, pydantic.BaseModel):
    name: str


something = Something(name="something")
something.has_changed  # = False
something.__changed_fields__  # = set()
something.name = "something else"
something.has_changed  # = True
something.__changed_fields__  # = {"name"}
```

### Restrictions

`ChangeDetectionMixin` currently cannot detect changes inside lists, dicts and
other structured objects. In those cases you are required to set the changed
state yourself using `set_changed()`. It is recommended to pass the original
value to `set_changed()` when you want to also keep track of the actual changes
compared to the original value. Be advised to `.copy()` the original value
as lists/dicts will always be changed in place.

# Contributing

If you want to contribute to this project, feel free to just fork the project,
create a dev branch in your fork and then create a pull request (PR). If you
are unsure about whether your changes really suit the project please create an
issue first, to talk about this.

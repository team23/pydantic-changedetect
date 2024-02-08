import decimal
import warnings
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Literal,
    Optional,
    Set,
    Type,
    TypeVar,
    Union,
    cast,
    no_type_check,
    overload,
)

import pydantic

from ._compat import PYDANTIC_V1, PYDANTIC_V2, PydanticCompat
from .utils import is_pydantic_change_detect_annotation

if TYPE_CHECKING:  # pragma: no cover
    from pydantic.typing import AbstractSetIntStr, MappingIntStrAny
    if PYDANTIC_V1:
        from pydantic.typing import DictStrAny, SetStr
    if PYDANTIC_V2:
        from pydantic.main import IncEx

    Model = TypeVar("Model", bound="ChangeDetectionMixin")

NO_VALUE = object()


class ChangeDetectionMixin(pydantic.BaseModel):
    """
    Utility mixin to allow pydantic models to detect changes to fields.

    Example:
        ```python
        class Something(ChangeDetectionMixin, pydantic.BaseModel):
            name: str

        something = Something(name="Alice")
        something.model_has_changed  # False
        something.model_changed_fields  # empty
        something.name = "Bob"
        something.model_has_changed  # True
        something.model_changed_fields  # {"name"}
        something.model_self_changed_fields  # {"name": "Alice"}
        ```
    """

    if TYPE_CHECKING:  # pragma: no cover
        model_original: Dict[str, Any]
        model_self_changed_fields: Set[str]
        model_changed_markers: set[str]

    __slots__ = ("model_original", "model_self_changed_fields", "model_changed_markers")

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.model_reset_changed()

    def model_reset_changed(self) -> None:
        """
        Reset the changed state, this will clear model_self_changed_fields, model_original
        and remove all changed markers.
        """

        object.__setattr__(self, "model_original", {})
        object.__setattr__(self, "model_self_changed_fields", set())
        object.__setattr__(self, "model_changed_markers", set())

    @property
    def model_changed_fields(self) -> Set[str]:
        """Return list of all changed fields, submodels are considered as one field"""

        self_compat = PydanticCompat(self)

        changed_fields = self.model_self_changed_fields.copy()
        for field_name, model_field in self_compat.model_fields.items():
            field_value = self.__dict__[field_name]

            # Value is a ChangeDetectionMixin instance itself
            if (
                isinstance(field_value, ChangeDetectionMixin)
                and field_value.model_has_changed
            ):
                changed_fields.add(field_name)

            # Field contains ChangeDetectionMixin's, but inside list/dict structure
            elif (
                field_value
                and is_pydantic_change_detect_annotation(
                    self_compat.get_model_field_info_annotation(model_field),
                )
            ):
                # Collect all possible values
                if isinstance(field_value, (list, tuple)):
                    field_value_list = field_value
                elif isinstance(field_value, dict):
                    field_value_list = list(field_value.values())
                else:  # pragma: no cover
                    # Continue on unsupported type
                    # (should be already filtered by is_pydantic_change_detect_annotation)
                    continue

                # Check if any of the values has changed
                for inner_field_value in field_value_list:
                    if (
                        isinstance(inner_field_value, ChangeDetectionMixin)
                        and inner_field_value.model_has_changed
                    ):
                        changed_fields.add(field_name)
                        break

        return changed_fields

    @property
    def model_changed_fields_recursive(self) -> Set[str]:
        """Return a list of all changed fields recursive using dotted syntax"""

        self_compat = PydanticCompat(self)

        changed_fields = self.model_self_changed_fields.copy()
        for field_name, model_field in self_compat.model_fields.items():
            field_value = self.__dict__[field_name]

            # Value is a ChangeDetectionMixin instance itself
            if (
                    isinstance(field_value, ChangeDetectionMixin)
                    and field_value.model_has_changed
            ):
                changed_fields.add(field_name)
                for changed_field in field_value.model_changed_fields_recursive:
                    changed_fields.add(f"{field_name}.{changed_field}")

            # Field contains ChangeDetectionMixin's, but inside list/dict structure
            elif (
                field_value
                and is_pydantic_change_detect_annotation(
                    self_compat.get_model_field_info_annotation(model_field),
                )
            ):
                # Collect all possible values
                if isinstance(field_value, (list, tuple)):
                    field_value_list = list(enumerate(field_value))
                elif isinstance(field_value, dict):
                    field_value_list = list(field_value.items())
                else:  # pragma: no cover
                    # Continue on unsupported type
                    # (should be already filtered by is_pydantic_change_detect_annotation)
                    continue

                # Check if any of the values has changed
                for inner_field_index, inner_field_value in field_value_list:
                    if (
                        isinstance(inner_field_value, ChangeDetectionMixin)
                        and inner_field_value.model_has_changed
                    ):
                        for changed_field in inner_field_value.model_changed_fields_recursive:
                            changed_fields.add(f"{field_name}.{inner_field_index}.{changed_field}")
                        changed_fields.add(f"{field_name}.{inner_field_index}")
                        changed_fields.add(f"{field_name}")

        return changed_fields

    @property
    def model_has_changed(self) -> bool:
        """Return True, when some field was changed or some changed marker is set."""

        if self.model_self_changed_fields or self.model_changed_markers:
            return True

        return bool(self.model_changed_fields)

    @overload
    def model_set_changed(self, *fields: str) -> None: ...

    @overload
    def model_set_changed(self, field: str, /, *, original: Any = NO_VALUE) -> None: ...

    def model_set_changed(self, *fields: str, original: Any = NO_VALUE) -> None:
        """
        Set fields as changed.

        Optionally provide an original value for the field.
        """

        self_compat = PydanticCompat(self)

        # Ensure we have a valid call
        if original is not NO_VALUE and len(fields) > 1:
            raise RuntimeError(
                "Original value can only be used when only "
                "changing one field.",
            )

        # Ensure all fields exists
        for name in fields:
            if name not in self_compat.model_fields:
                raise AttributeError(f"Field {name} not available in this model")

        # Mark fields as changed
        for name in fields:
            if original is NO_VALUE:
                self.model_original[name] = self.__dict__[name]
            else:
                self.model_original[name] = original
            self.model_self_changed_fields.add(name)

    def _model_value_is_comparable_type(self, value: Any) -> bool:
        return (
            value is None
            or isinstance(value, (str, int, float, bool, decimal.Decimal))
        )

    @no_type_check
    def __setattr__(self, name, value) -> None:  # noqa: ANN001
        self_compat = PydanticCompat(self)

        # Private attributes need not to be handled
        if (
            self.__private_attributes__  # may be None
            and name in self.__private_attributes__
        ):
            super().__setattr__(name, value)
            return

        # Get original value
        original_update = {}
        if name in self_compat.model_fields and name not in self.model_original:
            original_update[name] = self.__dict__[name]

        # Store changed value using pydantic
        super().__setattr__(name, value)

        # Check if value has actually been changed
        has_changed = True
        if name in self_compat.model_fields:
            # Fetch original from original_update so we don't have to check everything again
            original_value = original_update.get(name, None)
            # Don't use value parameter directly, as pydantic validation might have changed it
            # (when validate_assignment == True)
            current_value = self.__dict__[name]
            if (
                self._model_value_is_comparable_type(original_value)
                and self._model_value_is_comparable_type(current_value)
                and original_value == current_value
            ):
                has_changed = False

        # Store changed state
        if has_changed:
            self.model_original.update(original_update)
            self.model_self_changed_fields.add(name)

    def __getstate__(self) -> Dict[str, Any]:
        state = super().__getstate__()
        state["model_original"] = self.model_original.copy()
        state["model_self_changed_fields"] = self.model_self_changed_fields.copy()
        state["model_changed_markers"] = self.model_changed_markers.copy()
        return state

    def __setstate__(self, state: Dict[str, Any]) -> None:
        super().__setstate__(state)
        if "model_original" in state:
            object.__setattr__(self, "model_original", state["model_original"])
        else:
            object.__setattr__(self, "model_original", {})
        if "model_self_changed_fields" in state:
            object.__setattr__(self, "model_self_changed_fields", state["model_self_changed_fields"])
        else:
            object.__setattr__(self, "model_self_changed_fields", set())
        if "model_changed_markers" in state:
            object.__setattr__(self, "model_changed_markers", state["model_changed_markers"])
        else:
            object.__setattr__(self, "model_changed_markers", set())

    def _get_changed_export_includes(
        self,
        exclude_unchanged: bool,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Return updated kwargs for json()/dict(), so only changed fields
        get exported when exclude_unchanged=True
        """

        if exclude_unchanged:
            changed_fields = self.model_changed_fields
            if "include" in kwargs and kwargs["include"] is not None:
                kwargs["include"] = {  # calculate intersect
                    i
                    for i
                    in kwargs["include"]
                    if i in changed_fields
                }
            else:
                kwargs["include"] = set(changed_fields)
        return kwargs

    # Restore model/value state

    @classmethod
    def model_restore_value(cls, value: Any, /) -> Any:
        """
        Restore original state of value if it contains any ChangeDetectionMixin
        instances.

        Contain might be:
        * value is a list containing such instances
        * value is a dict containing such instances
        * value is a ChangeDetectionMixin instance itself
        """

        if isinstance(value, list):
            return [
                cls.model_restore_value(v)
                for v
                in value
            ]
        elif isinstance(value, dict):
            return {
                k: cls.model_restore_value(v)
                for k, v
                in value.items()
            }
        elif (
            isinstance(value, ChangeDetectionMixin)
            and value.model_has_changed
        ):
            return value.model_restore_original()
        else:
            return value

    def model_restore_original(
        self: "Model",
    ) -> "Model":
        """Restore original state of a ChangeDetectionMixin object."""

        restored_values = {}
        for key, value in self.__dict__.items():
            restored_values[key] = self.model_restore_value(value)

        return self.__class__(
            **{
                **restored_values,
                **self.model_original,
            },
        )

    def model_get_original_field_value(self, field_name: str, /) -> Any:
        """Return original value for a field."""

        self_compat = PydanticCompat(self)

        if field_name not in self_compat.model_fields:
            raise AttributeError(f"Field {field_name} not available in this model")

        if field_name in self.model_original:
            return self.model_original[field_name]

        current_value = getattr(self, field_name)
        return self.model_restore_value(current_value)

    # Changed markers

    def model_mark_changed(self, marker: str) -> None:
        """
        Add marker for something being changed.

        Markers can be used to keep information about things being changed outside
        the model scope, but related to the model itself. This could for example
        be a marker for related objects being added/updated/removed.
        """

        self.model_changed_markers.add(marker)

    def model_unmark_changed(self, marker: str) -> None:
        """Remove one changed marker."""

        self.model_changed_markers.discard(marker)

    def model_has_changed_marker(
        self,
        marker: str,
    ) -> bool:
        """Check whether one changed marker is set."""

        return marker in self.model_changed_markers

    # pydantic 2.0 only methods

    if PYDANTIC_V2:
        @classmethod
        def model_construct(cls: Type["Model"], *args: Any, **kwargs: Any) -> "Model":
            """Construct an unvalidated instance"""

            m = cast("Model", super().model_construct(*args, **kwargs))
            m.model_reset_changed()
            return m

        def model_post_init(self, __context: Any) -> None:
            super().model_post_init(__context)
            self.model_reset_changed()

        def __copy__(self: "Model") -> "Model":
            clone = cast(
                "Model",
                super().__copy__(),
            )
            object.__setattr__(clone, "model_original", self.model_original.copy())
            object.__setattr__(clone, "model_self_changed_fields", self.model_self_changed_fields.copy())
            object.__setattr__(clone, "model_changed_markers", self.model_changed_markers.copy())
            return clone

        def __deepcopy__(self: "Model", memo: Optional[Dict[str, Any]] = None) -> "Model":
            clone = cast(
                "Model",
                super().__deepcopy__(memo=memo),
            )
            object.__setattr__(clone, "model_original", self.model_original.copy())
            object.__setattr__(clone, "model_self_changed_fields", self.model_self_changed_fields.copy())
            object.__setattr__(clone, "model_changed_markers", self.model_changed_markers.copy())
            return clone

        def model_dump(
            self,
            *,
            mode: Union[Literal['json', 'python'], str] = 'python',
            include: "IncEx" = None,
            exclude: "IncEx" = None,
            by_alias: bool = False,
            exclude_unset: bool = False,
            exclude_defaults: bool = False,
            exclude_none: bool = False,
            exclude_unchanged: bool = False,
            round_trip: bool = False,
            warnings: bool = True,
        ) -> Dict[str, Any]:
            """
            Generate a dictionary representation of the model, optionally specifying
            which fields to include or exclude.

            Extends normal pydantic method to also allow to use `exclude_unchanged`.
            """

            return super().model_dump(
                **self._get_changed_export_includes(
                    mode=mode,
                    include=include,
                    exclude=exclude,
                    by_alias=by_alias,
                    exclude_unset=exclude_unset,
                    exclude_defaults=exclude_defaults,
                    exclude_none=exclude_none,
                    exclude_unchanged=exclude_unchanged,
                    round_trip=round_trip,
                    warnings=warnings,
                ),
            )

        def model_dump_json(
            self,
            *,
            indent: Optional[int] = None,
            include: "IncEx" = None,
            exclude: "IncEx" = None,
            by_alias: bool = False,
            exclude_unset: bool = False,
            exclude_defaults: bool = False,
            exclude_none: bool = False,
            exclude_unchanged: bool = False,
            round_trip: bool = False,
            warnings: bool = True,
        ) -> str:
            """
            Generates a JSON representation of the model using Pydantic's `to_json`
            method.

            Extends normal pydantic method to also allow to use `exclude_unchanged`.
            """

            return super().model_dump_json(
                **self._get_changed_export_includes(
                    indent=indent,
                    include=include,
                    exclude=exclude,
                    by_alias=by_alias,
                    exclude_unset=exclude_unset,
                    exclude_defaults=exclude_defaults,
                    exclude_none=exclude_none,
                    exclude_unchanged=exclude_unchanged,
                    round_trip=round_trip,
                    warnings=warnings,
                ),
            )

    # Compatibility for pydantic 2.0 compatibility methods to support pydantic 1.0 migration 🙈

    def copy(
        self: "Model",
        *,
        include: "Union[AbstractSetIntStr, MappingIntStrAny, None]" = None,
        exclude: "Union[AbstractSetIntStr, MappingIntStrAny, None]" = None,
        update: Optional[Dict[str, Any]] = None,
        deep: bool = False,
    ) -> "Model":
        warnings.warn(
            "copy(...) is deprecated even in pydantic v2, use model_copy(...) instead",
            DeprecationWarning,
            stacklevel=2,
        )
        clone = cast(
            "Model",
            super().copy(
                include=include,
                exclude=exclude,
                update=update,
                deep=deep,
            ),
        )
        object.__setattr__(clone, "model_original", self.model_original.copy())
        object.__setattr__(clone, "model_self_changed_fields", self.model_self_changed_fields.copy())
        object.__setattr__(clone, "model_changed_markers", self.model_changed_markers.copy())
        return clone

    if PYDANTIC_V2:
        # The following methods are SLIGHTLY different fpr v1 and v2, so we need to keep
        # them separate

        def dict(
            self,
            *,
            include: Optional[Union['AbstractSetIntStr', 'MappingIntStrAny']] = None,
            exclude: Optional[Union['AbstractSetIntStr', 'MappingIntStrAny']] = None,
            by_alias: bool = False,
            exclude_unset: bool = False,
            exclude_defaults: bool = False,
            exclude_none: bool = False,
            exclude_unchanged: bool = False,
        ) -> Dict[str, Any]:
            """
            Generate a dictionary representation of the model, optionally
            specifying which fields to include or exclude.
            """

            return super().dict(
                **self._get_changed_export_includes(
                    include=include,
                    exclude=exclude,
                    by_alias=by_alias,
                    exclude_unset=exclude_unset,
                    exclude_defaults=exclude_defaults,
                    exclude_none=exclude_none,
                    exclude_unchanged=exclude_unchanged,
                ),
            )

        def json(
            self,
            include: Optional[Union['AbstractSetIntStr', 'MappingIntStrAny']] = None,
            exclude: Optional[Union['AbstractSetIntStr', 'MappingIntStrAny']] = None,
            by_alias: bool = False,
            exclude_unset: bool = False,
            exclude_defaults: bool = False,
            exclude_none: bool = False,
            exclude_unchanged: bool = False,
            **dumps_kwargs: Any,
        ) -> str:
            """
            Generate a JSON representation of the model, `include` and `exclude`
            arguments as per `dict()`.
            """

            return super().json(
                **self._get_changed_export_includes(
                    include=include,
                    exclude=exclude,
                    by_alias=by_alias,
                    exclude_unset=exclude_unset,
                    exclude_defaults=exclude_defaults,
                    exclude_none=exclude_none,
                    exclude_unchanged=exclude_unchanged,
                    **dumps_kwargs,
                ),
            )

    # Compatibility methods for pydantic v1

    if PYDANTIC_V1:  # pragma: no cover
        @classmethod
        def construct(cls: Type["Model"], *args: Any, **kwargs: Any) -> "Model":
            """Construct an unvalidated instance"""

            m = cast("Model", super().construct(*args, **kwargs))
            m.model_reset_changed()
            return m

        def _copy_and_set_values(
            self: "Model",
            values: 'DictStrAny',
            fields_set: 'SetStr',
            *,
            deep: bool,
        ) -> "Model":
            """
            Return a copy of the model instance, will be used in copy() (among others).
            """

            clone = cast(
                "Model",
                super()._copy_and_set_values(
                    values,
                    fields_set,
                    deep=deep,
                ),
            )
            object.__setattr__(clone, "model_original", self.model_original.copy())
            object.__setattr__(clone, "model_self_changed_fields", self.model_self_changed_fields.copy())
            object.__setattr__(clone, "model_changed_markers", self.model_changed_markers.copy())
            return clone

        def dict(  # type: ignore[misc]
            self,
            *,
            include: Optional[Union['AbstractSetIntStr', 'MappingIntStrAny']] = None,
            exclude: Optional[Union['AbstractSetIntStr', 'MappingIntStrAny']] = None,
            by_alias: bool = False,
            skip_defaults: Optional[bool] = None,
            exclude_unset: bool = False,
            exclude_defaults: bool = False,
            exclude_none: bool = False,
            exclude_unchanged: bool = False,
        ) -> Dict[str, Any]:
            """
            Generate a dictionary representation of the model, optionally
            specifying which fields to include or exclude.
            """

            return super().dict(
                **self._get_changed_export_includes(
                    include=include,
                    exclude=exclude,
                    by_alias=by_alias,
                    skip_defaults=skip_defaults,
                    exclude_unset=exclude_unset,
                    exclude_defaults=exclude_defaults,
                    exclude_none=exclude_none,
                    exclude_unchanged=exclude_unchanged,
                ),
            )

        def json(  # type: ignore[misc]
            self,
            include: Optional[Union['AbstractSetIntStr', 'MappingIntStrAny']] = None,
            exclude: Optional[Union['AbstractSetIntStr', 'MappingIntStrAny']] = None,
            by_alias: bool = False,
            skip_defaults: Optional[bool] = None,
            exclude_unset: bool = False,
            exclude_defaults: bool = False,
            exclude_none: bool = False,
            exclude_unchanged: bool = False,
            encoder: Optional[Callable[[Any], Any]] = None,
            models_as_dict: bool = True,
            **dumps_kwargs: Any,
        ) -> str:
            """
            Generate a JSON representation of the model, `include` and `exclude`
            arguments as per `dict()`.
            """

            return super().json(
                **self._get_changed_export_includes(
                    include=include,
                    exclude=exclude,
                    by_alias=by_alias,
                    skip_defaults=skip_defaults,
                    exclude_unset=exclude_unset,
                    exclude_defaults=exclude_defaults,
                    exclude_none=exclude_none,
                    exclude_unchanged=exclude_unchanged,
                    encoder=encoder,
                    models_as_dict=models_as_dict,
                    **dumps_kwargs,
                ),
            )

    # Compatibility methods for older versions of pydantic-changedetect

    def reset_changed(self) -> None:
        warnings.warn(
            "reset_changed() is deprecated, use model_reset_changed() instead",
            DeprecationWarning,
            stacklevel=2,
        )
        self.model_reset_changed()

    @property
    def __original__(self) -> Dict[str, Any]:
        warnings.warn(
            "__original__ is deprecated, use model_original instead",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.model_original

    @property
    def __self_changed_fields__(self) -> Set[str]:
        warnings.warn(
            "__self_changed_fields__ is deprecated, use model_self_changed_fields instead",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.model_self_changed_fields

    @property
    def __changed_fields__(self) -> Set[str]:
        warnings.warn(
            "__changed_fields__ is deprecated, use model_changed_fields instead",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.model_changed_fields

    @property
    def __changed_fields_recursive__(self) -> Set[str]:
        warnings.warn(
            "__changed_fields_recursive__ is deprecated, use model_changed_fields_recursive instead",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.model_changed_fields_recursive

    @property
    def has_changed(self) -> bool:
        warnings.warn(
            "has_changed is deprecated, use model_has_changed instead",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.model_has_changed

    @overload
    def set_changed(self, *fields: str) -> None: ...

    @overload
    def set_changed(self, field: str, /, *, original: Any = NO_VALUE) -> None: ...

    def set_changed(self, *fields: str, original: Any = NO_VALUE) -> None:
        warnings.warn(
            "set_changed(...) is deprecated, use model_set_changed(...) instead",
            DeprecationWarning,
            stacklevel=2,
        )
        self.model_set_changed(*fields, original=original)

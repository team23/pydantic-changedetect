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

    __slots__ = ("model_original", "model_self_changed_fields")

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.model_reset_changed()

    def model_reset_changed(self) -> None:
        """
        Reset the changed state, this will clear model_self_changed_fields and model_original
        """

        object.__setattr__(self, "model_original", {})
        object.__setattr__(self, "model_self_changed_fields", set())

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
                else:
                    # Continue on unsupported type
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
                else:
                    # Continue on unsupported type
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
        """Return True, when some field was changed"""

        if self.model_self_changed_fields:
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

        # Store changed data
        if name in self_compat.model_fields and name not in self.model_original:
            self.model_original[name] = self.__dict__[name]
        super().__setattr__(name, value)
        self.model_self_changed_fields.add(name)

    def __getstate__(self) -> Dict[str, Any]:
        state = super().__getstate__()
        state["model_original"] = self.model_original.copy()
        state["model_self_changed_fields"] = self.model_self_changed_fields.copy()
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

        def model_copy(
            self: "Model",
            *,
            update: Optional[Dict[str, Any]] = None,
            deep: bool = False,
        ) -> "Model":
            clone = cast(
                "Model",
                super().model_copy(
                    update=update,
                    deep=deep,
                ),
            )
            object.__setattr__(clone, "model_original", self.model_original.copy())
            object.__setattr__(clone, "model_self_changed_fields", self.model_self_changed_fields.copy())
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
            return clone

        def dict(  # type: ignore[misc]  # noqa: F811
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

        def json(  # type: ignore[misc]  # noqa: F811
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

from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
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

from .utils import safe_issubclass

if TYPE_CHECKING:
    from pydantic.typing import AbstractSetIntStr, DictStrAny, MappingIntStrAny, SetStr

NO_VALUE = object()

SelfT = TypeVar("SelfT", bound="ChangeDetectionMixin")


class ChangeDetectionMixin(pydantic.BaseModel):
    """
    Utility mixin to allow pydantic models to detect changes to fields.

    Example:
        ```python
        class Something(ChangeDetectionMixin, pydantic.BaseModel):
            name: str

        something = Something(name="Alice")
        something.has_changed  # False
        something.__changed_fields__  # empty
        something.name = "Bob"
        something.has_changed  # True
        something.__changed_fields__  # {"name"}
        ```
    """

    __original__: Dict[str, Any] = pydantic.PrivateAttr({})
    __self_changed_fields__: Set[str] = pydantic.PrivateAttr({})

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.reset_changed()

    def reset_changed(self) -> None:
        """Reset the changed state, this will clear __changed_fields__"""

        object.__setattr__(self, "__original__", {})
        object.__setattr__(self, "__self_changed_fields__", set())

    @property
    def __changed_fields__(self) -> Set[str]:
        """Return list of all changed fields, submodels are considered as one field"""

        changed_fields = self.__self_changed_fields__.copy()
        for field_name, model_field in self.__fields__.items():
            field_value = self.__dict__[field_name]

            # Value is a ChangeDetectionMixin instance itself
            if (
                isinstance(field_value, ChangeDetectionMixin)
                and field_value.has_changed
            ):
                changed_fields.add(field_name)

            # Field contains ChangeDetectionMixin's, but inside list/dict structure
            elif (
                field_value
                and safe_issubclass(model_field.type_, ChangeDetectionMixin)
            ):
                # Collect all possible values
                if isinstance(field_value, list):
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
                        and inner_field_value.has_changed
                    ):
                        changed_fields.add(field_name)
                        break

        return changed_fields

    @property
    def __changed_fields_recursive__(self) -> Set[str]:
        """Return a list of all changed fields recursive using dotted syntax"""

        changed_fields = self.__self_changed_fields__.copy()
        for field_name, model_field in self.__fields__.items():
            field_value = self.__dict__[field_name]

            # Value is a ChangeDetectionMixin instance itself
            if (
                    isinstance(field_value, ChangeDetectionMixin)
                    and field_value.has_changed
            ):
                changed_fields.add(field_name)
                for changed_field in field_value.__changed_fields_recursive__:
                    changed_fields.add(f"{field_name}.{changed_field}")

            # Field contains ChangeDetectionMixin's, but inside list/dict structure
            elif (
                field_value
                and safe_issubclass(model_field.type_, ChangeDetectionMixin)
            ):
                # Collect all possible values
                if isinstance(field_value, list):
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
                        and inner_field_value.has_changed
                    ):
                        for changed_field in inner_field_value.__changed_fields_recursive__:
                            changed_fields.add(f"{field_name}.{inner_field_index}.{changed_field}")
                        changed_fields.add(f"{field_name}.{inner_field_index}")
                        changed_fields.add(f"{field_name}")

        return changed_fields

    @property
    def has_changed(self) -> bool:
        """Return True, when some field was changed"""

        if self.__self_changed_fields__:
            return True

        return bool(self.__changed_fields__)

    @overload
    def set_changed(self, *fields: str) -> None: ...

    @overload
    def set_changed(self, field: str, /, *, original: Any = NO_VALUE) -> None: ...

    def set_changed(self, *fields: str, original: Any = NO_VALUE) -> None:
        """
        Set fields as changed.

        Optionally provide an original value for the field.
        """

        # Ensure we have a valid call
        if original is not NO_VALUE and len(fields) > 1:
            raise RuntimeError(
                "Original value can only be used when only "
                "changing one field.",
            )

        # Ensure all fields exists
        for name in fields:
            if name not in self.__fields__:
                raise AttributeError(f"Field {name} not available in this model")

        # Mark fields as changed
        for name in fields:
            if original is NO_VALUE:
                self.__original__[name] = self.__dict__[name]
            else:
                self.__original__[name] = original
            self.__self_changed_fields__.add(name)

    @no_type_check
    def __setattr__(self, name, value) -> None:  # noqa: ANN001
        # Private attributes need not to be handled
        if name in self.__private_attributes__:
            super().__setattr__(name, value)
            return

        # Store changed data
        if name in self.__fields__ and name not in self.__original__:
            self.__original__[name] = self.__dict__[name]
        super().__setattr__(name, value)
        self.__self_changed_fields__.add(name)

    @classmethod
    def construct(cls: Type["SelfT"], *args: Any, **kwargs: Any) -> "SelfT":
        """Construct an unvalidated instance"""

        m = cast(SelfT, super().construct(*args, **kwargs))
        m.reset_changed()
        return m

    def _copy_and_set_values(
        self: SelfT,
        values: 'DictStrAny',
        fields_set: 'SetStr',
        *,
        deep: bool,
    ) -> SelfT:
        """
        Return a copy of the model instance, will be used in copy() (among others).
        """

        m = cast(
            SelfT,
            super()._copy_and_set_values(
                values,
                fields_set,
                deep=deep,
            ),
        )
        object.__setattr__(m, "__original__", self.__original__.copy())
        object.__setattr__(m, "__self_changed_fields__", self.__self_changed_fields__.copy())
        return m

    def __getstate__(self) -> Dict[str, Any]:
        state = super().__getstate__()
        state["__original__"] = self.__original__.copy()
        state["__self_changed_fields__"] = self.__self_changed_fields__.copy()
        return state

    def __setstate__(self, state: Dict[str, Any]) -> None:
        super().__setstate__(state)
        if "__original__" in state:
            object.__setattr__(self, "__original__", state["__original__"])
        else:
            object.__setattr__(self, "__original__", {})
        if "__self_changed_fields__" in state:
            object.__setattr__(self, "__self_changed_fields__", state["__self_changed_fields__"])
        else:
            object.__setattr__(self, "__self_changed_fields__", set())

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
            changed_fields = self.__changed_fields__
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

    def dict(
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

    def json(
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

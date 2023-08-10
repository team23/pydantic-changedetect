from typing import Any, Dict, Optional, Type

import pydantic
from pydantic.fields import FieldInfo
from pydantic.version import VERSION as PYDANTIC_VERSION

PYDANTIC_V1 = PYDANTIC_VERSION.startswith("1.")
PYDANTIC_V2 = PYDANTIC_VERSION.startswith("2.")

if PYDANTIC_V1:  # pragma: no cover
    class PydanticCompat:
        obj: pydantic.BaseModel

        def __init__(
            self,
            obj: pydantic.BaseModel,
        ) -> None:
            self.obj = obj

        @property
        def model_fields(self) -> Dict[str, FieldInfo]:
            return self.obj.__fields__

        def get_model_field_info_annotation(self, model_field: FieldInfo) -> type:
            return model_field.type_  # type: ignore

elif PYDANTIC_V2:  # pragma: no cover
    class PydanticCompat:  # type: ignore
        obj: pydantic.BaseModel

        def __init__(
            self,
            obj: pydantic.BaseModel,
        ) -> None:
            self.obj = obj

        @property
        def model_fields(self) -> Dict[str, FieldInfo]:
            return self.obj.model_fields

        def get_model_field_info_annotation(self, model_field: FieldInfo) -> Optional[Type[Any]]:
            return model_field.annotation

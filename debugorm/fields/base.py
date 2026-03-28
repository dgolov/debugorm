from __future__ import annotations
from typing import Any, Optional


class Field:
    """Base class for all ORM fields."""

    def __init__(
        self,
        primary_key: bool = False,
        null: bool = False,
        default: Any = None,
    ) -> None:
        self.primary_key = primary_key
        self.null = null
        self.default = default
        self.name: Optional[str] = None

    def contribute_to_class(self, model_class: type, name: str) -> None:
        self.name = name
        self.model = model_class

    def validate(self, value: Any) -> None:
        if value is None and not self.null and not self.primary_key:
            raise ValueError(f"Field '{self.name}' cannot be null")

    def to_db(self, value: Any) -> Any:
        return value

    def from_db(self, value: Any) -> Any:
        return value

    def get_sql_type(self) -> str:
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r}, pk={self.primary_key})"

from __future__ import annotations
from typing import Any, Optional

from .base import Field


class IntegerField(Field):
    """Maps to SQLite INTEGER."""

    def validate(self, value: Any) -> None:
        super().validate(value)
        if value is not None and not isinstance(value, int):
            raise TypeError(
                f"Field '{self.name}' expects int, got {type(value).__name__}"
            )

    def to_db(self, value: Any) -> Optional[int]:
        return int(value) if value is not None else None

    def from_db(self, value: Any) -> Optional[int]:
        return int(value) if value is not None else None

    def get_sql_type(self) -> str:
        return "INTEGER"

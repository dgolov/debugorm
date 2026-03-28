from __future__ import annotations
from typing import Any, Optional

from .base import Field


class StringField(Field):
    """Maps to SQLite TEXT."""

    def __init__(self, max_length: int = 255, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.max_length = max_length

    def validate(self, value: Any) -> None:
        super().validate(value)
        if value is not None and not isinstance(value, str):
            raise TypeError(
                f"Field '{self.name}' expects str, got {type(value).__name__}"
            )
        if value is not None and len(value) > self.max_length:
            raise ValueError(
                f"Field '{self.name}': {len(value)} chars exceeds max_length={self.max_length}"
            )

    def to_db(self, value: Any) -> Optional[str]:
        return str(value) if value is not None else None

    def from_db(self, value: Any) -> Optional[str]:
        return str(value) if value is not None else None

    def get_sql_type(self) -> str:
        return "TEXT"

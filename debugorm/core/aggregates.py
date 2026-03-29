from __future__ import annotations


class Aggregate:
    """Base class for SQL aggregate functions."""

    sql_function: str = ""

    def __init__(self, field: str) -> None:
        self.field = field
        self.alias: str = ""

    def to_sql(self) -> str:
        return f"{self.sql_function}({self.field})"

    def as_sql_fragment(self) -> str:
        return f"{self.to_sql()} AS {self.alias}" if self.alias else self.to_sql()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.field!r})"


class Avg(Aggregate):
    sql_function = "AVG"


class Max(Aggregate):
    sql_function = "MAX"


class Min(Aggregate):
    sql_function = "MIN"


class Sum(Aggregate):
    sql_function = "SUM"


class Count(Aggregate):
    """COUNT(field) — defaults to COUNT(*)"""

    sql_function = "COUNT"

    def __init__(self, field: str = "*") -> None:
        super().__init__(field)

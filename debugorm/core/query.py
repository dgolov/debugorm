from __future__ import annotations
import copy
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


OPERATOR_MAP: Dict[str, str] = {
    "eq":     "=",
    "ne":     "!=",
    "gt":     ">",
    "gte":    ">=",
    "lt":     "<",
    "lte":    "<=",
    "like":   "LIKE",
    "ilike":  "LIKE",
    "in":     "IN",
    "isnull": "IS NULL",
}


@dataclass
class FilterCondition:
    """A single WHERE predicate stored as a structured object, not a SQL string."""

    field: str
    operator: str
    value: Any

    def __str__(self) -> str:
        if self.operator in ("IS NULL", "IS NOT NULL"):
            return f"{self.field} {self.operator}"
        return f"{self.field} {self.operator} {self.value!r}"

    def identity_key(self) -> str:
        """Identifies *which* predicate this is (field + operator) for diffing."""
        return f"{self.field}__{self.operator}"


@dataclass
class OrderByClause:
    field: str
    descending: bool = False

    def __str__(self) -> str:
        return f"{self.field} {'DESC' if self.descending else 'ASC'}"


class Query:
    """
    Structured, SQL-free representation of a database query.

    This is the single source of truth for query intent.  ``SQLCompiler``
    reads it and produces a ``(sql, params)`` pair; plugins inspect and
    optionally modify it before that happens.
    """

    def __init__(self, model_class: type) -> None:
        self.model = model_class
        self.table: str = model_class._table_name
        self.query_type: str = "SELECT"

        self.conditions: List[FilterCondition] = []
        self.or_groups: List[List[FilterCondition]] = []
        self.exclude_groups: List[List[FilterCondition]] = []
        self.order_by_clauses: List[OrderByClause] = []
        self.limit_value: Optional[int] = None
        self.offset_value: Optional[int] = None
        self.select_fields: Optional[List[str]] = None

        self.data: Dict[str, Any] = {}
        self.pk_value: Any = None

    def _parse_condition(self, field_lookup: str, value: Any) -> FilterCondition:
        parts = field_lookup.split("__", 1)
        field_name = parts[0]
        op_key = parts[1] if len(parts) == 2 else "eq"

        operator = OPERATOR_MAP.get(op_key)
        if operator is None:
            raise ValueError(
                f"Unknown lookup operator {op_key!r}. Available: {list(OPERATOR_MAP)}"
            )

        if op_key == "isnull":
            operator = "IS NULL" if value else "IS NOT NULL"
            value = None

        return FilterCondition(field_name, operator, value)

    def add_filter(self, field_lookup: str, value: Any) -> "Query":
        """
        Parse a Django-style lookup string and append a ``FilterCondition``.

        Examples: ``age__gt`` → ``age > ?``, ``name`` → ``name = ?``
        """
        self.conditions.append(self._parse_condition(field_lookup, value))
        return self

    def add_exclude_group(self, lookups: Dict[str, Any]) -> "Query":
        """
        Add a NOT group.  Each call to ``exclude()`` on a QuerySet becomes
        one group so that::

            .exclude(a=1).exclude(b=2)  →  NOT (a = 1) AND NOT (b = 2)
            .exclude(a=1, b=2)          →  NOT (a = 1 AND b = 2)
        """
        self.exclude_groups.append(
            [self._parse_condition(k, v) for k, v in lookups.items()]
        )
        return self

    def add_or_group(self, lookups: Dict[str, Any]) -> "Query":
        """Add a group of conditions that is OR-joined to the rest of the WHERE clause."""
        self.or_groups.append(
            [self._parse_condition(k, v) for k, v in lookups.items()]
        )
        return self

    def copy(self) -> "Query":
        return copy.deepcopy(self)

    def diff(self, other: "Query") -> str:
        """
        Compare two queries at the internal representation level.

        Returns a unified-diff-style string.  Comparison happens on
        ``FilterCondition`` objects, not on SQL strings.
        """
        lines: List[str] = []

        lines.extend(self._diff_conditions(self.conditions, other.conditions))

        for i in range(max(len(self.or_groups), len(other.or_groups))):
            self_g = self.or_groups[i] if i < len(self.or_groups) else []
            other_g = other.or_groups[i] if i < len(other.or_groups) else []
            lines.extend(self._diff_conditions(self_g, other_g, prefix="OR: "))

        for i in range(max(len(self.exclude_groups), len(other.exclude_groups))):
            self_g = self.exclude_groups[i] if i < len(self.exclude_groups) else []
            other_g = other.exclude_groups[i] if i < len(other.exclude_groups) else []
            lines.extend(self._diff_conditions(self_g, other_g, prefix="NOT: "))

        self_order = [str(o) for o in self.order_by_clauses]
        other_order = [str(o) for o in other.order_by_clauses]
        if self_order != other_order:
            if self_order:
                lines.append(f"- ORDER BY {', '.join(self_order)}")
            if other_order:
                lines.append(f"+ ORDER BY {', '.join(other_order)}")

        if self.limit_value != other.limit_value:
            if self.limit_value is not None:
                lines.append(f"- LIMIT {self.limit_value}")
            if other.limit_value is not None:
                lines.append(f"+ LIMIT {other.limit_value}")

        if self.offset_value != other.offset_value:
            if self.offset_value is not None:
                lines.append(f"- OFFSET {self.offset_value}")
            if other.offset_value is not None:
                lines.append(f"+ OFFSET {other.offset_value}")

        return "\n".join(lines) if lines else "Queries are identical"

    @staticmethod
    def _diff_conditions(
        self_conds: List[FilterCondition],
        other_conds: List[FilterCondition],
        prefix: str = "",
    ) -> List[str]:
        lines = []
        self_by_key = {c.identity_key(): c for c in self_conds}
        other_by_key = {c.identity_key(): c for c in other_conds}
        seen = list(self_by_key) + [k for k in other_by_key if k not in self_by_key]

        for key in seen:
            in_self = key in self_by_key
            in_other = key in other_by_key
            if in_self and not in_other:
                lines.append(f"- {prefix}{self_by_key[key]}")
            elif not in_self and in_other:
                lines.append(f"+ {prefix}{other_by_key[key]}")
            elif str(self_by_key[key]) != str(other_by_key[key]):
                lines.append(f"- {prefix}{self_by_key[key]}")
                lines.append(f"+ {prefix}{other_by_key[key]}")
        return lines

    def __repr__(self) -> str:
        return (
            f"Query(model={self.model.__name__!r}, "
            f"type={self.query_type!r}, "
            f"conditions={self.conditions!r})"
        )

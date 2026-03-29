from __future__ import annotations
from dataclasses import dataclass
from typing import Any, List, Tuple

from .query import FilterCondition, Query


@dataclass
class CompiledQuery:
    """The output of SQL compilation: a statement string and its parameter tuple."""

    sql: str
    params: Tuple[Any, ...]
    query: Query

    def __str__(self) -> str:
        return self.sql

    def interpolated(self) -> str:
        """SQL with parameters substituted inline — for display only."""
        result = self.sql
        for p in self.params:
            placeholder = f"'{p}'" if isinstance(p, str) else str(p)
            result = result.replace("?", placeholder, 1)
        return result


class SQLCompiler:
    """Translates a ``Query`` object into a ``CompiledQuery``."""

    def compile(self, query: Query) -> CompiledQuery:
        handlers = {
            "SELECT": self._compile_select,
            "INSERT": self._compile_insert,
            "UPDATE": self._compile_update,
            "DELETE": self._compile_delete,
        }
        handler = handlers.get(query.query_type)
        if handler is None:
            raise ValueError(f"Unknown query type: {query.query_type!r}")
        return handler(query)

    def _compile_select(self, query: Query) -> CompiledQuery:
        fields = "*" if not query.select_fields else ", ".join(query.select_fields)
        sql = f"SELECT {fields} FROM {query.table}"
        params: List[Any] = []

        where, where_params = self._compile_where(query)
        if where:
            sql += f" WHERE {where}"
            params.extend(where_params)

        if query.order_by_clauses:
            order = ", ".join(
                f"{c.field} {'DESC' if c.descending else 'ASC'}"
                for c in query.order_by_clauses
            )
            sql += f" ORDER BY {order}"

        if query.limit_value is not None:
            sql += " LIMIT ?"
            params.append(query.limit_value)
        elif query.offset_value is not None:
            sql += " LIMIT -1"

        if query.offset_value is not None:
            sql += " OFFSET ?"
            params.append(query.offset_value)

        return CompiledQuery(sql=sql, params=tuple(params), query=query)

    def _compile_insert(self, query: Query) -> CompiledQuery:
        columns = list(query.data.keys())
        values = list(query.data.values())
        placeholders = ", ".join(["?"] * len(columns))
        sql = (
            f"INSERT INTO {query.table} "
            f"({', '.join(columns)}) VALUES ({placeholders})"
        )
        return CompiledQuery(sql=sql, params=tuple(values), query=query)

    def _compile_update(self, query: Query) -> CompiledQuery:
        pk_name = self._pk_field_name(query)
        set_parts: List[str] = []
        params: List[Any] = []

        for col, val in query.data.items():
            if col != pk_name:
                set_parts.append(f"{col} = ?")
                params.append(val)

        sql = f"UPDATE {query.table} SET {', '.join(set_parts)}"

        where, where_params = self._compile_where(query)
        if where:
            sql += f" WHERE {where}"
            params.extend(where_params)
        elif query.pk_value is not None:
            sql += f" WHERE {pk_name} = ?"
            params.append(query.pk_value)

        return CompiledQuery(sql=sql, params=tuple(params), query=query)

    def _compile_delete(self, query: Query) -> CompiledQuery:
        pk_name = self._pk_field_name(query)
        sql = f"DELETE FROM {query.table}"
        params: List[Any] = []

        where, where_params = self._compile_where(query)
        if where:
            sql += f" WHERE {where}"
            params.extend(where_params)
        elif query.pk_value is not None:
            sql += f" WHERE {pk_name} = ?"
            params.append(query.pk_value)

        return CompiledQuery(sql=sql, params=tuple(params), query=query)

    def _compile_where(self, query: Query) -> Tuple[str, List[Any]]:
        """
        Build a WHERE clause that supports:
        - AND conditions (``filter``)
        - OR groups     (``or_filter``)
        - NOT conditions (``exclude``)

        Generated form::

            (cond1 AND cond2) OR (or_group1) OR (or_group2) AND NOT (excl1 AND excl2)
        """
        has_main = bool(query.conditions)
        has_or = bool(query.or_groups)
        has_excl = bool(query.exclude_groups)

        if not has_main and not has_or and not has_excl:
            return "", []

        params: List[Any] = []
        top_parts: List[str] = []

        if has_main or has_or:
            or_clauses: List[str] = []

            if has_main:
                sql, p = self._build_and_conditions(query.conditions)
                or_clauses.append(sql)
                params.extend(p)

            for group in query.or_groups:
                sql, p = self._build_and_conditions(group)
                or_clauses.append(sql)
                params.extend(p)

            if len(or_clauses) == 1:
                top_parts.append(or_clauses[0])
            else:
                top_parts.append(" OR ".join(f"({c})" for c in or_clauses))

        for group in query.exclude_groups:
            sql, p = self._build_and_conditions(group)
            top_parts.append(f"NOT ({sql})")
            params.extend(p)

        return " AND ".join(top_parts), params

    def _build_and_conditions(
        self, conditions: List[FilterCondition]
    ) -> Tuple[str, List[Any]]:
        parts: List[str] = []
        params: List[Any] = []

        for cond in conditions:
            if cond.operator == "IN":
                placeholders = ", ".join(["?"] * len(cond.value))
                parts.append(f"{cond.field} IN ({placeholders})")
                params.extend(cond.value)
            elif cond.operator in ("IS NULL", "IS NOT NULL"):
                parts.append(f"{cond.field} {cond.operator}")
            else:
                parts.append(f"{cond.field} {cond.operator} ?")
                params.append(cond.value)

        return " AND ".join(parts), params

    def _pk_field_name(self, query: Query) -> str:
        for name, f in query.model._fields.items():
            if f.primary_key:
                return name
        return "id"

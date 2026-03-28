from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .compiler import CompiledQuery, SQLCompiler
from ..db.connection import Connection, get_connection

if TYPE_CHECKING:
    from .query import Query
    from ..plugins.base import Plugin


@dataclass
class QueryResult:
    """Everything available to the caller after a query runs."""

    rows: List[Dict[str, Any]]
    rowcount: int
    compiled: CompiledQuery
    execution_time: float = 0.0
    last_insert_id: Optional[int] = None

    def __repr__(self) -> str:
        return (
            f"QueryResult(rowcount={self.rowcount}, "
            f"time={self.execution_time * 1000:.2f}ms)"
        )


@dataclass
class PipelineContext:
    """
    Shared context threaded through every hook in a single pipeline run.

    Plugins can store per-run state in ``extra`` instead of using instance
    variables, which keeps plugin instances reusable across parallel runs.
    """

    connection: Connection
    extra: Dict[str, Any] = field(default_factory=dict)


class QueryExecutor:
    def __init__(self, connection: Optional[Connection] = None) -> None:
        self._connection = connection

    @property
    def connection(self) -> Connection:
        return self._connection or get_connection()

    def execute(self, compiled: CompiledQuery) -> QueryResult:
        start = time.perf_counter()
        qtype = compiled.query.query_type

        if qtype == "SELECT":
            rows_raw = self.connection.fetchall(compiled.sql, compiled.params)
            rows = [dict(r) for r in rows_raw]
            return QueryResult(
                rows=rows,
                rowcount=len(rows),
                compiled=compiled,
                execution_time=time.perf_counter() - start,
            )

        cursor = self.connection.execute(compiled.sql, compiled.params)
        return QueryResult(
            rows=[],
            rowcount=cursor.rowcount,
            compiled=compiled,
            execution_time=time.perf_counter() - start,
            last_insert_id=cursor.lastrowid if qtype == "INSERT" else None,
        )


class QueryPipeline:
    """
    Orchestrates the full lifecycle of a single query.

    Execution order:
        1. ``before_compile``  — plugins may inspect / modify the Query
        2. SQL compilation     — ``SQLCompiler`` produces a ``CompiledQuery``
        3. ``after_compile``   — plugins may inspect the generated SQL
        4. ``before_execute``  — plugins may intercept (return a ``QueryResult`` to skip DB)
        5. DB execution        — ``QueryExecutor`` hits SQLite
        6. ``after_execute``   — plugins may inspect results
    """

    def __init__(
        self,
        plugins: Optional[List["Plugin"]] = None,
        connection: Optional[Connection] = None,
    ) -> None:
        self.plugins: List["Plugin"] = list(plugins or [])
        self.compiler = SQLCompiler()
        self.executor = QueryExecutor(connection)

    @property
    def connection(self) -> Connection:
        return self.executor.connection

    def with_plugins(self, additional: List["Plugin"]) -> "QueryPipeline":
        """Return a new pipeline with *additional* plugins appended."""
        return QueryPipeline(
            plugins=self.plugins + additional,
            connection=self.executor._connection,
        )

    def run(self, query: "Query") -> QueryResult:
        ctx = PipelineContext(connection=self.connection)

        for plugin in self.plugins:
            plugin.before_compile(query, ctx)

        compiled = self.compiler.compile(query)

        for plugin in self.plugins:
            plugin.after_compile(compiled, ctx)

        for plugin in self.plugins:
            intercepted = plugin.before_execute(compiled, ctx)
            if intercepted is not None:
                for p in self.plugins:
                    p.after_execute(intercepted, ctx)
                return intercepted

        result = self.executor.execute(compiled)

        for plugin in self.plugins:
            plugin.after_execute(result, ctx)

        return result

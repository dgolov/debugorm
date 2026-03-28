from __future__ import annotations
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.query import Query
    from ..core.compiler import CompiledQuery
    from ..core.pipeline import PipelineContext, QueryResult


class Plugin:
    """
    Base class for all DebugORM plugins.

    Hook execution order for a single query::

        before_compile(query, ctx)
            ↓  [SQLCompiler.compile]
        after_compile(compiled, ctx)
            ↓
        before_execute(compiled, ctx)   ← return a QueryResult to skip execution
            ↓  [QueryExecutor.execute]
        after_execute(result, ctx)
    """

    name: str = "base"

    def before_compile(self, query: "Query", ctx: "PipelineContext") -> None:
        """Inspect or modify the ``Query`` before SQL generation."""

    def after_compile(self, compiled: "CompiledQuery", ctx: "PipelineContext") -> None:
        """Inspect or modify the generated SQL."""

    def before_execute(
        self,
        compiled: "CompiledQuery",
        ctx: "PipelineContext",
    ) -> Optional["QueryResult"]:
        """
        Called right before the query hits the database.

        Return a ``QueryResult`` to intercept execution (dry-run pattern).
        Return ``None`` to continue normally.
        """
        return None

    def after_execute(self, result: "QueryResult", ctx: "PipelineContext") -> None:
        """Inspect results, log timings, etc."""

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"

from __future__ import annotations
from typing import Optional, TYPE_CHECKING

from .base import Plugin

if TYPE_CHECKING:
    from ..core.compiler import CompiledQuery
    from ..core.pipeline import PipelineContext, QueryResult


class DryRunPlugin(Plugin):
    """
    Prevents query execution.

    Prints the SQL that *would* run and estimates how many rows would be
    affected (via a COUNT sub-query for SELECT/UPDATE/DELETE, or '1 row'
    for INSERT).  Returns a synthetic ``QueryResult`` to short-circuit the
    pipeline.
    """

    name = "dry_run"

    def before_execute(
        self,
        compiled: "CompiledQuery",
        ctx: "PipelineContext",
    ) -> Optional["QueryResult"]:
        from ..core.pipeline import QueryResult

        sep = "─" * 60
        estimated = self._estimate(compiled, ctx)

        print(f"\n╔{sep}╗")
        print("║  [DryRunPlugin]  ⚠  NOT EXECUTED")
        print(f"╠{sep}╣")
        print(f"║  Type  : {compiled.query.query_type}")
        print(f"║  SQL   : {compiled.sql}")
        if compiled.params:
            print(f"║  Params: {compiled.params}")
        print(f"║  Interpolated: {compiled.interpolated()}")
        print(f"╠{sep}╣")
        print(f"║  Estimated rows affected: ~{estimated}")
        print(f"╚{sep}╝\n")

        return QueryResult(rows=[], rowcount=0, compiled=compiled)

    def _estimate(self, compiled: "CompiledQuery", ctx: "PipelineContext") -> str:
        if compiled.query.query_type == "INSERT":
            return "1 (new row)"

        try:
            from ..core.compiler import SQLCompiler

            count_query = compiled.query.copy()
            count_query.query_type = "SELECT"
            count_query.select_fields = ["COUNT(*) as count"]
            count_query.limit_value = None
            count_query.offset_value = None
            count_query.order_by_clauses = []

            count_compiled = SQLCompiler().compile(count_query)
            rows = ctx.connection.fetchall(count_compiled.sql, count_compiled.params)
            if rows:
                return str(dict(rows[0]).get("count", "?"))
        except Exception:
            pass

        return "?"

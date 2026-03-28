from __future__ import annotations
from typing import Optional, TYPE_CHECKING

from .base import Plugin

if TYPE_CHECKING:
    from ..core.query import Query
    from ..core.compiler import CompiledQuery
    from ..core.pipeline import PipelineContext, QueryResult


class ExplainPlugin(Plugin):
    """
    Runs ``EXPLAIN QUERY PLAN`` after query execution and prints a
    human-readable breakdown of the SQLite execution plan.
    """

    name = "explain"

    def __init__(self, verbose: bool = False) -> None:
        self.verbose = verbose
        self._compiled: Optional["CompiledQuery"] = None

    def after_compile(self, compiled: "CompiledQuery", ctx: "PipelineContext") -> None:
        self._compiled = compiled

    def after_execute(self, result: "QueryResult", ctx: "PipelineContext") -> None:
        if self._compiled is None:
            return

        sep = "─" * 60
        compiled = self._compiled

        print(f"\n╔{sep}╗")
        print(f"║  [ExplainPlugin]")
        print(f"╠{sep}╣")
        print(f"║  SQL  : {compiled.sql}")
        if compiled.params:
            print(f"║  Params: {compiled.params}")
        print(f"╠{sep}╣")
        print(f"║  QUERY PLAN")

        try:
            rows = ctx.connection.fetchall(
                f"EXPLAIN QUERY PLAN {compiled.sql}", compiled.params
            )
            if rows:
                for row in rows:
                    d = dict(row)
                    indent = "  " * d.get("indent", 0)
                    print(f"║    {indent}└── {d.get('detail', d)}")
            else:
                print("║    (no plan returned)")
        except Exception as exc:
            print(f"║    [error: {exc}]")

        print(f"╚{sep}╝\n")

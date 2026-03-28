from __future__ import annotations
import re
from typing import List, TYPE_CHECKING

from .base import Plugin

if TYPE_CHECKING:
    from ..core.compiler import CompiledQuery
    from ..core.pipeline import PipelineContext


_CLAUSE_RE = re.compile(
    r"\b(SELECT|FROM|WHERE|AND|OR|ORDER BY|GROUP BY|HAVING|LIMIT|OFFSET"
    r"|INSERT INTO|VALUES|UPDATE|SET|DELETE FROM"
    r"|INNER JOIN|LEFT JOIN|RIGHT JOIN|FULL JOIN|JOIN|ON)\b",
    re.IGNORECASE,
)


def _format_sql(sql: str) -> str:
    """
    Format a SQL string so that each major clause starts on its own indented line.

    This is display-only — the original ``CompiledQuery.sql`` is never modified.
    """
    sql = " ".join(sql.split())

    tokens: List[tuple] = []
    pos = 0
    for match in _CLAUSE_RE.finditer(sql):
        if match.start() > pos:
            tokens.append(("text", sql[pos : match.start()]))
        tokens.append(("keyword", match.group().upper()))
        pos = match.end()
    if pos < len(sql):
        tokens.append(("text", sql[pos:]))

    lines: List[str] = []
    current = ""
    for kind, text in tokens:
        if kind == "keyword":
            if current:
                lines.append(current)
            current = text
        else:
            current += text
    if current:
        lines.append(current)

    return "\n".join(
        line if i == 0 else "  " + line.strip()
        for i, line in enumerate(lines)
    )


class PrettyPrintPlugin(Plugin):
    """Formats the compiled SQL for human readability after compilation."""

    name = "pretty_print"

    def after_compile(self, compiled: "CompiledQuery", ctx: "PipelineContext") -> None:
        sep = "─" * 60

        print(f"\n╔{sep}╗")
        print("║  [PrettyPrintPlugin]  Formatted SQL")
        print(f"╠{sep}╣")
        for line in _format_sql(compiled.sql).splitlines():
            print(f"║  {line}")
        if compiled.params:
            print(f"╠{sep}╣")
            print(f"║  Params: {compiled.params}")
        print(f"╚{sep}╝\n")

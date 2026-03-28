from __future__ import annotations
import json
from typing import Any, Dict, List, TYPE_CHECKING

from .base import Plugin

if TYPE_CHECKING:
    from ..core.query import Query
    from ..core.pipeline import PipelineContext


class VisualizePlugin(Plugin):
    """
    Renders the ``Query`` as a human-readable tree *before* compilation,
    showing intent rather than generated SQL::

        User (SELECT)
        ├── filter: age > 18
        ├── order_by: age DESC
        └── limit: 10

    Pass ``show_json=True`` to also emit a JSON representation.
    """

    name = "visualize"

    def __init__(self, show_json: bool = False) -> None:
        self.show_json = show_json

    def before_compile(self, query: "Query", ctx: "PipelineContext") -> None:
        sep = "─" * 60
        lines: List[str] = []

        for cond in query.conditions:
            lines.append(f"filter: {cond}")
        for o in query.order_by_clauses:
            lines.append(f"order_by: {o}")
        if query.limit_value is not None:
            lines.append(f"limit: {query.limit_value}")
        if query.offset_value is not None:
            lines.append(f"offset: {query.offset_value}")
        if query.select_fields:
            lines.append(f"fields: {', '.join(query.select_fields)}")

        print(f"\n╔{sep}╗")
        print(f"║  [VisualizePlugin]  Query Structure")
        print(f"╠{sep}╣")
        print(f"║  {query.model.__name__} ({query.query_type})")

        for i, line in enumerate(lines):
            connector = "└──" if i == len(lines) - 1 else "├──"
            print(f"║   {connector} {line}")

        if not lines:
            print("║   └── (no constraints)")

        if self.show_json:
            print(f"╠{sep}╣")
            for json_line in json.dumps(self._to_dict(query), indent=2).splitlines():
                print(f"║    {json_line}")

        print(f"╚{sep}╝\n")

    def _to_dict(self, query: "Query") -> Dict[str, Any]:
        return {
            "model": query.model.__name__,
            "table": query.table,
            "type": query.query_type,
            "conditions": [
                {"field": c.field, "operator": c.operator, "value": c.value}
                for c in query.conditions
            ],
            "order_by": [
                {"field": o.field, "descending": o.descending}
                for o in query.order_by_clauses
            ],
            "limit": query.limit_value,
            "offset": query.offset_value,
            "select_fields": query.select_fields,
        }

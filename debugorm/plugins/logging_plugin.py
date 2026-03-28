from __future__ import annotations
import logging
import time
from typing import Optional, TYPE_CHECKING

from .base import Plugin

if TYPE_CHECKING:
    from ..core.compiler import CompiledQuery
    from ..core.pipeline import PipelineContext, QueryResult


class LoggingPlugin(Plugin):
    """
    Logs every SQL query and its execution time via Python's ``logging`` module.

    Integrates with any existing log configuration::

        logging.basicConfig(level=logging.DEBUG)
        User.objects.debug(log=True).filter(age__gt=18).all()
    """

    name = "logging"

    def __init__(
        self,
        logger: Optional[logging.Logger] = None,
        level: int = logging.DEBUG,
    ) -> None:
        self.logger = logger or logging.getLogger("debugorm.sql")
        self.level = level

    def before_execute(
        self,
        compiled: "CompiledQuery",
        ctx: "PipelineContext",
    ) -> None:
        ctx.extra["_log_start"] = time.perf_counter()
        self.logger.log(
            self.level,
            "SQL ▶ %s  params=%s",
            compiled.sql,
            compiled.params or "(none)",
        )
        return None

    def after_execute(self, result: "QueryResult", ctx: "PipelineContext") -> None:
        start = ctx.extra.pop("_log_start", None)
        elapsed_ms = (time.perf_counter() - start) * 1000 if start else 0.0
        self.logger.log(
            self.level,
            "SQL ◀ rows=%d  time=%.2fms",
            result.rowcount,
            elapsed_ms,
        )

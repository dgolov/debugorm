"""
DebugORM — a minimal, plugin-driven ORM for understanding and debugging SQL.

Quick start::

    from debugorm import configure, Model
    from debugorm.fields import IntegerField, StringField

    configure("myapp.db")   # or ":memory:"

    class User(Model):
        id   = IntegerField(primary_key=True)
        name = StringField()
        age  = IntegerField()

    User.create_table()

    alice = User(name="Alice", age=25)
    alice.save()

    users = User.objects.filter(age__gt=18).order_by("-age").all()

    # Debug any query on the fly
    User.objects.debug(explain=True, pretty=True).filter(age__gt=18).all()

    # Compare two queries
    q1 = User.objects.filter(age__gt=18)
    q2 = User.objects.filter(age__gt=21)
    print(q1.diff(q2))
"""

from .core.model import Model
from .core.query import Query
from .core.pipeline import QueryPipeline, QueryResult, PipelineContext
from .core.compiler import SQLCompiler, CompiledQuery
from .core.manager import Manager, QuerySet
from .db.connection import configure, get_connection, set_connection, Connection
from .fields import Field, IntegerField, StringField
from .core.aggregates import Aggregate, Avg, Max, Min, Sum, Count
from .plugins import (
    Plugin,
    ExplainPlugin,
    DryRunPlugin,
    LoggingPlugin,
    VisualizePlugin,
    PrettyPrintPlugin,
)

__version__ = "0.1.1"
__all__ = [
    "Model",
    "Query",
    "QueryPipeline",
    "QueryResult",
    "PipelineContext",
    "SQLCompiler",
    "CompiledQuery",
    "Manager",
    "QuerySet",
    "configure",
    "get_connection",
    "set_connection",
    "Connection",
    "Field",
    "IntegerField",
    "StringField",
    "Aggregate",
    "Avg",
    "Max",
    "Min",
    "Sum",
    "Count",
    "Plugin",
    "ExplainPlugin",
    "DryRunPlugin",
    "LoggingPlugin",
    "VisualizePlugin",
    "PrettyPrintPlugin",
    "DebugORM",
]


class DebugORM:
    """
    Optional facade for configuring a fixed plugin set across all models::

        orm = DebugORM(":memory:", plugins=[ExplainPlugin(), LoggingPlugin()])
        orm.install()   # applies the pipeline to every existing Model subclass
    """

    def __init__(
        self,
        db_path: str = ":memory:",
        plugins: list | None = None,
    ) -> None:
        self.connection = configure(db_path)
        self.plugins: list = plugins or []
        self._pipeline = QueryPipeline(plugins=self.plugins, connection=self.connection)

    def install(self) -> None:
        """Push the configured pipeline onto every ``Model`` subclass defined so far."""
        for subclass in self._all_subclasses(Model):
            if hasattr(subclass, "objects"):
                subclass.objects.pipeline = self._pipeline

    @staticmethod
    def _all_subclasses(base: type) -> list:
        result = []
        for cls in base.__subclasses__():
            result.append(cls)
            result.extend(DebugORM._all_subclasses(cls))
        return result

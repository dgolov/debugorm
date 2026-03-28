from __future__ import annotations
from typing import Any, Iterator, List, Optional, TYPE_CHECKING

from .query import Query, OrderByClause
from .pipeline import QueryPipeline

if TYPE_CHECKING:
    from .model import Model
    from ..plugins.base import Plugin


class DoesNotExist(Exception):
    pass


class MultipleObjectsReturned(Exception):
    pass


class QuerySet:
    """
    Lazy, chainable query builder.

    Every filtering or ordering call returns a *new* ``QuerySet`` — the
    original is never mutated.  The database is only hit when results are
    materialised via ``all()``, ``get()``, ``first()``, ``count()``, or
    direct iteration.
    """

    def __init__(
        self,
        model: type,
        pipeline: QueryPipeline,
        query: Optional[Query] = None,
    ) -> None:
        self._model = model
        self._pipeline = pipeline
        self._query = query if query is not None else Query(model)

    def filter(self, **kwargs: Any) -> "QuerySet":
        """Append WHERE conditions.  Multiple calls are AND-ed together."""
        new_query = self._query.copy()
        for lookup, value in kwargs.items():
            new_query.add_filter(lookup, value)
        return QuerySet(self._model, self._pipeline, new_query)

    def order_by(self, *fields: str) -> "QuerySet":
        """
        Order results.  Prefix a field name with ``-`` for descending order::

            User.objects.order_by('-age', 'name')
        """
        new_query = self._query.copy()
        for f in fields:
            descending = f.startswith("-")
            new_query.order_by_clauses.append(OrderByClause(f.lstrip("-"), descending))
        return QuerySet(self._model, self._pipeline, new_query)

    def limit(self, n: int) -> "QuerySet":
        new_query = self._query.copy()
        new_query.limit_value = n
        return QuerySet(self._model, self._pipeline, new_query)

    def offset(self, n: int) -> "QuerySet":
        new_query = self._query.copy()
        new_query.offset_value = n
        return QuerySet(self._model, self._pipeline, new_query)

    def all(self) -> List["Model"]:
        """Execute the query and return a list of model instances."""
        result = self._pipeline.run(self._query)
        return [self._model._from_row(row) for row in result.rows]

    def get(self, **kwargs: Any) -> "Model":
        """Return exactly one object; raise if zero or multiple match."""
        qs = self.filter(**kwargs) if kwargs else self
        results = qs.all()
        if not results:
            raise self._model.DoesNotExist(
                f"{self._model.__name__} matching query does not exist"
            )
        if len(results) > 1:
            raise self._model.MultipleObjectsReturned(
                f"get() returned more than one {self._model.__name__}"
            )
        return results[0]

    def first(self) -> Optional["Model"]:
        results = self.limit(1).all()
        return results[0] if results else None

    def count(self) -> int:
        count_query = self._query.copy()
        count_query.select_fields = ["COUNT(*) as count"]
        count_query.limit_value = None
        count_query.offset_value = None
        count_query.order_by_clauses = []
        result = self._pipeline.run(count_query)
        return result.rows[0]["count"] if result.rows else 0

    def exists(self) -> bool:
        return self.count() > 0

    def debug(
        self,
        explain: bool = False,
        dry_run: bool = False,
        log: bool = False,
        visualize: bool = False,
        pretty: bool = False,
    ) -> "QuerySet":
        """
        Attach debug plugins on the fly::

            User.objects.debug(explain=True, pretty=True).filter(age__gt=18).all()
        """
        extra: List["Plugin"] = []

        if visualize:
            from ..plugins.visualize import VisualizePlugin
            extra.append(VisualizePlugin())
        if log:
            from ..plugins.logging_plugin import LoggingPlugin
            extra.append(LoggingPlugin())
        if pretty:
            from ..plugins.pretty_print import PrettyPrintPlugin
            extra.append(PrettyPrintPlugin())
        if explain:
            from ..plugins.explain import ExplainPlugin
            extra.append(ExplainPlugin())
        if dry_run:
            from ..plugins.dry_run import DryRunPlugin
            extra.append(DryRunPlugin())

        return QuerySet(self._model, self._pipeline.with_plugins(extra), self._query.copy())

    def diff(self, other: "QuerySet") -> str:
        """
        Compare two ``QuerySet`` objects at the internal representation level::

            q1 = User.objects.filter(age__gt=18)
            q2 = User.objects.filter(age__gt=21)
            print(q1.diff(q2))
            # - age > 18
            # + age > 21
        """
        return self._query.diff(other._query)

    def __iter__(self) -> Iterator["Model"]:
        return iter(self.all())

    def __len__(self) -> int:
        return self.count()

    def __repr__(self) -> str:
        return f"QuerySet<{self._model.__name__}>"


class Manager:
    """
    Entry point for all database queries on a model.

    Attached to every ``Model`` subclass as ``Model.objects`` by ``ModelMeta``.
    """

    def __init__(self, model_class: type) -> None:
        self._model = model_class
        self._pipeline: Optional[QueryPipeline] = None

    @property
    def pipeline(self) -> QueryPipeline:
        if self._pipeline is None:
            self._pipeline = QueryPipeline()
        return self._pipeline

    @pipeline.setter
    def pipeline(self, value: QueryPipeline) -> None:
        self._pipeline = value

    def get_queryset(self) -> QuerySet:
        return QuerySet(self._model, self.pipeline)

    def filter(self, **kwargs: Any) -> QuerySet:
        return self.get_queryset().filter(**kwargs)

    def all(self) -> List["Model"]:
        return self.get_queryset().all()

    def get(self, **kwargs: Any) -> "Model":
        return self.get_queryset().get(**kwargs)

    def order_by(self, *fields: str) -> QuerySet:
        return self.get_queryset().order_by(*fields)

    def first(self) -> Optional["Model"]:
        return self.get_queryset().first()

    def count(self) -> int:
        return self.get_queryset().count()

    def create(self, **kwargs: Any) -> "Model":
        instance = self._model(**kwargs)
        instance.save()
        return instance

    def debug(self, **kwargs: Any) -> QuerySet:
        return self.get_queryset().debug(**kwargs)

from __future__ import annotations
from typing import Any, Dict, Iterator, List, Optional, TYPE_CHECKING

from .query import Query, OrderByClause
from .pipeline import QueryPipeline

if TYPE_CHECKING:
    from .model import Model
    from .aggregates import Aggregate
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
        self._return_mode: str = "model"

    def _clone(self, query: Optional[Query] = None, **overrides: Any) -> "QuerySet":
        """Return a shallow copy with optionally overridden attributes."""
        qs = QuerySet(self._model, self._pipeline, query)
        qs._return_mode = self._return_mode
        for key, val in overrides.items():
            setattr(qs, key, val)
        return qs

    def filter(self, **kwargs: Any) -> "QuerySet":
        """Append AND WHERE conditions.  Multiple calls are AND-ed together."""
        new_query = self._query.copy()
        for lookup, value in kwargs.items():
            new_query.add_filter(lookup, value)
        return self._clone(new_query)

    def or_filter(self, **kwargs: Any) -> "QuerySet":
        """
        Add a group of conditions OR-joined to the existing WHERE clause::

            User.objects.filter(age__gt=18).or_filter(name="Admin")
            # WHERE (age > 18) OR (name = 'Admin')

            User.objects.filter(active=True).or_filter(age__gt=18, role="admin")
            # WHERE (active = 1) OR (age > 18 AND role = 'admin')
        """
        new_query = self._query.copy()
        new_query.add_or_group(kwargs)
        return self._clone(new_query)

    def exclude(self, **kwargs: Any) -> "QuerySet":
        """
        Exclude rows that match the given conditions::

            User.objects.exclude(age__lt=18)
            # WHERE NOT (age < 18)
        """
        new_query = self._query.copy()
        new_query.add_exclude_group(kwargs)
        return self._clone(new_query)

    def order_by(self, *fields: str) -> "QuerySet":
        """
        Order results.  Prefix a field name with ``-`` for descending order::

            User.objects.order_by('-age', 'name')
        """
        new_query = self._query.copy()
        for f in fields:
            descending = f.startswith("-")
            new_query.order_by_clauses.append(OrderByClause(f.lstrip("-"), descending))
        return self._clone(new_query)

    def limit(self, n: int) -> "QuerySet":
        new_query = self._query.copy()
        new_query.limit_value = n
        return self._clone(new_query)

    def offset(self, n: int) -> "QuerySet":
        new_query = self._query.copy()
        new_query.offset_value = n
        return self._clone(new_query)

    def values(self, *fields: str) -> "QuerySet":
        """
        Return dicts instead of model instances.
        An optional field list restricts which columns are selected::

            User.objects.filter(age__gt=18).values("id", "name")
            # [{"id": 1, "name": "Alice"}, ...]
        """
        new_query = self._query.copy()
        if fields:
            new_query.select_fields = list(fields)
        return self._clone(new_query, _return_mode="dict")

    def values_list(self, *fields: str, flat: bool = False) -> "QuerySet":
        """
        Return tuples instead of model instances::

            User.objects.values_list("id", "name")
            # [(1, "Alice"), (2, "Bob"), ...]

            User.objects.values_list("name", flat=True)
            # ["Alice", "Bob", ...]
        """
        if flat and len(fields) != 1:
            raise ValueError("values_list(flat=True) requires exactly one field")
        new_query = self._query.copy()
        if fields:
            new_query.select_fields = list(fields)
        return self._clone(new_query, _return_mode="flat" if flat else "tuple")

    def all(self) -> List[Any]:
        """Execute the query and return results in the current return mode."""
        result = self._pipeline.run(self._query)

        if self._return_mode == "dict":
            return list(result.rows)
        elif self._return_mode == "tuple":
            return [tuple(row.values()) for row in result.rows]
        elif self._return_mode == "flat":
            return [next(iter(row.values())) for row in result.rows]

        return [self._model._from_row(row) for row in result.rows]

    def get(self, **kwargs: Any) -> Any:
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

    def first(self) -> Optional[Any]:
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

    def aggregate(self, **kwargs: "Aggregate") -> Dict[str, Any]:
        """
        Compute aggregate values over the current queryset::

            User.objects.filter(age__gt=18).aggregate(
                avg_age=Avg("age"),
                max_age=Max("age"),
                total=Count(),
            )
            # {"avg_age": 25.7, "max_age": 30, "total": 3}
        """
        agg_query = self._query.copy()
        agg_query.select_fields = []
        for alias, agg in kwargs.items():
            agg.alias = alias
            agg_query.select_fields.append(agg.as_sql_fragment())
        agg_query.limit_value = None
        agg_query.offset_value = None
        agg_query.order_by_clauses = []

        result = self._pipeline.run(agg_query)
        return dict(result.rows[0]) if result.rows else {k: None for k in kwargs}

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

        return self._clone(
            self._query.copy(),
            _pipeline=self._pipeline.with_plugins(extra),
        )

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

    def __iter__(self) -> Iterator[Any]:
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

    def or_filter(self, **kwargs: Any) -> QuerySet:
        return self.get_queryset().or_filter(**kwargs)

    def exclude(self, **kwargs: Any) -> QuerySet:
        return self.get_queryset().exclude(**kwargs)

    def all(self) -> List[Any]:
        return self.get_queryset().all()

    def get(self, **kwargs: Any) -> Any:
        return self.get_queryset().get(**kwargs)

    def order_by(self, *fields: str) -> QuerySet:
        return self.get_queryset().order_by(*fields)

    def first(self) -> Optional[Any]:
        return self.get_queryset().first()

    def count(self) -> int:
        return self.get_queryset().count()

    def aggregate(self, **kwargs: "Aggregate") -> Dict[str, Any]:
        return self.get_queryset().aggregate(**kwargs)

    def values(self, *fields: str) -> QuerySet:
        return self.get_queryset().values(*fields)

    def values_list(self, *fields: str, flat: bool = False) -> QuerySet:
        return self.get_queryset().values_list(*fields, flat=flat)

    def create(self, **kwargs: Any) -> Any:
        instance = self._model(**kwargs)
        instance.save()
        return instance

    def debug(self, **kwargs: Any) -> QuerySet:
        return self.get_queryset().debug(**kwargs)

from __future__ import annotations
from typing import Any, Dict, Optional, Tuple, TYPE_CHECKING

from ..fields.base import Field
from ..db.connection import get_connection

if TYPE_CHECKING:
    pass


class ModelMeta(type):
    """
    Metaclass that wires up fields, the table name, and the ``Manager``
    when a ``Model`` subclass is defined.
    """

    def __new__(
        mcs,
        name: str,
        bases: Tuple[type, ...],
        namespace: Dict[str, Any],
    ) -> "ModelMeta":
        fields: Dict[str, Field] = {}

        for base in bases:
            if hasattr(base, "_fields"):
                fields.update(base._fields)

        for attr_name, attr_val in list(namespace.items()):
            if isinstance(attr_val, Field):
                attr_val.name = attr_name
                fields[attr_name] = attr_val

        namespace["_fields"] = fields

        inner_meta = namespace.get("Meta")
        if inner_meta is not None and hasattr(inner_meta, "table_name"):
            namespace["_table_name"] = inner_meta.table_name
        else:
            namespace["_table_name"] = name.lower() + "s"

        cls = super().__new__(mcs, name, bases, namespace)

        if name != "Model":
            from .manager import Manager, DoesNotExist, MultipleObjectsReturned

            cls.objects = Manager(cls)
            cls.DoesNotExist = type("DoesNotExist", (DoesNotExist,), {})
            cls.MultipleObjectsReturned = type(
                "MultipleObjectsReturned", (MultipleObjectsReturned,), {}
            )

        return cls


class Model(metaclass=ModelMeta):
    """
    Base class for all DebugORM models::

        class User(Model):
            id   = IntegerField(primary_key=True)
            name = StringField()
            age  = IntegerField()
    """

    _fields: Dict[str, Field] = {}
    _table_name: str = ""

    def __init__(self, **kwargs: Any) -> None:
        for field_name, field_obj in self._fields.items():
            value = kwargs.get(field_name, field_obj.default)
            object.__setattr__(self, field_name, value)
        for key, value in kwargs.items():
            if key not in self._fields:
                object.__setattr__(self, key, value)

    @classmethod
    def _from_row(cls, row: Dict[str, Any]) -> "Model":
        """Reconstruct a model instance from a raw DB row dict."""
        instance = cls.__new__(cls)
        for field_name, field_obj in cls._fields.items():
            object.__setattr__(instance, field_name, field_obj.from_db(row.get(field_name)))
        return instance

    def _pk_info(self) -> Tuple[Optional[str], Optional[Field]]:
        for name, f in self._fields.items():
            if f.primary_key:
                return name, f
        return None, None

    def _pk_value(self) -> Any:
        pk_name, _ = self._pk_info()
        return getattr(self, pk_name, None) if pk_name else None

    def save(self) -> None:
        """INSERT if this is a new instance, UPDATE if it already has a PK."""
        from .query import Query
        from .pipeline import QueryPipeline

        pk_name, _ = self._pk_info()
        pk_val = self._pk_value()

        data: Dict[str, Any] = {}
        for field_name, field_obj in self._fields.items():
            value = getattr(self, field_name, None)
            field_obj.validate(value)
            if field_obj.primary_key and pk_val is None:
                continue
            data[field_name] = field_obj.to_db(value)

        pipeline = QueryPipeline(connection=get_connection())

        if pk_val is None:
            query = Query(self.__class__)
            query.query_type = "INSERT"
            query.data = data
            result = pipeline.run(query)
            if pk_name and result.last_insert_id is not None:
                object.__setattr__(self, pk_name, result.last_insert_id)
        else:
            query = Query(self.__class__)
            query.query_type = "UPDATE"
            query.data = data
            query.pk_value = pk_val
            pipeline.run(query)

    def delete(self) -> None:
        """Delete this instance from the database and clear its primary key."""
        from .query import Query
        from .pipeline import QueryPipeline

        pk_name, _ = self._pk_info()
        pk_val = self._pk_value()

        if pk_val is None:
            raise ValueError(
                f"Cannot delete an unsaved {self.__class__.__name__} instance"
            )

        query = Query(self.__class__)
        query.query_type = "DELETE"
        query.pk_value = pk_val
        QueryPipeline(connection=get_connection()).run(query)

        if pk_name:
            object.__setattr__(self, pk_name, None)

    @classmethod
    def create_table(cls) -> None:
        """Execute ``CREATE TABLE IF NOT EXISTS`` for this model."""
        col_defs = []
        for field_name, field_obj in cls._fields.items():
            col_def = f"{field_name} {field_obj.get_sql_type()}"
            if field_obj.primary_key:
                col_def += " PRIMARY KEY AUTOINCREMENT"
            elif not field_obj.null:
                col_def += " NOT NULL"
            col_defs.append(col_def)
        get_connection().create_table(cls._table_name, ", ".join(col_defs))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return NotImplemented
        pk_name, _ = self._pk_info()
        if pk_name:
            return getattr(self, pk_name) == getattr(other, pk_name)
        return False

    def __repr__(self) -> str:
        attrs = ", ".join(
            f"{k}={getattr(self, k, None)!r}" for k in self._fields
        )
        return f"{self.__class__.__name__}({attrs})"

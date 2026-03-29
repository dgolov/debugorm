# DebugORM

A minimal, plugin-driven ORM for SQLite whose primary goal is **helping developers understand and debug SQL queries**, not just execute them.

---

## Architecture

```
Model → QuerySet → Query → Pipeline → [Plugins] → SQLCompiler → Executor → Result
```

### Key objects

| Object | Responsibility |
|---|---|
| `Field` | Declares a column; validates and converts values |
| `Model` | Base class; provides `save()`, `delete()`, `create_table()` |
| `Manager` | Attached as `Model.objects`; creates QuerySets |
| `QuerySet` | Chainable, lazy query builder |
| `Query` | **Structured, SQL-free** representation of a query (the internal AST) |
| `SQLCompiler` | Translates `Query` → `(sql, params)` |
| `QueryPipeline` | Orchestrates the full lifecycle and calls plugin hooks |
| `Plugin` | Base class for all debug extensions |

### Plugin hook order

```
before_compile(query, ctx)
    ↓
SQLCompiler.compile(query) → CompiledQuery
    ↓
after_compile(compiled, ctx)
    ↓
before_execute(compiled, ctx)   ← return QueryResult here to skip execution
    ↓
QueryExecutor.execute(compiled) → QueryResult
    ↓
after_execute(result, ctx)
```

---

## Quick start

```python
from debugorm import configure, Model
from debugorm.fields import IntegerField, StringField

configure(":memory:")       # or a file path: "myapp.db"

class User(Model):
    id   = IntegerField(primary_key=True)
    name = StringField(max_length=100)
    age  = IntegerField()

User.create_table()
```

### CRUD

```python
# Create
alice = User(name="Alice", age=25)
alice.save()                        # INSERT

alice.age = 26
alice.save()                        # UPDATE

alice.delete()                      # DELETE

# Read
User.objects.all()
User.objects.filter(age__gte=18).order_by("-age").all()
User.objects.get(name="Bob")
User.objects.filter(age__gt=20).count()
User.objects.order_by("-age").first()

# OR conditions
User.objects.filter(name="Alice").or_filter(name="Bob").all()
# WHERE (name = 'Alice') OR (name = 'Bob')

# Multiple conditions per OR group
User.objects.filter(age__gt=28).or_filter(age__lt=18, name="Bob").all()
# WHERE (age > 28) OR (age < 18 AND name = 'Bob')

# Exclude
User.objects.exclude(age__lt=18).all()
# WHERE NOT (age < 18)

User.objects.exclude(age__lt=18).exclude(name="Admin").all()
# WHERE NOT (age < 18) AND NOT (name = 'Admin')

# Aggregations
from debugorm import Avg, Max, Min, Sum, Count

User.objects.aggregate(avg_age=Avg("age"), max_age=Max("age"), total=Count())
# {"avg_age": 25.0, "max_age": 30, "total": 4}

User.objects.filter(age__gte=18).aggregate(avg_age=Avg("age"))
# {"avg_age": 25.7}

# values() — return dicts
User.objects.filter(age__gt=18).values("id", "name").all()
# [{"id": 1, "name": "Alice"}, ...]

# values_list() — return tuples
User.objects.values_list("id", "name").all()
# [(1, "Alice"), (2, "Bob"), ...]

User.objects.values_list("name", flat=True).all()
# ["Alice", "Bob", ...]
```

### Supported lookup operators

| Suffix | SQL |
|---|---|
| `age__eq=18` or `age=18` | `age = 18` |
| `age__ne=18` | `age != 18` |
| `age__gt=18` | `age > 18` |
| `age__gte=18` | `age >= 18` |
| `age__lt=18` | `age < 18` |
| `age__lte=18` | `age <= 18` |
| `name__like="A%"` | `name LIKE 'A%'` |
| `name__in=["Alice","Bob"]` | `name IN ('Alice', 'Bob')` |
| `name__isnull=True` | `name IS NULL` |

---

## Debug plugins

Attach plugins on the fly with `.debug()`:

```python
User.objects.debug(
    explain=True,       # EXPLAIN QUERY PLAN
    dry_run=True,       # show SQL without executing
    log=True,           # log SQL + timing via Python logging
    visualize=True,     # print query tree
    pretty=True,        # pretty-format SQL
).filter(age__gt=18).all()
```

### ExplainPlugin

Runs `EXPLAIN QUERY PLAN` after query execution and prints how SQLite plans to process it.

```
╔────────────────────────────────────────────────────────────╗
║  [ExplainPlugin]
╠────────────────────────────────────────────────────────────╣
║  SQL  : SELECT * FROM users WHERE age > ? ORDER BY age DESC
╠────────────────────────────────────────────────────────────╣
║  QUERY PLAN
║    └── SCAN users
║    └── USE TEMP B-TREE FOR ORDER BY
╚────────────────────────────────────────────────────────────╝
```

### DryRunPlugin

Prevents execution; estimates how many rows would be affected.

```
╔────────────────────────────────────────────────────────────╗
║  [DryRunPlugin]  ⚠  NOT EXECUTED
╠────────────────────────────────────────────────────────────╣
║  SQL   : SELECT * FROM users WHERE age >= ? ORDER BY name ASC
║  Interpolated: SELECT * FROM users WHERE age >= 18 ORDER BY name ASC
╠────────────────────────────────────────────────────────────╣
║  Estimated rows affected: ~3
╚────────────────────────────────────────────────────────────╝
```

### LoggingPlugin

Uses Python's `logging` module — integrates with any existing log config.

```
DEBUG  debugorm.sql › SQL ▶ SELECT * FROM users WHERE age > ?  params=(20,)
DEBUG  debugorm.sql › SQL ◀ rows=3  time=0.12ms
```

### VisualizePlugin

Renders the query as a tree **before** compilation (shows intent, not SQL).

```
╔────────────────────────────────────────────────────────────╗
║  [VisualizePlugin]  Query Structure
╠────────────────────────────────────────────────────────────╣
║  User (SELECT)
║   ├── filter: age > 18
║   ├── filter: name LIKE 'A%'
║   ├── order_by: name ASC
║   └── limit: 10
╚────────────────────────────────────────────────────────────╝
```

Pass `show_json=True` to also get the JSON representation.

### PrettyPrintPlugin

Formats the compiled SQL for human readability.

```
SELECT *
  FROM users
  WHERE age >= ?
  ORDER BY age DESC
  LIMIT ?
```

---

## Query Diff

Compare two queries at the **internal representation level** (not string comparison):

```python
q1 = User.objects.filter(age__gt=18)
q2 = User.objects.filter(age__gt=21)

print(q1.diff(q2))
# - age > 18
# + age > 21

q3 = User.objects.filter(age__gte=18).order_by("-age").limit(10)
q4 = User.objects.filter(age__gte=18).order_by("name").limit(5)

print(q3.diff(q4))
# - ORDER BY age DESC
# + ORDER BY name ASC
# - LIMIT 10
# + LIMIT 5

print(q1.diff(q1))
# Queries are identical
```

---

## Global plugin configuration via DebugORM facade

```python
from debugorm import DebugORM, LoggingPlugin, PrettyPrintPlugin

orm = DebugORM(":memory:", plugins=[LoggingPlugin(), PrettyPrintPlugin()])
orm.install()   # applies the pipeline to every already-defined model
```

---

## Project structure

```
debugorm/
├── __init__.py          public API
├── core/
│   ├── model.py         Model base class + ModelMeta
│   ├── query.py         Query AST + FilterCondition + Query.diff()
│   ├── compiler.py      SQLCompiler → CompiledQuery
│   ├── pipeline.py      QueryPipeline + QueryExecutor + QueryResult
│   └── manager.py       Manager + QuerySet
├── fields/
│   ├── base.py
│   ├── integer.py
│   └── string.py
├── plugins/
│   ├── base.py          Plugin base class + hook signatures
│   ├── explain.py       ExplainPlugin
│   ├── dry_run.py       DryRunPlugin
│   ├── logging_plugin.py LoggingPlugin
│   ├── visualize.py     VisualizePlugin
│   └── pretty_print.py  PrettyPrintPlugin
└── db/
    └── connection.py    Connection + configure()
demo.py                  end-to-end usage example
```

---

## Writing a custom plugin

```python
from debugorm.plugins.base import Plugin

class TimingPlugin(Plugin):
    name = "timing"

    def before_execute(self, compiled, ctx):
        import time
        ctx.extra["t0"] = time.perf_counter()
        return None   # don't intercept

    def after_execute(self, result, ctx):
        elapsed = (time.perf_counter() - ctx.extra["t0"]) * 1000
        print(f"[TimingPlugin] {elapsed:.1f}ms — {result.rowcount} rows")


# Use it:
User.objects.debug().filter(age__gt=18)   # ... or
from debugorm import QueryPipeline
User.objects.pipeline = QueryPipeline(plugins=[TimingPlugin()])
```

---

## Requirements

- Python 3.10+
- No external dependencies (standard library only: `sqlite3`, `logging`, `dataclasses`, `copy`, `re`, `time`, `json`)

"""
demo.py — demonstrates all major DebugORM features.

Run with:
    python demo.py
"""

import logging

# ── Setup logging so LoggingPlugin output is visible ──────────────────────────
logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)-8s %(name)s › %(message)s",
)

# ── 1. Configure ORM ──────────────────────────────────────────────────────────
from debugorm import (
    configure,
    Model,
    IntegerField,
    StringField,
    ExplainPlugin,
    DryRunPlugin,
    LoggingPlugin,
    VisualizePlugin,
    PrettyPrintPlugin,
)

configure(":memory:")   # use in-memory SQLite database


# ── 2. Define models ──────────────────────────────────────────────────────────
class User(Model):
    id    = IntegerField(primary_key=True)
    name  = StringField(max_length=100)
    age   = IntegerField()


class Post(Model):
    id      = IntegerField(primary_key=True)
    title   = StringField(max_length=200)
    user_id = IntegerField()
    views   = IntegerField(null=True)


User.create_table()
Post.create_table()

print("\n" + "═" * 70)
print("  DebugORM — Demo")
print("═" * 70)


# ── 3. CRUD ───────────────────────────────────────────────────────────────────
print("\n▶  [1] INSERT via save()")
users_data = [
    ("Alice",   25),
    ("Bob",     17),
    ("Charlie", 30),
    ("Diana",   22),
    ("Eve",     15),
]
for name, age in users_data:
    u = User(name=name, age=age)
    u.save()
    print(f"   Saved: {u}")

print("\n▶  [2] UPDATE")
alice = User.objects.get(name="Alice")
alice.age = 26
alice.save()
print(f"   Updated: {alice}")

print("\n▶  [3] DELETE")
eve = User.objects.get(name="Eve")
eve.delete()
print(f"   Deleted Eve (id is now {eve.id})")


# ── 4. Queries ────────────────────────────────────────────────────────────────
print("\n▶  [4] filter + order_by + all()")
adults = User.objects.filter(age__gte=18).order_by("-age").all()
print(f"   Adults (sorted by age desc): {adults}")

print("\n▶  [5] count()")
print(f"   Total users: {User.objects.count()}")
print(f"   Users age >= 18: {User.objects.filter(age__gte=18).count()}")

print("\n▶  [6] first()")
oldest = User.objects.order_by("-age").first()
print(f"   Oldest user: {oldest}")

print("\n▶  [7] get() — exact match")
bob = User.objects.get(name="Bob")
print(f"   Found: {bob}")


# ── 5. PrettyPrintPlugin ──────────────────────────────────────────────────────
print("\n▶  [8] PrettyPrintPlugin — formatted SQL output")
(
    User.objects
    .debug(pretty=True)
    .filter(age__gte=18)
    .order_by("-age")
    .limit(3)
    .all()
)


# ── 6. VisualizePlugin ────────────────────────────────────────────────────────
print("\n▶  [9] VisualizePlugin — query tree + JSON")
(
    User.objects
    .debug(visualize=True)
    .filter(age__gt=18, name__like="A%")
    .order_by("name")
    .limit(10)
    .all()
)


# ── 7. ExplainPlugin ──────────────────────────────────────────────────────────
print("\n▶  [10] ExplainPlugin — EXPLAIN QUERY PLAN")
(
    User.objects
    .debug(explain=True)
    .filter(age__gt=18)
    .order_by("-age")
    .all()
)


# ── 8. DryRunPlugin ───────────────────────────────────────────────────────────
print("\n▶  [11] DryRunPlugin — see SQL without executing")
(
    User.objects
    .debug(dry_run=True)
    .filter(age__gte=18)
    .order_by("name")
    .all()
)

# DryRun on an INSERT
print("   (DryRun INSERT)")
dry_qs = User.objects.debug(dry_run=True)
# Manually trigger to show INSERT dry-run:
from debugorm.core.query import Query
from debugorm.core.pipeline import QueryPipeline
from debugorm import get_connection
_q = Query(User)
_q.query_type = "INSERT"
_q.data = {"name": "Fake", "age": 99}
QueryPipeline(plugins=[DryRunPlugin()], connection=get_connection()).run(_q)


# ── 9. LoggingPlugin ──────────────────────────────────────────────────────────
print("\n▶  [12] LoggingPlugin — SQL + timing via Python logging")
(
    User.objects
    .debug(log=True)
    .filter(age__gt=20)
    .all()
)


# ── 10. Combined plugins ──────────────────────────────────────────────────────
print("\n▶  [13] Combined: visualize + pretty + explain")
(
    User.objects
    .debug(visualize=True, pretty=True, explain=True)
    .filter(age__gt=18)
    .limit(5)
    .all()
)


# ── 11. Query Diff ────────────────────────────────────────────────────────────
print("\n▶  [14] Query Diff — compare two queries")
q1 = User.objects.filter(age__gt=18)
q2 = User.objects.filter(age__gt=21)
diff = q1.diff(q2)
print(f"   diff(q1, q2):\n{chr(10).join('   ' + l for l in diff.splitlines())}")

q3 = User.objects.filter(age__gte=18).order_by("-age").limit(10)
q4 = User.objects.filter(age__gte=18).order_by("name").limit(5)
diff2 = q3.diff(q4)
print(f"\n   diff(q3, q4):\n{chr(10).join('   ' + l for l in diff2.splitlines())}")

q5 = User.objects.filter(age__gt=18)
diff3 = q5.diff(q5)
print(f"\n   diff(q5, q5): {diff3}")


# ── 12. DebugORM facade ───────────────────────────────────────────────────────
print("\n▶  [15] DebugORM facade — global plugin configuration")
from debugorm import DebugORM

# Spin up a second in-memory DB with logging enabled everywhere
class Product(Model):
    id    = IntegerField(primary_key=True)
    name  = StringField()
    price = IntegerField()

orm = DebugORM(":memory:", plugins=[LoggingPlugin(), PrettyPrintPlugin()])
orm.install()

Product.create_table()
Product(name="Widget", price=9).save()
Product(name="Gadget", price=42).save()
products = Product.objects.filter(price__gt=5).all()
print(f"   Products: {products}")

print("\n" + "═" * 70)
print("  Demo complete.")
print("═" * 70 + "\n")

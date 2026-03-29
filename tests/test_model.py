import pytest
from debugorm import Avg, Max, Min, Sum, Count


class TestCRUD:
    def test_save_insert(self, User):
        u = User(name="Alice", age=25)
        u.save()
        assert u.id is not None

    def test_save_update(self, User):
        u = User(name="Alice", age=25)
        u.save()
        original_id = u.id
        u.age = 26
        u.save()
        assert u.id == original_id
        fetched = User.objects.get(id=original_id)
        assert fetched.age == 26

    def test_delete(self, populated_db):
        User = populated_db
        alice = User.objects.get(name="Alice")
        alice.delete()
        assert alice.id is None
        assert User.objects.filter(name="Alice").count() == 0

    def test_delete_unsaved_raises(self, User):
        u = User(name="Ghost", age=0)
        with pytest.raises(ValueError):
            u.delete()

    def test_repr(self, User):
        u = User(name="Alice", age=25)
        assert "Alice" in repr(u)
        assert "25" in repr(u)


class TestQuerySet:
    def test_all(self, populated_db):
        User = populated_db
        assert len(User.objects.all()) == 4

    def test_filter(self, populated_db):
        User = populated_db
        adults = User.objects.filter(age__gte=18).all()
        assert all(u.age >= 18 for u in adults)

    def test_filter_chaining(self, populated_db):
        User = populated_db
        result = User.objects.filter(age__gte=18).filter(age__lt=30).all()
        assert all(18 <= u.age < 30 for u in result)

    def test_get_exact(self, populated_db):
        User = populated_db
        assert User.objects.get(name="Bob").name == "Bob"

    def test_get_does_not_exist(self, populated_db):
        User = populated_db
        with pytest.raises(User.DoesNotExist):
            User.objects.get(name="NoOne")

    def test_get_multiple_raises(self, User):
        User(name="A", age=20).save()
        User(name="A", age=21).save()
        with pytest.raises(User.MultipleObjectsReturned):
            User.objects.get(name="A")

    def test_order_by_asc(self, populated_db):
        User = populated_db
        ages = [u.age for u in User.objects.order_by("age").all()]
        assert ages == sorted(ages)

    def test_order_by_desc(self, populated_db):
        User = populated_db
        ages = [u.age for u in User.objects.order_by("-age").all()]
        assert ages == sorted(ages, reverse=True)

    def test_limit(self, populated_db):
        User = populated_db
        assert len(User.objects.order_by("id").limit(2).all()) == 2

    def test_offset(self, populated_db):
        User = populated_db
        all_users = User.objects.order_by("id").all()
        offset_users = User.objects.order_by("id").offset(2).all()
        assert offset_users[0].id == all_users[2].id

    def test_count(self, populated_db):
        User = populated_db
        assert User.objects.count() == 4
        assert User.objects.filter(age__gte=18).count() == 3

    def test_first(self, populated_db):
        User = populated_db
        oldest = User.objects.order_by("-age").first()
        assert oldest.age == max(u.age for u in User.objects.all())

    def test_first_returns_none_on_empty(self, User):
        assert User.objects.first() is None

    def test_exists_true(self, populated_db):
        User = populated_db
        assert User.objects.filter(age__gt=10).exists() is True

    def test_exists_false(self, populated_db):
        User = populated_db
        assert User.objects.filter(age__gt=999).exists() is False

    def test_iteration(self, populated_db):
        User = populated_db
        assert len(list(User.objects.all())) == 4

    def test_len(self, populated_db):
        User = populated_db
        assert len(User.objects.filter(age__gte=18)) == 3

    def test_create(self, User):
        u = User.objects.create(name="New", age=99)
        assert u.id is not None
        assert User.objects.count() == 1


class TestOrFilter:
    def test_simple_or(self, populated_db):
        User = populated_db
        result = User.objects.filter(name="Alice").or_filter(name="Bob").all()
        names = {u.name for u in result}
        assert names == {"Alice", "Bob"}

    def test_or_returns_all_matching(self, populated_db):
        User = populated_db
        result = User.objects.filter(age__gt=28).or_filter(age__lt=18).all()
        assert all(u.age > 28 or u.age < 18 for u in result)

    def test_multiple_or_groups(self, populated_db):
        User = populated_db
        result = (
            User.objects
            .filter(name="Alice")
            .or_filter(name="Bob")
            .or_filter(name="Charlie")
            .all()
        )
        assert len(result) == 3

    def test_or_filter_without_main_filter(self, populated_db):
        User = populated_db
        result = User.objects.or_filter(name="Alice").or_filter(name="Bob").all()
        assert len(result) == 2

    def test_or_filter_combined_conditions(self, populated_db):
        User = populated_db
        # (age > 28 AND name = 'Charlie') OR (age < 18 AND name = 'Bob')
        result = (
            User.objects
            .filter(age__gt=28, name="Charlie")
            .or_filter(age__lt=18, name="Bob")
            .all()
        )
        names = {u.name for u in result}
        assert "Charlie" in names
        assert "Bob" in names


class TestExclude:
    def test_simple_exclude(self, populated_db):
        User = populated_db
        result = User.objects.exclude(age__lt=18).all()
        assert all(u.age >= 18 for u in result)

    def test_exclude_multiple(self, populated_db):
        User = populated_db
        result = User.objects.exclude(name="Alice").exclude(name="Bob").all()
        names = {u.name for u in result}
        assert "Alice" not in names
        assert "Bob" not in names

    def test_filter_and_exclude(self, populated_db):
        User = populated_db
        result = User.objects.filter(age__gte=18).exclude(name="Alice").all()
        assert all(u.age >= 18 for u in result)
        assert all(u.name != "Alice" for u in result)


class TestAggregate:
    def test_avg(self, populated_db):
        User = populated_db
        result = User.objects.aggregate(avg_age=Avg("age"))
        assert "avg_age" in result
        assert isinstance(result["avg_age"], float)

    def test_max(self, populated_db):
        User = populated_db
        result = User.objects.aggregate(max_age=Max("age"))
        assert result["max_age"] == max(u.age for u in User.objects.all())

    def test_min(self, populated_db):
        User = populated_db
        result = User.objects.aggregate(min_age=Min("age"))
        assert result["min_age"] == min(u.age for u in User.objects.all())

    def test_sum(self, populated_db):
        User = populated_db
        result = User.objects.aggregate(total_age=Sum("age"))
        expected = sum(u.age for u in User.objects.all())
        assert result["total_age"] == expected

    def test_count(self, populated_db):
        User = populated_db
        result = User.objects.aggregate(total=Count())
        assert result["total"] == 4

    def test_multiple_aggregates(self, populated_db):
        User = populated_db
        result = User.objects.aggregate(
            avg_age=Avg("age"),
            max_age=Max("age"),
            total=Count(),
        )
        assert set(result.keys()) == {"avg_age", "max_age", "total"}

    def test_aggregate_with_filter(self, populated_db):
        User = populated_db
        result = User.objects.filter(age__gte=18).aggregate(total=Count())
        assert result["total"] == 3

    def test_aggregate_empty_result(self, User):
        result = User.objects.filter(age__gt=999).aggregate(avg_age=Avg("age"))
        assert result["avg_age"] is None


class TestValues:
    def test_values_returns_dicts(self, populated_db):
        User = populated_db
        result = User.objects.values("name", "age").all()
        assert all(isinstance(r, dict) for r in result)

    def test_values_selected_fields_only(self, populated_db):
        User = populated_db
        result = User.objects.values("name").all()
        assert all(set(r.keys()) == {"name"} for r in result)

    def test_values_no_fields_returns_all(self, populated_db):
        User = populated_db
        result = User.objects.values().all()
        assert all(isinstance(r, dict) for r in result)
        assert all("name" in r and "age" in r for r in result)

    def test_values_with_filter(self, populated_db):
        User = populated_db
        result = User.objects.filter(age__gte=18).values("name").all()
        assert len(result) == 3

    def test_values_with_order_by(self, populated_db):
        User = populated_db
        result = User.objects.values("name", "age").order_by("age").all()
        ages = [r["age"] for r in result]
        assert ages == sorted(ages)

    def test_values_preserves_mode_after_filter(self, populated_db):
        User = populated_db
        qs = User.objects.values("name")
        result = qs.filter(age__gte=18).all()
        assert all(isinstance(r, dict) for r in result)


class TestValuesList:
    def test_values_list_returns_tuples(self, populated_db):
        User = populated_db
        result = User.objects.values_list("name", "age").all()
        assert all(isinstance(r, tuple) for r in result)
        assert all(len(r) == 2 for r in result)

    def test_values_list_flat(self, populated_db):
        User = populated_db
        result = User.objects.values_list("name", flat=True).all()
        assert all(isinstance(r, str) for r in result)

    def test_values_list_flat_requires_one_field(self, User):
        with pytest.raises(ValueError):
            User.objects.values_list("name", "age", flat=True)

    def test_values_list_with_order_by(self, populated_db):
        User = populated_db
        names = User.objects.order_by("name").values_list("name", flat=True).all()
        assert names == sorted(names)


class TestQuerySetImmutability:
    def test_filter_does_not_mutate_original(self, populated_db):
        User = populated_db
        base = User.objects.filter(age__gte=18)
        _ = base.filter(age__lt=25)
        assert base.count() == 3

    def test_or_filter_does_not_mutate_original(self, populated_db):
        User = populated_db
        base = User.objects.filter(name="Alice")
        _ = base.or_filter(name="Bob")
        assert base.count() == 1


class TestQueryDiff:
    def test_value_change(self, User):
        q1 = User.objects.filter(age__gt=18)
        q2 = User.objects.filter(age__gt=21)
        diff = q1.diff(q2)
        assert "- age > 18" in diff
        assert "+ age > 21" in diff

    def test_identical(self, User):
        q = User.objects.filter(age__gt=18)
        assert q.diff(q) == "Queries are identical"

    def test_or_group_in_diff(self, User):
        q1 = User.objects.filter(age__gt=18).or_filter(name="Alice")
        q2 = User.objects.filter(age__gt=18).or_filter(name="Bob")
        diff = q1.diff(q2)
        assert "OR:" in diff

    def test_exclude_in_diff(self, User):
        q1 = User.objects.exclude(age__lt=18)
        q2 = User.objects.exclude(age__lt=21)
        diff = q1.diff(q2)
        assert "NOT:" in diff

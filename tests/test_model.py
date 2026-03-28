import pytest


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
        users = User.objects.all()
        assert len(users) == 4

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
        user = User.objects.get(name="Bob")
        assert user.name == "Bob"

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
        users = User.objects.order_by("age").all()
        ages = [u.age for u in users]
        assert ages == sorted(ages)

    def test_order_by_desc(self, populated_db):
        User = populated_db
        users = User.objects.order_by("-age").all()
        ages = [u.age for u in users]
        assert ages == sorted(ages, reverse=True)

    def test_limit(self, populated_db):
        User = populated_db
        users = User.objects.order_by("id").limit(2).all()
        assert len(users) == 2

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
        user = User.objects.order_by("age").first()
        assert user.age == min(u.age for u in User.objects.all())

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
        users = list(User.objects.all())
        assert len(users) == 4

    def test_len(self, populated_db):
        User = populated_db
        assert len(User.objects.filter(age__gte=18)) == 3

    def test_create(self, User):
        u = User.objects.create(name="New", age=99)
        assert u.id is not None
        assert User.objects.count() == 1


class TestQuerySetImmutability:
    def test_filter_does_not_mutate_original(self, populated_db):
        User = populated_db
        base = User.objects.filter(age__gte=18)
        _ = base.filter(age__lt=25)
        assert base.count() == 3


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

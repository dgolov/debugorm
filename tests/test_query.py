import pytest
from debugorm import Model
from debugorm.fields import IntegerField, StringField
from debugorm.core.query import Query, FilterCondition, OrderByClause


class DummyModel(Model):
    id  = IntegerField(primary_key=True)
    age = IntegerField()

    class Meta:
        table_name = "dummy"


class TestFilterCondition:
    def test_str_with_value(self):
        cond = FilterCondition("age", ">", 18)
        assert str(cond) == "age > 18"

    def test_str_is_null(self):
        cond = FilterCondition("age", "IS NULL", None)
        assert str(cond) == "age IS NULL"

    def test_identity_key(self):
        cond = FilterCondition("age", ">", 18)
        assert cond.identity_key() == "age__>"


class TestQuery:
    def setup_method(self):
        self.q = Query(DummyModel)

    def test_default_type_is_select(self):
        assert self.q.query_type == "SELECT"

    def test_add_filter_gt(self):
        self.q.add_filter("age__gt", 18)
        assert len(self.q.conditions) == 1
        assert self.q.conditions[0].operator == ">"
        assert self.q.conditions[0].value == 18

    def test_add_filter_default_eq(self):
        self.q.add_filter("age", 5)
        assert self.q.conditions[0].operator == "="

    def test_add_filter_isnull_true(self):
        self.q.add_filter("age__isnull", True)
        assert self.q.conditions[0].operator == "IS NULL"
        assert self.q.conditions[0].value is None

    def test_add_filter_isnull_false(self):
        self.q.add_filter("age__isnull", False)
        assert self.q.conditions[0].operator == "IS NOT NULL"

    def test_add_filter_unknown_operator(self):
        with pytest.raises(ValueError, match="Unknown lookup operator"):
            self.q.add_filter("age__wtf", 1)

    def test_copy_is_independent(self):
        self.q.add_filter("age__gt", 18)
        copy = self.q.copy()
        copy.add_filter("age__lt", 99)
        assert len(self.q.conditions) == 1
        assert len(copy.conditions) == 2


class TestQueryDiff:
    def setup_method(self):
        self.q1 = Query(DummyModel)
        self.q2 = Query(DummyModel)

    def test_identical_queries(self):
        self.q1.add_filter("age__gt", 18)
        self.q2.add_filter("age__gt", 18)
        assert self.q1.diff(self.q2) == "Queries are identical"

    def test_value_change(self):
        self.q1.add_filter("age__gt", 18)
        self.q2.add_filter("age__gt", 21)
        diff = self.q1.diff(self.q2)
        assert "- age > 18" in diff
        assert "+ age > 21" in diff

    def test_added_condition(self):
        self.q2.add_filter("age__gt", 18)
        diff = self.q1.diff(self.q2)
        assert "+ age > 18" in diff

    def test_removed_condition(self):
        self.q1.add_filter("age__gt", 18)
        diff = self.q1.diff(self.q2)
        assert "- age > 18" in diff

    def test_limit_diff(self):
        self.q1.limit_value = 10
        self.q2.limit_value = 5
        diff = self.q1.diff(self.q2)
        assert "- LIMIT 10" in diff
        assert "+ LIMIT 5" in diff

    def test_order_by_diff(self):
        self.q1.order_by_clauses = [OrderByClause("age", descending=True)]
        self.q2.order_by_clauses = [OrderByClause("age", descending=False)]
        diff = self.q1.diff(self.q2)
        assert "- ORDER BY age DESC" in diff
        assert "+ ORDER BY age ASC" in diff

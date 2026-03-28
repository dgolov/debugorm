import pytest
from debugorm.fields import IntegerField, StringField


class TestIntegerField:
    def test_get_sql_type(self):
        assert IntegerField().get_sql_type() == "INTEGER"

    def test_to_db_converts_value(self):
        f = IntegerField()
        f.name = "age"
        assert f.to_db(42) == 42
        assert f.to_db(None) is None

    def test_from_db_converts_value(self):
        f = IntegerField()
        f.name = "age"
        assert f.from_db("7") == 7
        assert f.from_db(None) is None

    def test_validate_rejects_non_int(self):
        f = IntegerField(null=True)
        f.name = "age"
        with pytest.raises(TypeError):
            f.validate("not-an-int")

    def test_validate_allows_null_when_permitted(self):
        f = IntegerField(null=True)
        f.name = "age"
        f.validate(None)  # should not raise

    def test_validate_rejects_null_by_default(self):
        f = IntegerField()
        f.name = "age"
        with pytest.raises(ValueError):
            f.validate(None)


class TestStringField:
    def test_get_sql_type(self):
        assert StringField().get_sql_type() == "TEXT"

    def test_to_db_and_from_db(self):
        f = StringField()
        f.name = "name"
        assert f.to_db("hello") == "hello"
        assert f.from_db("hello") == "hello"
        assert f.to_db(None) is None

    def test_max_length_enforced(self):
        f = StringField(max_length=5)
        f.name = "name"
        with pytest.raises(ValueError):
            f.validate("toolong")

    def test_max_length_accepts_exact(self):
        f = StringField(max_length=5)
        f.name = "name"
        f.validate("hello")  # should not raise

    def test_validate_rejects_non_str(self):
        f = StringField(null=True)
        f.name = "name"
        with pytest.raises(TypeError):
            f.validate(123)

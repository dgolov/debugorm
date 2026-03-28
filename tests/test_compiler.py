import pytest
from debugorm import configure, Model
from debugorm.fields import IntegerField, StringField
from debugorm.core.query import Query
from debugorm.core.compiler import SQLCompiler


class Article(Model):
    id    = IntegerField(primary_key=True)
    title = StringField()
    views = IntegerField(null=True)

    class Meta:
        table_name = "articles"


@pytest.fixture(autouse=True)
def db():
    configure(":memory:")


class TestSelectCompilation:
    def test_select_all(self):
        q = Query(Article)
        compiled = SQLCompiler().compile(q)
        assert compiled.sql == "SELECT * FROM articles"
        assert compiled.params == ()

    def test_select_with_filter(self):
        q = Query(Article)
        q.add_filter("views__gt", 100)
        compiled = SQLCompiler().compile(q)
        assert "WHERE views > ?" in compiled.sql
        assert compiled.params == (100,)

    def test_select_multiple_filters(self):
        q = Query(Article)
        q.add_filter("views__gt", 100)
        q.add_filter("views__lt", 1000)
        compiled = SQLCompiler().compile(q)
        assert "views > ?" in compiled.sql
        assert "views < ?" in compiled.sql
        assert "AND" in compiled.sql

    def test_select_in_operator(self):
        q = Query(Article)
        q.add_filter("views__in", [1, 2, 3])
        compiled = SQLCompiler().compile(q)
        assert "views IN (?, ?, ?)" in compiled.sql
        assert compiled.params == (1, 2, 3)

    def test_select_is_null(self):
        q = Query(Article)
        q.add_filter("views__isnull", True)
        compiled = SQLCompiler().compile(q)
        assert "views IS NULL" in compiled.sql
        assert compiled.params == ()

    def test_select_order_by(self):
        from debugorm.core.query import OrderByClause
        q = Query(Article)
        q.order_by_clauses = [OrderByClause("views", descending=True)]
        compiled = SQLCompiler().compile(q)
        assert "ORDER BY views DESC" in compiled.sql

    def test_select_limit_offset(self):
        q = Query(Article)
        q.limit_value = 10
        q.offset_value = 20
        compiled = SQLCompiler().compile(q)
        assert "LIMIT ?" in compiled.sql
        assert "OFFSET ?" in compiled.sql
        assert compiled.params == (10, 20)

    def test_select_custom_fields(self):
        q = Query(Article)
        q.select_fields = ["id", "title"]
        compiled = SQLCompiler().compile(q)
        assert compiled.sql.startswith("SELECT id, title FROM")


class TestInsertCompilation:
    def test_basic_insert(self):
        q = Query(Article)
        q.query_type = "INSERT"
        q.data = {"title": "Hello", "views": 0}
        compiled = SQLCompiler().compile(q)
        assert "INSERT INTO articles" in compiled.sql
        assert "title" in compiled.sql
        assert compiled.params == ("Hello", 0)


class TestUpdateCompilation:
    def test_basic_update(self):
        q = Query(Article)
        q.query_type = "UPDATE"
        q.data = {"title": "Updated", "views": 5}
        q.pk_value = 1
        compiled = SQLCompiler().compile(q)
        assert "UPDATE articles SET" in compiled.sql
        assert "WHERE id = ?" in compiled.sql
        assert 1 in compiled.params


class TestDeleteCompilation:
    def test_basic_delete(self):
        q = Query(Article)
        q.query_type = "DELETE"
        q.pk_value = 42
        compiled = SQLCompiler().compile(q)
        assert compiled.sql == "DELETE FROM articles WHERE id = ?"
        assert compiled.params == (42,)


class TestInterpolated:
    def test_string_params_quoted(self):
        q = Query(Article)
        q.add_filter("title__like", "Py%")
        compiled = SQLCompiler().compile(q)
        assert "'Py%'" in compiled.interpolated()

    def test_int_params_unquoted(self):
        q = Query(Article)
        q.add_filter("views__gt", 100)
        compiled = SQLCompiler().compile(q)
        assert "100" in compiled.interpolated()
        assert "?" not in compiled.interpolated()

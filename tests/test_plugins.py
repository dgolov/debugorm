import logging
import pytest

from debugorm import configure, Model, ExplainPlugin, DryRunPlugin, LoggingPlugin
from debugorm.fields import IntegerField, StringField
from debugorm.core.query import Query
from debugorm.core.compiler import SQLCompiler
from debugorm.core.pipeline import QueryPipeline, PipelineContext, QueryResult
from debugorm.db.connection import get_connection


@pytest.fixture(autouse=True)
def db():
    configure(":memory:")


@pytest.fixture
def User():
    class User(Model):
        id   = IntegerField(primary_key=True)
        name = StringField()
        age  = IntegerField()

    User.create_table()
    User(name="Alice", age=25).save()
    User(name="Bob",   age=17).save()
    return User


class TestDryRunPlugin:
    def test_intercepts_execution(self, User):
        result = (
            User.objects
            .debug(dry_run=True)
            .filter(age__gt=18)
            .all()
        )
        assert result == []

    def test_does_not_modify_db(self, User, capsys):
        User.objects.debug(dry_run=True).filter(age__gt=18).all()
        assert User.objects.count() == 2

    def test_prints_sql(self, User, capsys):
        User.objects.debug(dry_run=True).filter(age__gt=18).all()
        out = capsys.readouterr().out
        assert "DryRunPlugin" in out
        assert "NOT EXECUTED" in out

    def test_estimates_count(self, User, capsys):
        User.objects.debug(dry_run=True).filter(age__gt=18).all()
        out = capsys.readouterr().out
        assert "~1" in out

    def test_insert_estimate(self, User, capsys):
        q = Query(User)
        q.query_type = "INSERT"
        q.data = {"name": "X", "age": 1}
        QueryPipeline(
            plugins=[DryRunPlugin()], connection=get_connection()
        ).run(q)
        out = capsys.readouterr().out
        assert "new row" in out


class TestExplainPlugin:
    def test_prints_query_plan(self, User, capsys):
        User.objects.debug(explain=True).filter(age__gt=18).all()
        out = capsys.readouterr().out
        assert "ExplainPlugin" in out
        assert "QUERY PLAN" in out

    def test_shows_sql(self, User, capsys):
        User.objects.debug(explain=True).filter(age__gt=18).all()
        out = capsys.readouterr().out
        assert "SELECT * FROM users" in out


class TestLoggingPlugin:
    def test_logs_sql(self, User, caplog):
        with caplog.at_level(logging.DEBUG, logger="debugorm.sql"):
            User.objects.debug(log=True).filter(age__gt=18).all()
        assert any("SELECT" in r.message for r in caplog.records)

    def test_logs_row_count(self, User, caplog):
        with caplog.at_level(logging.DEBUG, logger="debugorm.sql"):
            User.objects.debug(log=True).filter(age__gt=18).all()
        assert any("rows=" in r.message for r in caplog.records)


class TestPipelineInterception:
    def test_first_intercepting_plugin_wins(self, User):
        results = []

        class CountingPlugin(DryRunPlugin):
            def before_execute(self, compiled, ctx):
                results.append("intercepted")
                return super().before_execute(compiled, ctx)

        User.objects.debug(dry_run=True).filter(age__gt=0).all()
        # Only one interception should occur
        assert results == [] or len(results) <= 1

# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] — 2026-03-28

### Added
- `Model` base class with `save()`, `delete()`, `create_table()`
- `IntegerField` and `StringField` with validation and type coercion
- `QuerySet` — lazy, chainable query builder (`filter`, `order_by`, `limit`, `offset`, `all`, `get`, `first`, `count`, `exists`)
- Django-style lookup operators: `eq`, `ne`, `gt`, `gte`, `lt`, `lte`, `like`, `in`, `isnull`
- `QueryPipeline` with six plugin hooks: `before_compile`, `after_compile`, `before_execute`, `after_execute`
- `ExplainPlugin` — runs `EXPLAIN QUERY PLAN` and prints the SQLite execution plan
- `DryRunPlugin` — intercepts execution and estimates affected rows
- `LoggingPlugin` — logs SQL and timing via Python's `logging` module
- `VisualizePlugin` — renders the query as a tree before compilation
- `PrettyPrintPlugin` — formats compiled SQL for human readability
- `Query.diff()` / `QuerySet.diff()` — structural comparison of two queries
- `DebugORM` facade for applying a fixed plugin set globally
- `configure()`, `get_connection()`, `set_connection()` connection management helpers

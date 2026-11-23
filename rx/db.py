"""Connect to Postgres and build the schema from sql/*.sql."""
from __future__ import annotations

import sys
from pathlib import Path

import psycopg
from pgvector.psycopg import register_vector
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo

from rx import config

HINT = ("Is Postgres running, and does RX_DSN point at it? Create the"
        " databases with `make db`, build rx with `make index`"
        " (appendix A).")


# region: connect
def connect(dsn: str | None = None) -> psycopg.Connection:
    """Open an autocommit connection that understands vectors."""
    try:
        conn = psycopg.connect(dsn or config.DSN, autocommit=True)
    except psycopg.OperationalError as exc:
        raise psycopg.OperationalError(f"{exc}\n{HINT}") from exc
    conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
    register_vector(conn)
    return conn
# endregion: connect


# region: apply-sql
def apply_sql(conn: psycopg.Connection, path: str | Path) -> None:
    """Run every statement in one .sql file."""
    conn.execute(Path(path).read_text())
# endregion: apply-sql


# region: reset-schema
# The schema files each book adds, in the order they apply. A Book 1
# database applies Book 1's files only, so its timings never include
# a later book's triggers; Books 2 and 3 apply theirs on top. A new
# file directly under sql/ must be named here (sql_files checks).
SQL_BOOKS = {
    1: ("001_core", "040_vectors", "050_fts", "050_hybrid",
        "060_catalog", "070_blocks", "080_chunks", "090_metadata",
        "100_entities", "120_ingest"),
    2: ("110_query_log", "130_citations", "140_telemetry",
        "141_online", "150_traces", "160_training_pairs", "170_ann",
        "180_shards", "190_prepared", "200_versions",
        "210_overrides"),
    3: ("220_conversations", "230_visual", "240_erp", "250_agent",
        "270_dashboard"),
}


def sql_files(book: int = 3) -> list[Path]:
    """sql/*.sql for Books 1 to `book`, in file-name order.

    A file SQL_BOOKS doesn't name is an error. A named file that isn't
    there yet is skipped: the companion repository gains its schema
    files chapter by chapter."""
    known = {n for names in SQL_BOOKS.values() for n in names}
    found = {p.stem: p for p in config.SQL_DIR.glob("*.sql")}
    if set(found) - known:
        raise RuntimeError("sql/ has files rx.db.SQL_BOOKS doesn't "
                           f"name: {sorted(set(found) - known)}")
    want = {n for b, names in SQL_BOOKS.items() if b <= book
            for n in names}
    return [found[n] for n in sorted(want & set(found))]


def reset_schema(conn: psycopg.Connection, book: int = 3) -> None:
    """Drop everything in schema public and rebuild it from sql/,
    with the files of Books 1 to `book`."""
    conn.execute("DROP SCHEMA IF EXISTS public CASCADE")
    conn.execute("CREATE SCHEMA public")
    conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
    register_vector(conn)  # the new vector type has a new OID
    for path in sql_files(book):
        apply_sql(conn, path)
# endregion: reset-schema


# region: scratch-databases
def dbname(dsn: str) -> str:
    """The database a connection string names ('rx' by default)."""
    return conninfo_to_dict(dsn).get("dbname") or "rx"


def scratch_dsn(name: str, base: str | None = None) -> str:
    """RX_DSN with the database renamed to rx_<name>, e.g. rx_ch07.

    Same server, user and options, so a lab never needs its own
    settings; commands that reset a schema default to one of these."""
    return make_conninfo(base or config.DSN, dbname=f"rx_{name}")


def ensure_database(dsn: str) -> bool:
    """Create the database named in dsn if it is missing.

    Returns True when it was created. Needs the CREATEDB privilege,
    which the `postgres` role has."""
    name = dbname(dsn)
    last: Exception | None = None
    for admin_db in ("postgres", "template1"):
        try:
            admin = psycopg.connect(make_conninfo(dsn, dbname=admin_db),
                                    autocommit=True)
        except psycopg.OperationalError as exc:
            last = exc
            continue
        with admin:
            if admin.execute("SELECT 1 FROM pg_database"
                             " WHERE datname = %s", (name,)).fetchone():
                return False
            try:
                admin.execute(sql.SQL("CREATE DATABASE {}").format(
                    sql.Identifier(name)))
            except psycopg.errors.DuplicateDatabase:
                return False                # another session won
            except psycopg.Error as exc:
                raise RuntimeError(
                    f"could not create database {name}: {exc}; run"
                    f" `createdb {name}` as a role that may, or pass"
                    " --dsn") from exc
        print(f"created database {name}", file=sys.stderr)
        return True
    raise psycopg.OperationalError(f"{last}\n{HINT}") from last


def lab_dsn(dsn: str | None, name: str) -> str:
    """The --dsn a lab command was given, or its scratch database.

    The scratch database is created if missing, and the choice is
    printed, so a command never resets a database silently."""
    target = dsn or scratch_dsn(name)
    ensure_database(target)
    print(f"using database {dbname(target)}", file=sys.stderr)
    return target


def table_rows(conn: psycopg.Connection, table: str) -> int:
    """Rows in a table, or 0 when it doesn't exist (yet)."""
    if conn.execute("SELECT to_regclass(%s)", (table,)).fetchone()[0] \
            is None:
        return 0
    return conn.execute(sql.SQL("SELECT count(*) FROM {}").format(
        sql.Identifier(table))).fetchone()[0]


def ensure_schema(conn: psycopg.Connection, book: int = 3) -> bool:
    """Build the schema in a database that has none yet (a new
    scratch database); True when it did. Never touches one that has."""
    if conn.execute("SELECT to_regclass('chunks')").fetchone()[0]:
        return False
    reset_schema(conn, book)
    return True
# endregion: scratch-databases

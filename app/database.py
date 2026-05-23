import json
import shutil
import sqlite3
from collections.abc import Mapping
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from app.config import BACKUP_DIR, DB_PATH, DATABASE_URL

SCHEMA_VERSION = 1
USE_POSTGRES = bool(DATABASE_URL)


def _adapt_sql(sql: str) -> str:
    if USE_POSTGRES:
        return sql.replace("?", "%s")
    return sql


class _Row(Mapping):
    def __init__(self, data):
        if isinstance(data, sqlite3.Row):
            self._d = dict(data)
        elif isinstance(data, Mapping):
            self._d = dict(data)
        else:
            self._d = dict(data)

    def __getitem__(self, key):
        if isinstance(key, int):
            return list(self._d.values())[key]
        return self._d[key]

    def __iter__(self):
        return iter(self._d)

    def __len__(self):
        return len(self._d)


class _CursorResult:
    def __init__(self, rowcount: int = 0, lastrowid: int | None = None, rows=None):
        self.rowcount = rowcount
        self.lastrowid = lastrowid
        self._rows = list(rows or [])

    def fetchone(self):
        if not self._rows:
            return None
        return self._rows.pop(0)

    def fetchall(self):
        rows, self._rows = self._rows, []
        return rows


class DbConnection:
    def __init__(self, raw):
        self._raw = raw

    def execute(self, sql: str, params: tuple | list = ()):
        sql = _adapt_sql(sql)
        if USE_POSTGRES:
            import psycopg2.extras

            cur = self._raw.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            sql_upper = sql.strip().upper()
            is_insert = sql_upper.startswith("INSERT")
            tem_id = "INTO TRATATIVAS" in sql_upper or "INTO VENDAS" in sql_upper
            if is_insert and tem_id and "RETURNING" not in sql_upper:
                sql = sql.rstrip().rstrip(";") + " RETURNING id"
            cur.execute(sql, tuple(params))
            if is_insert and "RETURNING" in sql.upper():
                row = cur.fetchone()
                return _CursorResult(
                    cur.rowcount, row["id"] if row and "id" in row else None
                )
            if is_insert:
                return _CursorResult(cur.rowcount)
            if cur.description:
                return _CursorResult(rows=[_Row(r) for r in cur.fetchall()])
            return _CursorResult(cur.rowcount)
        cur = self._raw.execute(sql, params)
        if cur.description:
            return _CursorResult(rows=[_Row(r) for r in cur.fetchall()])
        return _CursorResult(cur.rowcount, cur.lastrowid)

    def executescript(self, script: str):
        if USE_POSTGRES:
            for stmt in script.split(";"):
                s = stmt.strip()
                if s:
                    self.execute(s)
            return
        self._raw.executescript(script)

    def commit(self):
        self._raw.commit()

    def rollback(self):
        self._raw.rollback()


def _connect():
    if USE_POSTGRES:
        import psycopg2

        url = DATABASE_URL
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        return psycopg2.connect(url, connect_timeout=15, sslmode="require")
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=FULL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def get_db():
    raw = _connect()
    conn = DbConnection(raw)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        raw.close()


def _pg_schema():
    return """
    CREATE TABLE IF NOT EXISTS schema_meta (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS tratativas (
        id SERIAL PRIMARY KEY,
        data_registro TEXT NOT NULL,
        setor TEXT NOT NULL,
        situacao TEXT NOT NULL,
        tempo_solucao TEXT,
        impacto_reais DOUBLE PRECISION,
        status TEXT NOT NULL,
        observacao TEXT,
        criado_em TEXT NOT NULL,
        atualizado_em TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS vendas (
        id SERIAL PRIMARY KEY,
        data_registro TEXT NOT NULL,
        pedido TEXT NOT NULL,
        valor DOUBLE PRECISION NOT NULL,
        convertido INTEGER NOT NULL DEFAULT 0,
        id_perda INTEGER REFERENCES tratativas(id),
        observacao TEXT,
        criado_em TEXT NOT NULL,
        atualizado_em TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_tratativas_status ON tratativas(status);
    CREATE INDEX IF NOT EXISTS idx_tratativas_setor ON tratativas(setor);
    CREATE INDEX IF NOT EXISTS idx_vendas_convertido ON vendas(convertido);
    """


def _sqlite_schema():
    return """
    CREATE TABLE IF NOT EXISTS schema_meta (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS tratativas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data_registro TEXT NOT NULL,
        setor TEXT NOT NULL,
        situacao TEXT NOT NULL,
        tempo_solucao TEXT,
        impacto_reais REAL,
        status TEXT NOT NULL,
        observacao TEXT,
        criado_em TEXT NOT NULL,
        atualizado_em TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS vendas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data_registro TEXT NOT NULL,
        pedido TEXT NOT NULL,
        valor REAL NOT NULL,
        convertido INTEGER NOT NULL DEFAULT 0,
        id_perda INTEGER,
        observacao TEXT,
        criado_em TEXT NOT NULL,
        atualizado_em TEXT NOT NULL,
        FOREIGN KEY (id_perda) REFERENCES tratativas(id)
    );
    CREATE INDEX IF NOT EXISTS idx_tratativas_status ON tratativas(status);
    CREATE INDEX IF NOT EXISTS idx_tratativas_setor ON tratativas(setor);
    CREATE INDEX IF NOT EXISTS idx_vendas_convertido ON vendas(convertido);
    """


def init_db():
    if not USE_POSTGRES:
        try:
            backup_database("pre_init")
        except OSError:
            pass
    with get_db() as conn:
        conn.executescript(_pg_schema() if USE_POSTGRES else _sqlite_schema())
        row = conn.execute(
            "SELECT value FROM schema_meta WHERE key = ?", ("version",)
        ).fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO schema_meta (key, value) VALUES (?, ?)",
                ("version", str(SCHEMA_VERSION)),
            )


def backup_database(reason: str = "manual") -> Path | None:
    if USE_POSTGRES or not DB_PATH.exists():
        return None
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = BACKUP_DIR / f"vendas_tratativas_{reason}_{stamp}.db"
    shutil.copy2(DB_PATH, dest)
    wal = Path(str(DB_PATH) + "-wal")
    if wal.exists():
        shutil.copy2(wal, BACKUP_DIR / f"{dest.stem}-wal.db")
    return dest


def export_json_snapshot() -> Path:
    backup_database("pre_export")
    snapshot = {"exportado_em": datetime.now().isoformat(), "tratativas": [], "vendas": []}
    with get_db() as conn:
        snapshot["tratativas"] = [
            dict(r) for r in conn.execute("SELECT * FROM tratativas ORDER BY id").fetchall()
        ]
        snapshot["vendas"] = [
            dict(r) for r in conn.execute("SELECT * FROM vendas ORDER BY id").fetchall()
        ]
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = BACKUP_DIR / f"snapshot_{stamp}.json"
    path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    return path

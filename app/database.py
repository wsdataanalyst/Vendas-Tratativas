import json
import shutil
import sqlite3
from collections.abc import Mapping
from contextlib import contextmanager
from pathlib import Path

from app.config import BACKUP_DIR, DB_PATH, DATABASE_URL
from app.utils.datetime_br import agora_iso

SCHEMA_VERSION = 4
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
            tem_id = any(
                x in sql_upper
                for x in ("INTO TRATATIVAS", "INTO VENDAS", "INTO NEGOCIOS")
            )
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
        codigo_item TEXT,
        numero_orcamento TEXT,
        observacao TEXT,
        criado_em TEXT NOT NULL,
        atualizado_em TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS vendas (
        id SERIAL PRIMARY KEY,
        data_registro TEXT NOT NULL,
        tipo TEXT NOT NULL DEFAULT 'performance',
        pedido TEXT NOT NULL,
        valor DOUBLE PRECISION NOT NULL,
        status_venda TEXT,
        previsao_data TEXT,
        cliente TEXT,
        vendedor TEXT,
        convertido INTEGER NOT NULL DEFAULT 0,
        motivo_perda TEXT,
        id_perda INTEGER REFERENCES tratativas(id),
        id_tratativa INTEGER REFERENCES tratativas(id),
        resultado_tratativa TEXT,
        concorrencia TEXT,
        observacao TEXT,
        criado_em TEXT NOT NULL,
        atualizado_em TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS negocios (
        id SERIAL PRIMARY KEY,
        data_registro TEXT NOT NULL,
        referencia TEXT NOT NULL,
        cliente TEXT,
        vendedor TEXT,
        valor DOUBLE PRECISION NOT NULL,
        status TEXT NOT NULL DEFAULT 'Em acompanhamento',
        motivo_perda TEXT,
        id_tratativa INTEGER REFERENCES tratativas(id),
        concorrencia TEXT,
        observacao TEXT,
        criado_em TEXT NOT NULL,
        atualizado_em TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_tratativas_status ON tratativas(status);
    CREATE INDEX IF NOT EXISTS idx_tratativas_setor ON tratativas(setor);
    CREATE INDEX IF NOT EXISTS idx_vendas_convertido ON vendas(convertido);
    CREATE INDEX IF NOT EXISTS idx_negocios_status ON negocios(status);
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
        codigo_item TEXT,
        numero_orcamento TEXT,
        observacao TEXT,
        criado_em TEXT NOT NULL,
        atualizado_em TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS vendas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data_registro TEXT NOT NULL,
        tipo TEXT NOT NULL DEFAULT 'performance',
        pedido TEXT NOT NULL,
        valor REAL NOT NULL,
        status_venda TEXT,
        previsao_data TEXT,
        cliente TEXT,
        vendedor TEXT,
        convertido INTEGER NOT NULL DEFAULT 0,
        motivo_perda TEXT,
        id_perda INTEGER,
        id_tratativa INTEGER,
        resultado_tratativa TEXT,
        concorrencia TEXT,
        observacao TEXT,
        criado_em TEXT NOT NULL,
        atualizado_em TEXT NOT NULL,
        FOREIGN KEY (id_perda) REFERENCES tratativas(id),
        FOREIGN KEY (id_tratativa) REFERENCES tratativas(id)
    );
    CREATE TABLE IF NOT EXISTS negocios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data_registro TEXT NOT NULL,
        referencia TEXT NOT NULL,
        cliente TEXT,
        vendedor TEXT,
        valor REAL NOT NULL,
        status TEXT NOT NULL DEFAULT 'Em acompanhamento',
        motivo_perda TEXT,
        id_tratativa INTEGER,
        concorrencia TEXT,
        observacao TEXT,
        criado_em TEXT NOT NULL,
        atualizado_em TEXT NOT NULL,
        FOREIGN KEY (id_tratativa) REFERENCES tratativas(id)
    );
    CREATE INDEX IF NOT EXISTS idx_tratativas_status ON tratativas(status);
    CREATE INDEX IF NOT EXISTS idx_tratativas_setor ON tratativas(setor);
    CREATE INDEX IF NOT EXISTS idx_vendas_convertido ON vendas(convertido);
    CREATE INDEX IF NOT EXISTS idx_negocios_status ON negocios(status);
    """


def _coluna_existe(conn, tabela: str, coluna: str) -> bool:
    if USE_POSTGRES:
        row = conn.execute(
            """
            SELECT 1 FROM information_schema.columns
            WHERE table_name = ? AND column_name = ?
            """,
            (tabela.lower(), coluna),
        ).fetchone()
        return row is not None
    rows = conn.execute(f"PRAGMA table_info({tabela})").fetchall()
    return any(r["name"] == coluna for r in rows)


def _tabela_existe(conn, tabela: str) -> bool:
    if USE_POSTGRES:
        row = conn.execute(
            "SELECT 1 FROM information_schema.tables WHERE table_name = ?",
            (tabela.lower(),),
        ).fetchone()
        return row is not None
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (tabela,),
    ).fetchone()
    return row is not None


def _migrate_v2(conn):
    if not _tabela_existe(conn, "negocios"):
        if USE_POSTGRES:
            conn.execute(
                """
                CREATE TABLE negocios (
                    id SERIAL PRIMARY KEY,
                    data_registro TEXT NOT NULL,
                    referencia TEXT NOT NULL,
                    cliente TEXT,
                    vendedor TEXT,
                    valor DOUBLE PRECISION NOT NULL,
                    status TEXT NOT NULL DEFAULT 'Em acompanhamento',
                    motivo_perda TEXT,
                    id_tratativa INTEGER REFERENCES tratativas(id),
                    concorrencia TEXT,
                    observacao TEXT,
                    criado_em TEXT NOT NULL,
                    atualizado_em TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_negocios_status ON negocios(status)"
            )
        else:
            conn.execute(
                """
                CREATE TABLE negocios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    data_registro TEXT NOT NULL,
                    referencia TEXT NOT NULL,
                    cliente TEXT,
                    vendedor TEXT,
                    valor REAL NOT NULL,
                    status TEXT NOT NULL DEFAULT 'Em acompanhamento',
                    motivo_perda TEXT,
                    id_tratativa INTEGER,
                    concorrencia TEXT,
                    observacao TEXT,
                    criado_em TEXT NOT NULL,
                    atualizado_em TEXT NOT NULL,
                    FOREIGN KEY (id_tratativa) REFERENCES tratativas(id)
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_negocios_status ON negocios(status)"
            )

    for col, tipo in (("motivo_perda", "TEXT"), ("concorrencia", "TEXT")):
        if not _coluna_existe(conn, "vendas", col):
            conn.execute(f"ALTER TABLE vendas ADD COLUMN {col} {tipo}")


def _migrate_v3(conn):
    if not _coluna_existe(conn, "tratativas", "codigo_item"):
        conn.execute("ALTER TABLE tratativas ADD COLUMN codigo_item TEXT")


def _migrate_v4(conn):
    if not _coluna_existe(conn, "tratativas", "numero_orcamento"):
        conn.execute("ALTER TABLE tratativas ADD COLUMN numero_orcamento TEXT")

    cols_vendas = [
        ("tipo", "TEXT"),
        ("status_venda", "TEXT"),
        ("previsao_data", "TEXT"),
        ("cliente", "TEXT"),
        ("vendedor", "TEXT"),
        ("id_tratativa", "INTEGER"),
        ("resultado_tratativa", "TEXT"),
    ]
    for col, tipo in cols_vendas:
        if not _coluna_existe(conn, "vendas", col):
            conn.execute(f"ALTER TABLE vendas ADD COLUMN {col} {tipo}")

    conn.execute(
        """
        UPDATE vendas SET tipo = 'tratativa', id_tratativa = id_perda
        WHERE id_perda IS NOT NULL AND (tipo IS NULL OR tipo = 'performance')
        """
    )
    conn.execute(
        """
        UPDATE vendas SET tipo = 'performance'
        WHERE id_perda IS NULL AND (tipo IS NULL OR tipo = '')
        """
    )
    conn.execute(
        """
        UPDATE vendas SET status_venda = 'Venda Realizada'
        WHERE tipo = 'performance' AND status_venda IS NULL AND convertido = 1
        """
    )
    conn.execute(
        """
        UPDATE vendas SET status_venda = 'Negócio perdido'
        WHERE tipo = 'performance' AND status_venda IS NULL AND convertido = 0
        """
    )
    conn.execute(
        """
        UPDATE vendas SET resultado_tratativa = 'com_impacto'
        WHERE tipo = 'tratativa' AND resultado_tratativa IS NULL
        AND id_tratativa IN (
            SELECT id FROM tratativas WHERE status = 'Resolvido com impacto'
        )
        """
    )
    conn.execute(
        """
        UPDATE vendas SET resultado_tratativa = 'sem_impacto'
        WHERE tipo = 'tratativa' AND resultado_tratativa IS NULL
        AND id_tratativa IS NOT NULL
        """
    )

    if _tabela_existe(conn, "negocios"):
        rows = conn.execute("SELECT * FROM negocios").fetchall()
        mapa_status = {
            "Em acompanhamento": "Em andamento",
            "Convertido": "Venda Realizada",
            "Perdido": "Negócio perdido",
        }
        for n in rows:
            st = mapa_status.get(n["status"], "Em andamento")
            conn.execute(
                """
                INSERT INTO vendas (
                    data_registro, tipo, pedido, valor, status_venda, cliente, vendedor,
                    motivo_perda, id_tratativa, concorrencia, observacao,
                    convertido, criado_em, atualizado_em
                ) VALUES (?, 'performance', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    n["data_registro"],
                    n["referencia"],
                    n["valor"],
                    st,
                    n.get("cliente"),
                    n.get("vendedor"),
                    n.get("motivo_perda"),
                    n.get("id_tratativa"),
                    n.get("concorrencia"),
                    n.get("observacao"),
                    1 if st == "Venda Realizada" else 0,
                    n["criado_em"],
                    n["atualizado_em"],
                ),
            )


def _aplicar_migracoes(conn, version: int) -> int:
    if version < 2:
        _migrate_v2(conn)
        version = 2
    if version < 3:
        _migrate_v3(conn)
        version = 3
    if version < 4:
        _migrate_v4(conn)
        version = 4
    return version


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
        version = int(row["value"]) if row else 0
        if row is None:
            conn.execute(
                "INSERT INTO schema_meta (key, value) VALUES (?, ?)",
                ("version", str(SCHEMA_VERSION)),
            )
            version = SCHEMA_VERSION
        if version < SCHEMA_VERSION:
            version = _aplicar_migracoes(conn, version)
            conn.execute(
                "UPDATE schema_meta SET value = ? WHERE key = 'version'",
                (str(version),),
            )
        ts_row = conn.execute(
            "SELECT value FROM schema_meta WHERE key = 'ultima_atualizacao'"
        ).fetchone()
        if ts_row is None:
            conn.execute(
                "INSERT INTO schema_meta (key, value) VALUES (?, ?)",
                ("ultima_atualizacao", agora_iso()),
            )


def backup_database(reason: str = "manual") -> Path | None:
    if USE_POSTGRES or not DB_PATH.exists():
        return None
    from datetime import datetime

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = BACKUP_DIR / f"vendas_tratativas_{reason}_{stamp}.db"
    shutil.copy2(DB_PATH, dest)
    wal = Path(str(DB_PATH) + "-wal")
    if wal.exists():
        shutil.copy2(wal, BACKUP_DIR / f"{dest.stem}-wal.db")
    return dest


def export_json_snapshot() -> Path:
    from datetime import datetime

    backup_database("pre_export")
    snapshot = {
        "exportado_em": agora_iso(),
        "tratativas": [],
        "vendas": [],
        "negocios": [],
    }
    with get_db() as conn:
        snapshot["tratativas"] = [
            dict(r)
            for r in conn.execute("SELECT * FROM tratativas ORDER BY id").fetchall()
        ]
        snapshot["vendas"] = [
            dict(r) for r in conn.execute("SELECT * FROM vendas ORDER BY id").fetchall()
        ]
        if _tabela_existe(conn, "negocios"):
            snapshot["negocios"] = [
                dict(r)
                for r in conn.execute("SELECT * FROM negocios ORDER BY id").fetchall()
            ]
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = BACKUP_DIR / f"snapshot_{stamp}.json"
    path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    return path

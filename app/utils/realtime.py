from app.database import get_db
from app.utils.cache import invalidate
from app.utils.datetime_br import agora_iso


def marcar_atualizacao():
    invalidate("contagens", "metricas")
    ts = agora_iso()
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO schema_meta (key, value) VALUES ('ultima_atualizacao', ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (ts,),
        )


def versao_atual() -> str:
    with get_db() as conn:
        row = conn.execute(
            "SELECT value FROM schema_meta WHERE key = 'ultima_atualizacao'"
        ).fetchone()
    return row["value"] if row else ""

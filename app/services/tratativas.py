from datetime import datetime

from app.config import STATUS_EM_ABERTO
from app.database import get_db


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def listar_em_aberto():
    placeholders = ",".join("?" * len(STATUS_EM_ABERTO))
    sql = f"SELECT * FROM tratativas WHERE status IN ({placeholders}) ORDER BY id DESC"
    with get_db() as conn:
        rows = conn.execute(sql, STATUS_EM_ABERTO).fetchall()
    return [dict(r) for r in rows]


def listar(filtro_status: str | None = None, filtro_setor: str | None = None):
    sql = "SELECT * FROM tratativas WHERE 1=1"
    params: list = []
    if filtro_status:
        sql += " AND status = ?"
        params.append(filtro_status)
    if filtro_setor:
        sql += " AND setor = ?"
        params.append(filtro_setor)
    sql += " ORDER BY id DESC"
    with get_db() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def obter(tratativa_id: int):
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM tratativas WHERE id = ?", (tratativa_id,)
        ).fetchone()
    return dict(row) if row else None


def criar(dados: dict) -> int:
    agora = _now()
    with get_db() as conn:
        cur = conn.execute(
            """
            INSERT INTO tratativas (
                data_registro, setor, situacao, tempo_solucao,
                impacto_reais, status, observacao, criado_em, atualizado_em
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                dados.get("data_registro") or agora,
                dados["setor"],
                dados["situacao"],
                dados.get("tempo_solucao"),
                dados.get("impacto_reais"),
                dados["status"],
                dados.get("observacao"),
                agora,
                agora,
            ),
        )
        return cur.lastrowid


def atualizar(tratativa_id: int, dados: dict) -> bool:
    agora = _now()
    with get_db() as conn:
        cur = conn.execute(
            """
            UPDATE tratativas SET
                setor = ?, situacao = ?, tempo_solucao = ?,
                impacto_reais = ?, status = ?, observacao = ?,
                atualizado_em = ?
            WHERE id = ?
            """,
            (
                dados["setor"],
                dados["situacao"],
                dados.get("tempo_solucao"),
                dados.get("impacto_reais"),
                dados["status"],
                dados.get("observacao"),
                agora,
                tratativa_id,
            ),
        )
        return cur.rowcount > 0


def excluir(tratativa_id: int) -> bool:
    with get_db() as conn:
        conn.execute(
            "UPDATE vendas SET id_perda = NULL WHERE id_perda = ?", (tratativa_id,)
        )
        cur = conn.execute("DELETE FROM tratativas WHERE id = ?", (tratativa_id,))
        return cur.rowcount > 0


def metricas():
    with get_db() as conn:
        total = conn.execute("SELECT COUNT(*) FROM tratativas").fetchone()[0]
        em_andamento = conn.execute(
            f"""
            SELECT COUNT(*) FROM tratativas
            WHERE status IN ({",".join("?" * len(STATUS_EM_ABERTO))})
            """,
            STATUS_EM_ABERTO,
        ).fetchone()[0]
        impacto_total = conn.execute(
            """
            SELECT COALESCE(SUM(impacto_reais), 0) FROM tratativas
            WHERE status IN ('Resolvido com impacto', 'Em andamento c/impacto')
            AND impacto_reais IS NOT NULL
            """
        ).fetchone()[0]
        por_setor = conn.execute(
            """
            SELECT setor, COUNT(*) as qtd,
                   COALESCE(SUM(impacto_reais), 0) as impacto
            FROM tratativas GROUP BY setor ORDER BY qtd DESC
            """
        ).fetchall()
    return {
        "total": total,
        "em_andamento": em_andamento,
        "impacto_total": float(impacto_total or 0),
        "por_setor": [dict(r) for r in por_setor],
    }

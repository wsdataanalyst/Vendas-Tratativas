from app.config import STATUS_EM_ABERTO
from app.database import get_db
from app.utils.datetime_br import agora_iso
from app.utils.realtime import marcar_atualizacao


def listar_em_aberto():
    placeholders = ",".join("?" * len(STATUS_EM_ABERTO))
    sql = f"SELECT * FROM tratativas WHERE status IN ({placeholders}) ORDER BY id DESC"
    with get_db() as conn:
        rows = conn.execute(sql, STATUS_EM_ABERTO).fetchall()
    return [dict(r) for r in rows]


def listar(
    filtro_status: str | None = None,
    filtro_setor: str | None = None,
    apenas_resolvidas: bool = False,
):
    sql = "SELECT * FROM tratativas WHERE 1=1"
    params: list = []
    if filtro_status:
        sql += " AND status = ?"
        params.append(filtro_status)
    if filtro_setor:
        sql += " AND setor = ?"
        params.append(filtro_setor)
    if apenas_resolvidas:
        from app.config import STATUS_TRATATIVA_RESOLVIDA

        ph = ",".join("?" * len(STATUS_TRATATIVA_RESOLVIDA))
        sql += f" AND status IN ({ph})"
        params.extend(STATUS_TRATATIVA_RESOLVIDA)
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
    agora = agora_iso()
    with get_db() as conn:
        cur = conn.execute(
            """
            INSERT INTO tratativas (
                data_registro, setor, situacao, tempo_solucao,
                impacto_reais, status, codigo_item, numero_orcamento,
                observacao, criado_em, atualizado_em
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                dados.get("data_registro") or agora,
                dados["setor"],
                dados["situacao"],
                dados.get("tempo_solucao"),
                dados.get("impacto_reais"),
                dados["status"],
                dados.get("codigo_item"),
                dados.get("numero_orcamento"),
                dados.get("observacao"),
                agora,
                agora,
            ),
        )
        tid = cur.lastrowid
    marcar_atualizacao()
    return tid


def atualizar(tratativa_id: int, dados: dict) -> bool:
    agora = agora_iso()
    with get_db() as conn:
        cur = conn.execute(
            """
            UPDATE tratativas SET
                setor = ?, situacao = ?, tempo_solucao = ?,
                impacto_reais = ?, status = ?, codigo_item = ?,
                numero_orcamento = ?, observacao = ?, atualizado_em = ?
            WHERE id = ?
            """,
            (
                dados["setor"],
                dados["situacao"],
                dados.get("tempo_solucao"),
                dados.get("impacto_reais"),
                dados["status"],
                dados.get("codigo_item"),
                dados.get("numero_orcamento"),
                dados.get("observacao"),
                agora,
                tratativa_id,
            ),
        )
        ok = cur.rowcount > 0
    if ok:
        marcar_atualizacao()
    return ok


def excluir(tratativa_id: int) -> bool:
    with get_db() as conn:
        conn.execute(
            "UPDATE vendas SET id_perda = NULL WHERE id_perda = ?", (tratativa_id,)
        )
        cur = conn.execute("DELETE FROM tratativas WHERE id = ?", (tratativa_id,))
        ok = cur.rowcount > 0
    if ok:
        marcar_atualizacao()
    return ok


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
        resolvidas = conn.execute(
            """
            SELECT COUNT(*) FROM tratativas
            WHERE status IN ('Resolvido com impacto', 'Resolvido sem impacto')
            """
        ).fetchone()[0]
    return {
        "total": total,
        "em_andamento": em_andamento,
        "resolvidas": resolvidas,
        "impacto_total": float(impacto_total or 0),
        "por_setor": [dict(r) for r in por_setor],
    }

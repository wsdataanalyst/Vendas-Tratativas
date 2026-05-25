from app.database import get_db
from app.utils.datetime_br import agora_iso
from app.utils.realtime import marcar_atualizacao


def listar_sem_conversao():
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT v.*, t.situacao as tratativa_situacao, t.setor as tratativa_setor
            FROM vendas v
            LEFT JOIN tratativas t ON v.id_perda = t.id
            WHERE v.convertido = 0
            ORDER BY v.id DESC
            """
        ).fetchall()
    return [dict(r) for r in rows]


def listar():
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT v.*, t.situacao as tratativa_situacao, t.setor as tratativa_setor
            FROM vendas v
            LEFT JOIN tratativas t ON v.id_perda = t.id
            ORDER BY v.id DESC
            """
        ).fetchall()
    return [dict(r) for r in rows]


def criar(dados: dict) -> int:
    agora = agora_iso()
    with get_db() as conn:
        cur = conn.execute(
            """
            INSERT INTO vendas (
                data_registro, pedido, valor, convertido, motivo_perda,
                id_perda, concorrencia, observacao, criado_em, atualizado_em
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                dados.get("data_registro") or agora,
                dados["pedido"],
                float(dados["valor"]),
                1 if dados.get("convertido") else 0,
                dados.get("motivo_perda"),
                dados.get("id_perda") or None,
                dados.get("concorrencia"),
                dados.get("observacao"),
                agora,
                agora,
            ),
        )
        vid = cur.lastrowid
    marcar_atualizacao()
    return vid


def atualizar(venda_id: int, dados: dict) -> bool:
    agora = agora_iso()
    with get_db() as conn:
        cur = conn.execute(
            """
            UPDATE vendas SET
                pedido = ?, valor = ?, convertido = ?, motivo_perda = ?,
                id_perda = ?, concorrencia = ?, observacao = ?, atualizado_em = ?
            WHERE id = ?
            """,
            (
                dados["pedido"],
                float(dados["valor"]),
                1 if dados.get("convertido") else 0,
                dados.get("motivo_perda"),
                dados.get("id_perda") or None,
                dados.get("concorrencia"),
                dados.get("observacao"),
                agora,
                venda_id,
            ),
        )
        ok = cur.rowcount > 0
    if ok:
        marcar_atualizacao()
    return ok


def excluir(venda_id: int) -> bool:
    with get_db() as conn:
        cur = conn.execute("DELETE FROM vendas WHERE id = ?", (venda_id,))
        ok = cur.rowcount > 0
    if ok:
        marcar_atualizacao()
    return ok


def metricas():
    with get_db() as conn:
        total = conn.execute("SELECT COUNT(*) FROM vendas").fetchone()[0]
        convertidas = conn.execute(
            "SELECT COUNT(*) FROM vendas WHERE convertido = 1"
        ).fetchone()[0]
        valor_total = conn.execute(
            "SELECT COALESCE(SUM(valor), 0) FROM vendas"
        ).fetchone()[0]
        valor_convertido = conn.execute(
            "SELECT COALESCE(SUM(valor), 0) FROM vendas WHERE convertido = 1"
        ).fetchone()[0]
        sem_conversao = conn.execute(
            "SELECT COUNT(*) FROM vendas WHERE convertido = 0"
        ).fetchone()[0]
        sem_conversao_sem_vinculo = conn.execute(
            """
            SELECT COUNT(*) FROM vendas
            WHERE convertido = 0
            AND (
                (COALESCE(motivo_perda, 'tratativa') = 'tratativa' AND id_perda IS NULL)
                OR (motivo_perda = 'concorrencia' AND (concorrencia IS NULL OR concorrencia = ''))
            )
            """
        ).fetchone()[0]
        valor_perdido = conn.execute(
            "SELECT COALESCE(SUM(valor), 0) FROM vendas WHERE convertido = 0"
        ).fetchone()[0]
    taxa = (convertidas / total * 100) if total else 0
    return {
        "total": total,
        "convertidas": convertidas,
        "sem_conversao": sem_conversao,
        "sem_conversao_sem_vinculo": sem_conversao_sem_vinculo,
        "valor_total": float(valor_total or 0),
        "valor_convertido": float(valor_convertido or 0),
        "valor_perdido": float(valor_perdido or 0),
        "taxa_conversao": round(taxa, 1),
    }

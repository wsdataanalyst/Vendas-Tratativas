"""Vendas originadas de tratativas resolvidas (com ou sem impacto)."""

from app.config import (
    RESULTADO_COM_IMPACTO,
    RESULTADO_SEM_IMPACTO,
    STATUS_TRATATIVA_RESOLVIDA,
    TIPO_VENDA_TRATATIVA,
)
from app.database import get_db
from app.utils.datetime_br import agora_iso
from app.utils.realtime import marcar_atualizacao

_TIPO = TIPO_VENDA_TRATATIVA


def _resultado_de_status(status_tratativa: str) -> str:
    if status_tratativa == "Resolvido com impacto":
        return RESULTADO_COM_IMPACTO
    return RESULTADO_SEM_IMPACTO


def listar():
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT v.*, t.setor as tratativa_setor, t.situacao as tratativa_situacao,
                   t.status as tratativa_status, t.numero_orcamento as tratativa_orcamento
            FROM vendas v
            JOIN tratativas t ON v.id_tratativa = t.id
            WHERE v.tipo = ?
            ORDER BY v.id DESC
            """,
            (_TIPO,),
        ).fetchall()
    return [dict(r) for r in rows]


def listar_por_tratativa(tratativa_id: int):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM vendas WHERE tipo = ? AND id_tratativa = ? ORDER BY id DESC",
            (_TIPO, tratativa_id),
        ).fetchall()
    return [dict(r) for r in rows]


def criar(dados: dict, status_tratativa: str) -> int:
    agora = agora_iso()
    resultado = dados.get("resultado_tratativa") or _resultado_de_status(
        status_tratativa
    )
    tid = dados["id_tratativa"]
    with get_db() as conn:
        cur = conn.execute(
            """
            INSERT INTO vendas (
                data_registro, tipo, pedido, valor, status_venda, convertido,
                id_perda, id_tratativa, resultado_tratativa, observacao,
                criado_em, atualizado_em
            ) VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?)
            """,
            (
                dados.get("data_registro") or agora,
                _TIPO,
                dados["pedido"],
                float(dados["valor"]),
                "Venda Realizada",
                tid,
                tid,
                resultado,
                dados.get("observacao"),
                agora,
                agora,
            ),
        )
        vid = cur.lastrowid
    marcar_atualizacao()
    return vid


def atualizar(venda_id: int, dados: dict, status_tratativa: str | None = None) -> bool:
    agora = agora_iso()
    resultado = dados.get("resultado_tratativa")
    if not resultado and status_tratativa:
        resultado = _resultado_de_status(status_tratativa)
    with get_db() as conn:
        cur = conn.execute(
            """
            UPDATE vendas SET
                pedido = ?, valor = ?, resultado_tratativa = ?,
                observacao = ?, atualizado_em = ?
            WHERE id = ? AND tipo = ?
            """,
            (
                dados["pedido"],
                float(dados["valor"]),
                resultado,
                dados.get("observacao"),
                agora,
                venda_id,
                _TIPO,
            ),
        )
        ok = cur.rowcount > 0
    if ok:
        marcar_atualizacao()
    return ok


def excluir(venda_id: int) -> bool:
    with get_db() as conn:
        cur = conn.execute(
            "DELETE FROM vendas WHERE id = ? AND tipo = ?", (venda_id, _TIPO)
        )
        ok = cur.rowcount > 0
    if ok:
        marcar_atualizacao()
    return ok


def metricas():
    with get_db() as conn:
        total = conn.execute(
            "SELECT COUNT(*) FROM vendas WHERE tipo = ?", (_TIPO,)
        ).fetchone()[0]
        sem_impacto = conn.execute(
            """
            SELECT COUNT(*) FROM vendas
            WHERE tipo = ? AND resultado_tratativa = ?
            """,
            (_TIPO, RESULTADO_SEM_IMPACTO),
        ).fetchone()[0]
        com_impacto = conn.execute(
            """
            SELECT COUNT(*) FROM vendas
            WHERE tipo = ? AND resultado_tratativa = ?
            """,
            (_TIPO, RESULTADO_COM_IMPACTO),
        ).fetchone()[0]
        valor_total = conn.execute(
            "SELECT COALESCE(SUM(valor), 0) FROM vendas WHERE tipo = ?", (_TIPO,)
        ).fetchone()[0]
        valor_sem = conn.execute(
            """
            SELECT COALESCE(SUM(valor), 0) FROM vendas
            WHERE tipo = ? AND resultado_tratativa = ?
            """,
            (_TIPO, RESULTADO_SEM_IMPACTO),
        ).fetchone()[0]
        valor_com = conn.execute(
            """
            SELECT COALESCE(SUM(valor), 0) FROM vendas
            WHERE tipo = ? AND resultado_tratativa = ?
            """,
            (_TIPO, RESULTADO_COM_IMPACTO),
        ).fetchone()[0]
    return {
        "total": total,
        "sem_impacto": sem_impacto,
        "com_impacto": com_impacto,
        "valor_total": float(valor_total or 0),
        "valor_sem_impacto": float(valor_sem or 0),
        "valor_com_impacto": float(valor_com or 0),
        "status_resolvidos": STATUS_TRATATIVA_RESOLVIDA,
    }

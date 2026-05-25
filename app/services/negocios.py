from app.config import MOTIVOS_PERDA, STATUS_NEGOCIO
from app.database import get_db
from app.utils.datetime_br import agora_iso
from app.utils.realtime import marcar_atualizacao


def listar(filtro_status: str | None = None):
    sql = """
        SELECT n.*, t.situacao as tratativa_situacao, t.setor as tratativa_setor
        FROM negocios n
        LEFT JOIN tratativas t ON n.id_tratativa = t.id
        WHERE 1=1
    """
    params: list = []
    if filtro_status:
        sql += " AND n.status = ?"
        params.append(filtro_status)
    sql += " ORDER BY n.id DESC"
    with get_db() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def listar_em_acompanhamento():
    return listar(filtro_status="Em acompanhamento")


def listar_perdidos():
    return listar(filtro_status="Perdido")


def criar(dados: dict) -> int:
    agora = agora_iso()
    with get_db() as conn:
        cur = conn.execute(
            """
            INSERT INTO negocios (
                data_registro, referencia, cliente, vendedor, valor, status,
                motivo_perda, id_tratativa, concorrencia, observacao,
                criado_em, atualizado_em
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                dados.get("data_registro") or agora,
                dados["referencia"],
                dados.get("cliente"),
                dados.get("vendedor"),
                float(dados["valor"]),
                dados.get("status", "Em acompanhamento"),
                dados.get("motivo_perda"),
                dados.get("id_tratativa"),
                dados.get("concorrencia"),
                dados.get("observacao"),
                agora,
                agora,
            ),
        )
        nid = cur.lastrowid
    marcar_atualizacao()
    return nid


def atualizar(negocio_id: int, dados: dict) -> bool:
    agora = agora_iso()
    with get_db() as conn:
        cur = conn.execute(
            """
            UPDATE negocios SET
                referencia = ?, cliente = ?, vendedor = ?, valor = ?, status = ?,
                motivo_perda = ?, id_tratativa = ?, concorrencia = ?, observacao = ?,
                atualizado_em = ?
            WHERE id = ?
            """,
            (
                dados["referencia"],
                dados.get("cliente"),
                dados.get("vendedor"),
                float(dados["valor"]),
                dados["status"],
                dados.get("motivo_perda"),
                dados.get("id_tratativa"),
                dados.get("concorrencia"),
                dados.get("observacao"),
                agora,
                negocio_id,
            ),
        )
        ok = cur.rowcount > 0
    if ok:
        marcar_atualizacao()
    return ok


def excluir(negocio_id: int) -> bool:
    with get_db() as conn:
        cur = conn.execute("DELETE FROM negocios WHERE id = ?", (negocio_id,))
        ok = cur.rowcount > 0
    if ok:
        marcar_atualizacao()
    return ok


def metricas():
    with get_db() as conn:
        total = conn.execute("SELECT COUNT(*) FROM negocios").fetchone()[0]
        em_acompanhamento = conn.execute(
            "SELECT COUNT(*) FROM negocios WHERE status = 'Em acompanhamento'"
        ).fetchone()[0]
        convertidos = conn.execute(
            "SELECT COUNT(*) FROM negocios WHERE status = 'Convertido'"
        ).fetchone()[0]
        perdidos = conn.execute(
            "SELECT COUNT(*) FROM negocios WHERE status = 'Perdido'"
        ).fetchone()[0]
        valor_total = conn.execute(
            "SELECT COALESCE(SUM(valor), 0) FROM negocios"
        ).fetchone()[0]
        valor_convertido = conn.execute(
            "SELECT COALESCE(SUM(valor), 0) FROM negocios WHERE status = 'Convertido'"
        ).fetchone()[0]
        perdidos_sem_vinculo = conn.execute(
            """
            SELECT COUNT(*) FROM negocios
            WHERE status = 'Perdido' AND motivo_perda = 'tratativa' AND id_tratativa IS NULL
            """
        ).fetchone()[0]
    taxa = (convertidos / total * 100) if total else 0
    return {
        "total": total,
        "em_acompanhamento": em_acompanhamento,
        "convertidos": convertidos,
        "perdidos": perdidos,
        "valor_total": float(valor_total or 0),
        "valor_convertido": float(valor_convertido or 0),
        "taxa_conversao": round(taxa, 1),
        "perdidos_sem_vinculo": perdidos_sem_vinculo,
    }

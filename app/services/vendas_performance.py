"""Vendas Performance — acompanhamento direto sem vínculo com tratativa."""

from app.config import STATUS_VENDA_PERFORMANCE, TIPO_VENDA_PERFORMANCE
from app.database import get_db
from app.utils.datetime_br import agora_iso
from app.utils.realtime import marcar_atualizacao

_TIPO = TIPO_VENDA_PERFORMANCE


def _filtro_op(registrado_por: str | None) -> tuple[str, list]:
    if registrado_por:
        return " AND registrado_por = ?", [registrado_por]
    return "", []


def listar(filtro_status: str | None = None, registrado_por: str | None = None):
    sql = "SELECT * FROM vendas WHERE tipo = ?"
    params: list = [_TIPO]
    if filtro_status:
        sql += " AND status_venda = ?"
        params.append(filtro_status)
    extra, extra_p = _filtro_op(registrado_por)
    sql += extra
    params.extend(extra_p)
    sql += " ORDER BY id DESC"
    with get_db() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def listar_em_andamento(registrado_por: str | None = None):
    return listar(filtro_status="Em andamento", registrado_por=registrado_por)


def listar_perdidos(registrado_por: str | None = None):
    return listar(filtro_status="Negócio perdido", registrado_por=registrado_por)


def criar(dados: dict) -> int:
    agora = agora_iso()
    status = dados["status_venda"]
    with get_db() as conn:
        cur = conn.execute(
            """
            INSERT INTO vendas (
                data_registro, tipo, pedido, valor, status_venda, previsao_data,
                cliente, vendedor, convertido, motivo_perda, concorrencia,
                registrado_por, observacao, criado_em, atualizado_em
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                dados.get("data_registro") or agora,
                _TIPO,
                dados["pedido"],
                float(dados["valor"]),
                status,
                dados.get("previsao_data"),
                dados.get("cliente"),
                dados.get("vendedor"),
                1 if status == "Venda Realizada" else 0,
                dados.get("motivo_perda"),
                dados.get("concorrencia"),
                dados.get("registrado_por"),
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
    status = dados["status_venda"]
    with get_db() as conn:
        cur = conn.execute(
            """
            UPDATE vendas SET
                pedido = ?, valor = ?, status_venda = ?, previsao_data = ?,
                cliente = ?, vendedor = ?, convertido = ?,
                motivo_perda = ?, concorrencia = ?, observacao = ?, atualizado_em = ?
            WHERE id = ? AND tipo = ?
            """,
            (
                dados["pedido"],
                float(dados["valor"]),
                status,
                dados.get("previsao_data"),
                dados.get("cliente"),
                dados.get("vendedor"),
                1 if status == "Venda Realizada" else 0,
                dados.get("motivo_perda"),
                dados.get("concorrencia"),
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


def metricas(registrado_por: str | None = None):
    extra, params = _filtro_op(registrado_por)
    base = f"FROM vendas WHERE tipo = ?{extra}"
    p = [_TIPO, *params]
    with get_db() as conn:
        total = conn.execute(f"SELECT COUNT(*) {base}", p).fetchone()[0]
        realizadas = conn.execute(
            f"SELECT COUNT(*) {base} AND status_venda = 'Venda Realizada'", p
        ).fetchone()[0]
        em_andamento = conn.execute(
            f"SELECT COUNT(*) {base} AND status_venda = 'Em andamento'", p
        ).fetchone()[0]
        perdidos = conn.execute(
            f"SELECT COUNT(*) {base} AND status_venda = 'Negócio perdido'", p
        ).fetchone()[0]
        valor_total = conn.execute(
            f"SELECT COALESCE(SUM(valor), 0) {base}", p
        ).fetchone()[0]
        valor_realizado = conn.execute(
            f"SELECT COALESCE(SUM(valor), 0) {base} AND status_venda = 'Venda Realizada'",
            p,
        ).fetchone()[0]
    taxa = (realizadas / total * 100) if total else 0
    return {
        "total": total,
        "realizadas": realizadas,
        "em_andamento": em_andamento,
        "perdidos": perdidos,
        "valor_total": float(valor_total or 0),
        "valor_realizado": float(valor_realizado or 0),
        "taxa_conversao": round(taxa, 1),
        "status_opts": STATUS_VENDA_PERFORMANCE,
    }

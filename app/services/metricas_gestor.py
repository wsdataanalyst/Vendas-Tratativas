"""Métricas consolidadas e por operador para o painel gestor."""

from app import auth
from app.services import tratativas as svc_trat
from app.services import vendas_performance as svc_perf
from app.services import vendas_tratativa as svc_vtrat


def _somar(*dicts, key):
    return sum(d.get(key, 0) or 0 for d in dicts)


def painel_gestor() -> dict:
    """Retorna consolidado + métricas por operador."""
    por_op: dict[str, dict] = {}
    perf_ops = []
    vtrat_ops = []
    trat_ops = []

    for op_id, nome, _ in auth.listar_operadores():
        m_perf = svc_perf.metricas(registrado_por=op_id)
        m_vtrat = svc_vtrat.metricas(registrado_por=op_id)
        m_trat = svc_trat.metricas(registrado_por=op_id)
        por_op[op_id] = {
            "id": op_id,
            "nome": nome,
            "perf": m_perf,
            "vtrat": m_vtrat,
            "trat": m_trat,
        }
        perf_ops.append(m_perf)
        vtrat_ops.append(m_vtrat)
        trat_ops.append(m_trat)
    m_perf = {
        "total": _somar(*perf_ops, key="total"),
        "realizadas": _somar(*perf_ops, key="realizadas"),
        "em_andamento": _somar(*perf_ops, key="em_andamento"),
        "perdidos": _somar(*perf_ops, key="perdidos"),
        "valor_total": _somar(*perf_ops, key="valor_total"),
        "valor_realizado": _somar(*perf_ops, key="valor_realizado"),
    }
    total_p = m_perf["total"]
    m_perf["taxa_conversao"] = round(
        (m_perf["realizadas"] / total_p * 100) if total_p else 0, 1
    )

    m_vtrat = {
        "total": _somar(*vtrat_ops, key="total"),
        "sem_impacto": _somar(*vtrat_ops, key="sem_impacto"),
        "com_impacto": _somar(*vtrat_ops, key="com_impacto"),
        "valor_total": _somar(*vtrat_ops, key="valor_total"),
        "valor_sem_impacto": _somar(*vtrat_ops, key="valor_sem_impacto"),
        "valor_com_impacto": _somar(*vtrat_ops, key="valor_com_impacto"),
    }

    m_trat = {
        "total": _somar(*trat_ops, key="total"),
        "em_andamento": _somar(*trat_ops, key="em_andamento"),
        "resolvidas": _somar(*trat_ops, key="resolvidas"),
        "impacto_total": _somar(*trat_ops, key="impacto_total"),
    }

    m_perf["valor_vendas_todas"] = m_perf["valor_realizado"] + m_vtrat["valor_total"]

    return {
        "consolidado": {
            "perf": m_perf,
            "vtrat": m_vtrat,
            "trat": m_trat,
        },
        "por_operador": por_op,
    }

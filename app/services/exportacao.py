"""Geração de planilha Excel com todos os registros."""

from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from app.services import negocios as svc_negocios
from app.services import tratativas as svc_tratativas
from app.services import vendas as svc_vendas
from app.utils.datetime_br import agora_iso


def _estilizar_cabecalho(ws, colunas: int):
    fill = PatternFill(start_color="1E3A5F", end_color="1E3A5F", fill_type="solid")
    font = Font(bold=True, color="FFFFFF", size=11)
    for col in range(1, colunas + 1):
        cell = ws.cell(row=1, column=col)
        cell.fill = fill
        cell.font = font
        cell.alignment = Alignment(horizontal="center", vertical="center")


def _ajustar_larguras(ws, larguras: list[int]):
    for i, w in enumerate(larguras, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w


def gerar_excel() -> tuple[BytesIO, str]:
    tratativas = svc_tratativas.listar()
    vendas = svc_vendas.listar()
    negocios = svc_negocios.listar()
    m_trat = svc_tratativas.metricas()
    m_vendas = svc_vendas.metricas()
    m_neg = svc_negocios.metricas()

    wb = Workbook()

    ws_neg = wb.active
    ws_neg.title = "Negocios"
    cab_neg = [
        "Data",
        "ID",
        "Referência",
        "Cliente",
        "Vendedor",
        "Valor (R$)",
        "Status",
        "Motivo perda",
        "ID Tratativa",
        "Concorrência",
        "Observação",
        "Criado em",
        "Atualizado em",
    ]
    ws_neg.append(cab_neg)
    _estilizar_cabecalho(ws_neg, len(cab_neg))
    for n in negocios:
        ws_neg.append(
            [
                n.get("data_registro", ""),
                n.get("id"),
                n.get("referencia", ""),
                n.get("cliente") or "",
                n.get("vendedor") or "",
                n.get("valor"),
                n.get("status", ""),
                n.get("motivo_perda") or "",
                n.get("id_tratativa") or "",
                n.get("concorrencia") or "",
                n.get("observacao") or "",
                n.get("criado_em", ""),
                n.get("atualizado_em", ""),
            ]
        )
    _ajustar_larguras(ws_neg, [18, 6, 18, 16, 14, 12, 16, 14, 10, 22, 28, 18, 18])

    ws_trat = wb.create_sheet("Tratativas")
    cab_trat = [
        "Data",
        "ID",
        "Setor",
        "Situação",
        "Tempo de Solução",
        "R$ Impacto",
        "Status",
        "Código item",
        "Observação",
        "Criado em",
        "Atualizado em",
    ]
    ws_trat.append(cab_trat)
    _estilizar_cabecalho(ws_trat, len(cab_trat))
    for t in tratativas:
        ws_trat.append(
            [
                t.get("data_registro", ""),
                t.get("id"),
                t.get("setor", ""),
                t.get("situacao", ""),
                t.get("tempo_solucao") or "",
                t.get("impacto_reais"),
                t.get("status", ""),
                t.get("codigo_item") or "",
                t.get("observacao") or "",
                t.get("criado_em", ""),
                t.get("atualizado_em", ""),
            ]
        )
    _ajustar_larguras(ws_trat, [18, 6, 14, 38, 14, 12, 22, 14, 30, 18, 18])

    ws_vendas = wb.create_sheet("Vendas")
    cab_vendas = [
        "Data",
        "Pedido",
        "Valor (R$)",
        "Convertido",
        "Motivo perda",
        "ID Tratativa",
        "Concorrência",
        "Setor (tratativa)",
        "Situação (tratativa)",
        "Observação",
        "Criado em",
        "Atualizado em",
    ]
    ws_vendas.append(cab_vendas)
    _estilizar_cabecalho(ws_vendas, len(cab_vendas))
    for v in vendas:
        ws_vendas.append(
            [
                v.get("data_registro", ""),
                v.get("pedido", ""),
                v.get("valor"),
                "Sim" if v.get("convertido") else "Não",
                v.get("motivo_perda") or "",
                v.get("id_perda") or "",
                v.get("concorrencia") or "",
                v.get("tratativa_setor") or "",
                v.get("tratativa_situacao") or "",
                v.get("observacao") or "",
                v.get("criado_em", ""),
                v.get("atualizado_em", ""),
            ]
        )
    _ajustar_larguras(ws_vendas, [18, 14, 12, 10, 14, 10, 22, 14, 38, 30, 18, 18])

    ws_resumo = wb.create_sheet("Resumo", 0)
    ws_resumo.append(["Vendas & Tratativas — Exportação"])
    ws_resumo["A1"].font = Font(bold=True, size=14)
    ws_resumo.append(["Exportado em (Brasília)", agora_iso()])
    ws_resumo.append([])
    ws_resumo.append(["Negócios"])
    ws_resumo.append(["Total", m_neg["total"]])
    ws_resumo.append(["Em acompanhamento", m_neg["em_acompanhamento"]])
    ws_resumo.append(["Convertidos", m_neg["convertidos"]])
    ws_resumo.append(["Perdidos", m_neg["perdidos"]])
    ws_resumo.append(["Taxa conversão (%)", m_neg["taxa_conversao"]])
    ws_resumo.append([])
    ws_resumo.append(["Tratativas"])
    ws_resumo.append(["Total", m_trat["total"]])
    ws_resumo.append(["Em aberto", m_trat["em_andamento"]])
    ws_resumo.append(["Impacto (R$)", m_trat["impacto_total"]])
    ws_resumo.append([])
    ws_resumo.append(["Vendas"])
    ws_resumo.append(["Total", m_vendas["total"]])
    ws_resumo.append(["Convertidas", m_vendas["convertidas"]])
    ws_resumo.append(["Sem conversão", m_vendas["sem_conversao"]])
    ws_resumo.append(["Taxa conversão (%)", m_vendas["taxa_conversao"]])
    _ajustar_larguras(ws_resumo, [28, 22])

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    nome = f"vendas_tratativas_{agora_iso().replace(':', '').replace(' ', '_')}.xlsx"
    return buffer, nome

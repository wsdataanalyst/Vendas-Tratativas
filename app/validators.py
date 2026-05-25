"""Validação de formulários."""

from app.config import SITUACOES_COM_CODIGO_ITEM, STATUS_TRATATIVA_RESOLVIDA


def validar_tratativa_situacao(
    situacao: str, codigo_item: str | None
) -> tuple[bool, str]:
    if situacao in SITUACOES_COM_CODIGO_ITEM and not (codigo_item or "").strip():
        return False, "Informe o código do item para esta situação."
    return True, ""


def validar_venda_performance(
    status: str,
    previsao_data: str | None = None,
    motivo_perda: str | None = None,
    concorrencia: str | None = None,
) -> tuple[bool, str]:
    if status == "Em andamento" and not (previsao_data or "").strip():
        return False, "Registre a previsão (data) para vendas em andamento."
    if status == "Negócio perdido":
        motivo = (motivo_perda or "concorrencia").strip().lower()
        if motivo == "concorrencia" and not (concorrencia or "").strip():
            return (
                False,
                "Informe o motivo de concorrência para negócio perdido.",
            )
    return True, ""


def validar_venda_tratativa(
    id_tratativa: int | None, status_tratativa: str
) -> tuple[bool, str]:
    if not id_tratativa:
        return False, "Selecione a tratativa vinculada."
    if status_tratativa not in STATUS_TRATATIVA_RESOLVIDA:
        return (
            False,
            "Só é possível registrar venda para tratativa resolvida "
            "(com ou sem impacto).",
        )
    return True, ""


def validar_perda(
    *,
    convertido: bool = False,
    status: str | None = None,
    motivo_perda: str | None = None,
    id_tratativa: int | None = None,
    concorrencia: str | None = None,
) -> tuple[bool, str]:
    if convertido or status == "Convertido" or status == "Venda Realizada":
        return True, ""
    if status == "Em acompanhamento" or status == "Em andamento":
        return True, ""

    motivo = (motivo_perda or "tratativa").strip().lower()
    if motivo == "tratativa":
        if not id_tratativa:
            return (
                False,
                "Perda por problema interno exige o ID da tratativa vinculado.",
            )
        return True, ""
    if motivo == "concorrencia":
        if not (concorrencia or "").strip():
            return (
                False,
                "Informe qual concorrente ou motivo de preço.",
            )
        return True, ""
    return True, ""

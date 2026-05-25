"""Validação de formulários."""


def validar_tratativa_situacao(
    situacao: str, codigo_item: str | None
) -> tuple[bool, str]:
    from app.config import SITUACOES_COM_CODIGO_ITEM

    if situacao in SITUACOES_COM_CODIGO_ITEM and not (codigo_item or "").strip():
        return False, "Informe o código do item para esta situação."
    return True, ""


def validar_perda(
    *,
    convertido: bool = False,
    status: str | None = None,
    motivo_perda: str | None = None,
    id_tratativa: int | None = None,
    concorrencia: str | None = None,
) -> tuple[bool, str]:
    """Retorna (ok, mensagem_erro)."""
    if convertido or status == "Convertido":
        return True, ""
    if status == "Em acompanhamento":
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
                "Informe qual concorrente ou motivo de preço (não precisa de tratativa).",
            )
        return True, ""
    return True, ""

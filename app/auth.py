"""Usuários — senhas podem ser definidas por variáveis de ambiente no Render."""

import os

OPERADORES_IDS = ("mayara", "alessandro")

USUARIOS = {
    "mayara": {
        "nome": "Mayara Barros",
        "perfil": "operacional",
        "iniciais": "MB",
        "env_senha": "MAYARA_PASSWORD",
        "senha_padrao": "mayara",
        "titulo_boas_vindas": "Bem-vinda, Mayara Barros!",
        "subtitulo_boas_vindas": (
            "Vendas Performance para follow-up direto; tratativas para problemas "
            "internos e vendas convertidas via tratativa."
        ),
    },
    "alessandro": {
        "nome": "Alessandro",
        "perfil": "operacional",
        "iniciais": "AL",
        "env_senha": "ALESSANDRO_PASSWORD",
        "senha_padrao": "alessandro",
        "titulo_boas_vindas": "Bem-vindo, Alessandro!",
        "subtitulo_boas_vindas": (
            "Vendas Performance para follow-up direto; tratativas para problemas "
            "internos e vendas convertidas via tratativa."
        ),
    },
    "gestor": {
        "nome": "Willame Sousa",
        "perfil": "gestor",
        "iniciais": "WS",
        "env_senha": "GESTOR_PASSWORD",
        "senha_padrao": "161217",
        "titulo_boas_vindas": "Bem-vindo, Willame Sousa!",
        "subtitulo_boas_vindas": (
            "Visão consolidada e performance individual de Mayara e Alessandro."
        ),
    },
}


def _senha_usuario(user: dict) -> str:
    return os.getenv(user["env_senha"], user["senha_padrao"])


def listar_operadores() -> list[tuple[str, str, str]]:
    return [
        (uid, USUARIOS[uid]["nome"], USUARIOS[uid].get("iniciais", uid[:2].upper()))
        for uid in OPERADORES_IDS
        if uid in USUARIOS
    ]


def nome_operador(usuario_id: str | None) -> str:
    if not usuario_id:
        return "—"
    return USUARIOS.get(usuario_id, {}).get("nome", usuario_id)


def autenticar(usuario_id: str, senha: str) -> dict | None:
    user = USUARIOS.get(usuario_id)
    if user and senha == _senha_usuario(user):
        return {
            "id": usuario_id,
            "nome": user["nome"],
            "perfil": user["perfil"],
            "is_gestor": user["perfil"] == "gestor",
            "is_operacional": user["perfil"] == "operacional",
            "titulo_boas_vindas": user["titulo_boas_vindas"],
            "subtitulo_boas_vindas": user["subtitulo_boas_vindas"],
        }
    return None


def obter_usuario(usuario_id: str) -> dict | None:
    user = USUARIOS.get(usuario_id)
    if not user:
        return None
    return {
        "id": usuario_id,
        "nome": user["nome"],
        "perfil": user["perfil"],
        "is_gestor": user["perfil"] == "gestor",
        "is_operacional": user["perfil"] == "operacional",
    }

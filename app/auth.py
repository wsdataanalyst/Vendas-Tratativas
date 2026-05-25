"""Usuários — senhas podem ser definidas por variáveis de ambiente no Render."""

import os

USUARIOS = {
    "mayara": {
        "nome": "Mayara Barros",
        "perfil": "operacional",
        "env_senha": "MAYARA_PASSWORD",
        "senha_padrao": "mayara",
        "titulo_boas_vindas": "Bem-vinda, Mayara Barros!",
        "subtitulo_boas_vindas": (
            "Registre negócios em acompanhamento, tratativas e fechamentos "
            "junto aos vendedores."
        ),
    },
    "gestor": {
        "nome": "Willame Sousa",
        "perfil": "gestor",
        "env_senha": "GESTOR_PASSWORD",
        "senha_padrao": "161217",
        "titulo_boas_vindas": "Bem-vindo, Willame Sousa!",
        "subtitulo_boas_vindas": (
            "Visão gerencial em tempo real — negócios, conversão e tratativas."
        ),
    },
}


def _senha_usuario(user: dict) -> str:
    return os.getenv(user["env_senha"], user["senha_padrao"])


def autenticar(usuario_id: str, senha: str) -> dict | None:
    user = USUARIOS.get(usuario_id)
    if user and senha == _senha_usuario(user):
        return {
            "id": usuario_id,
            "nome": user["nome"],
            "perfil": user["perfil"],
            "is_gestor": user["perfil"] == "gestor",
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
    }

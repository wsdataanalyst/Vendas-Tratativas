"""Usuários locais — operacional e gestor."""

USUARIOS = {
    "mayara": {
        "nome": "Mayara Barros",
        "perfil": "operacional",
        "senha": "mayara",
        "titulo_boas_vindas": "Bem-vinda, Mayara Barros!",
        "subtitulo_boas_vindas": (
            "Registre o acompanhamento de clientes e o fechamento de negócios "
            "junto aos vendedores."
        ),
    },
    "gestor": {
        "nome": "Willame Sousa",
        "perfil": "gestor",
        "senha": "161217",
        "titulo_boas_vindas": "Bem-vindo, Willame Sousa!",
        "subtitulo_boas_vindas": (
            "Visão gerencial dos números e registros de Mayara Barros — "
            "vendas, conversão e tratativas da empresa."
        ),
    },
}


def autenticar(usuario_id: str, senha: str) -> dict | None:
    user = USUARIOS.get(usuario_id)
    if user and user["senha"] == senha:
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

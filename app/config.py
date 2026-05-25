import os
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv

load_dotenv()


def _url_pooler_invalida(url: str) -> bool:
    """Pooler Supabase exige usuario postgres.PROJECT_REF, nao apenas postgres."""
    if "pooler.supabase.com" not in url:
        return False
    if "postgres." in url.split("@")[0]:
        return False
    return "://postgres:" in url or "://postgres@" in url


def _montar_database_url() -> str:
    """Monta URL do Postgres a partir de variáveis separadas (evita erro de senha na URL)."""
    senha = os.getenv("SUPABASE_DB_PASSWORD", "").strip()
    projeto = os.getenv("SUPABASE_PROJECT_REF", "").strip()
    # Render nao alcanca conexao direct (5432/IPv6) — usar pooler
    padrao_modo = "pooler" if os.getenv("RENDER") else "direct"
    modo = os.getenv("SUPABASE_MODE", padrao_modo).strip().lower()

    url = (
        ""
        if os.getenv("RENDER")
        else os.getenv("DATABASE_URL", "").strip()
    )

    if senha and projeto:
        senha_cod = quote_plus(senha)
        if modo == "pooler":
            host = os.getenv(
                "SUPABASE_DB_HOST",
                "aws-1-us-east-1.pooler.supabase.com",
            ).strip()
            usuario = f"postgres.{projeto}"
            porta = 6543
        else:
            host = os.getenv(
                "SUPABASE_DB_HOST",
                f"db.{projeto}.supabase.co",
            ).strip()
            usuario = "postgres"
            porta = 5432
        return (
            f"postgresql://{usuario}:{senha_cod}@{host}:{porta}/postgres"
            "?sslmode=require"
        )

    if url:
        url = url.strip()
    if not url:
        return ""
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    if "[YOUR-PASSWORD]" in url or "YOUR-PASSWORD" in url:
        return ""
    if _url_pooler_invalida(url):
        return ""
    return _garantir_sslmode(url)


def _garantir_sslmode(url: str) -> str:
    if "sslmode=" not in url:
        url += "&sslmode=require" if "?" in url else "?sslmode=require"
    return url

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
BACKUP_DIR = DATA_DIR / "backups"
DB_PATH = DATA_DIR / "vendas_tratativas.db"

DATA_DIR.mkdir(parents=True, exist_ok=True)
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

SECRET_KEY = os.getenv("APP_SECRET_KEY", "dev-only-change-in-production")
DATABASE_URL = _montar_database_url()
# 0.0.0.0 = PC + celulares na mesma rede Wi-Fi; 127.0.0.1 = só neste computador
HOST = os.getenv("APP_HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", os.getenv("APP_PORT", "5050")))
IS_CLOUD = bool(os.getenv("RENDER") or DATABASE_URL)

# Opções de preenchimento (conforme Tratativas.xlsx)
SETORES = [
    "Logistica",
    "Compras",
    "Financeiro",
    "Ti Infra",
    "Ti Sistemas",
]

SITUACOES = [
    "Transferencia para atender pedido",
    "Transferencia para atender estoque",
    "Erro na entrega",
    "Alinhamento de entrega",
    "Ruptura no Estoque - Item no CD",
    "Liberação de Crédito",
    "Comunicação entre setores",
    "Devolução",
    "Prazo de cotação Fabrica",
    "Entrega não realizada",
    "Estornos e Ressarcimentos",
    "Falta de estoque produto indispensavel",
]

# Situações que exigem informar o código do item
SITUACOES_COM_CODIGO_ITEM = ("Falta de estoque produto indispensavel",)

TEMPOS_SOLUCAO = [
    "> 30 min",
    "> 45 min",
    "> 1 h",
    "> 2 h",
    "> 1 d",
    "> 3 d",
    "> 7 d",
]

STATUS_TRATATIVA = [
    "Resolvido com impacto",
    "Resolvido sem impacto",
    "Sem resposta",
    "Em andamento",
    "Em andamento c/impacto",
]

STATUS_EM_ABERTO = ("Em andamento", "Em andamento c/impacto", "Sem resposta")

# Vendas Performance — acompanhamento direto (sem tratativa)
STATUS_VENDA_PERFORMANCE = [
    "Venda Realizada",
    "Em andamento",
    "Negócio perdido",
]

TIPO_VENDA_PERFORMANCE = "performance"
TIPO_VENDA_TRATATIVA = "tratativa"

STATUS_TRATATIVA_RESOLVIDA = (
    "Resolvido com impacto",
    "Resolvido sem impacto",
)

RESULTADO_SEM_IMPACTO = "sem_impacto"
RESULTADO_COM_IMPACTO = "com_impacto"

MOTIVOS_PERDA = [
    ("tratativa", "Problema interno (Tratativa)"),
    ("concorrencia", "Concorrência (preço/outro)"),
    ("outro", "Outro motivo"),
]

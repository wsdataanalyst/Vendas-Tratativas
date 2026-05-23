import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
BACKUP_DIR = DATA_DIR / "backups"
DB_PATH = DATA_DIR / "vendas_tratativas.db"

DATA_DIR.mkdir(parents=True, exist_ok=True)
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

SECRET_KEY = os.getenv("APP_SECRET_KEY", "dev-only-change-in-production")
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
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
]

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

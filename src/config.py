"""
Configuração central do pipeline.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ---- Credencial da service account ----
# Caminho do JSON baixado do Google Cloud. Nunca versionar esse arquivo
CREDENTIALS_FILE = os.getenv("CREDENTIALS_FILE", "credentials.json")

# ---- Planilhas ----
# Origem: a planilha do IPYS (usada só pra leitura)
ORIGEM_SHEET_ID = os.getenv("ORIGEM_SHEET_ID", "")

# Destino: a nossa planilha
DESTINO_SHEET_ID = os.getenv("DESTINO_SHEET_ID", "").strip()

# Nome da aba onde a base limpa é escrita.
ABA_DESTINO = os.getenv("ABA_DESTINO", "CONSOLIDADO")

# ---- Escopos ----
# Sheets pra ler/escrever células; Drive pra criar o arquivo e compartilhar.
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# ---- Abas da origem que não são estados ----
ABAS_IGNORAR = {"COMPLETO"}

# ---- Ordem das colunas da base limpa ----
COLUNAS = [
    "estado",
    "unidade",
    "tipo_unidade",
    "unidade_original",
    "poblacion",
    "tamano",
    "medios_total",
    "medios_urbanos",
    "medios_rurales",
    "medios_plurales",
    "categoria_preliminar",
    "filtro_bosque_pct",
    "categoria_definitiva",
]
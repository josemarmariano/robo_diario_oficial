import os
from dotenv import load_dotenv

load_dotenv()

DATA_TESTE = os.getenv("DATA_TESTE", "").strip()
BASE_URL = os.getenv("BASE_URL", "").strip()
PASTA_DOWNLOAD = os.getenv("PASTA_DOWNLOAD", "storage/pdfs").strip()
PASTA_LOGS = os.getenv("PASTA_LOGS", "storage/logs").strip()
PASTA_RESULTADOS = os.getenv("PASTA_RESULTADOS", "storage/resultados").strip()


def validar_configuracoes():
    erros = []

    if not BASE_URL:
        erros.append("BASE_URL nao configurada no arquivo .env")

    for pasta in [PASTA_DOWNLOAD, PASTA_LOGS, PASTA_RESULTADOS]:
        if not pasta:
            erros.append("Existe uma pasta configurada vazia no arquivo .env")

    if erros:
        raise RuntimeError(" | ".join(erros))
import os
from dotenv import load_dotenv

load_dotenv()

DATA_TESTE = os.getenv("DATA_TESTE", "").strip()
BASE_URL = os.getenv("BASE_URL", "").strip()
PASTA_DOWNLOAD = os.getenv("PASTA_DOWNLOAD", "storage/pdfs").strip()
PASTA_LOGS = os.getenv("PASTA_LOGS", "storage/logs").strip()
PASTA_RESULTADOS = os.getenv("PASTA_RESULTADOS", "storage/resultados").strip()

TERMOS_PESQUISA = os.getenv("TERMOS_PESQUISA", "").strip()

EMAIL_ATIVO = os.getenv("EMAIL_ATIVO", "false").strip().lower() == "true"
EMAIL_SMTP_SERVIDOR = os.getenv("EMAIL_SMTP_SERVIDOR", "").strip()
EMAIL_SMTP_PORTA = int(os.getenv("EMAIL_SMTP_PORTA", "587").strip())
EMAIL_REMETENTE = os.getenv("EMAIL_REMETENTE", "").strip()
EMAIL_SENHA_APP = os.getenv("EMAIL_SENHA_APP", "").strip()
EMAIL_DESTINATARIOS = os.getenv("EMAIL_DESTINATARIOS", "").strip()


def obter_termos_pesquisa():
    if not TERMOS_PESQUISA:
        return []

    termos = []

    for termo in TERMOS_PESQUISA.split(","):
        termo_limpo = termo.strip()

        if termo_limpo:
            termos.append(termo_limpo)

    return termos


def obter_destinatarios_email():
    if not EMAIL_DESTINATARIOS:
        return []

    destinatarios = []

    for email in EMAIL_DESTINATARIOS.split(","):
        email_limpo = email.strip()

        if email_limpo:
            destinatarios.append(email_limpo)

    return destinatarios


def validar_configuracoes():
    erros = []

    if not BASE_URL:
        erros.append("BASE_URL nao configurada no arquivo .env")

    for pasta in [PASTA_DOWNLOAD, PASTA_LOGS, PASTA_RESULTADOS]:
        if not pasta:
            erros.append("Existe uma pasta configurada vazia no arquivo .env")

    if EMAIL_ATIVO:
        if not EMAIL_SMTP_SERVIDOR:
            erros.append("EMAIL_SMTP_SERVIDOR nao configurado no arquivo .env")

        if not EMAIL_REMETENTE:
            erros.append("EMAIL_REMETENTE nao configurado no arquivo .env")

        if not EMAIL_SENHA_APP:
            erros.append("EMAIL_SENHA_APP nao configurado no arquivo .env")

        if not obter_destinatarios_email():
            erros.append("EMAIL_DESTINATARIOS nao configurado no arquivo .env")

    if erros:
        raise RuntimeError(" | ".join(erros))
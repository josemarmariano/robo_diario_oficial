import os
from datetime import datetime
import requests
from app.config import BASE_URL, PASTA_DOWNLOAD


def montar_url_download(data_referencia=None):
    if data_referencia is None:
        data_referencia = datetime.now()

    ano = data_referencia.strftime("%Y")
    mes = data_referencia.strftime("%m")
    dia = data_referencia.strftime("%d")

    return f"{BASE_URL}/{ano}/{mes}/{dia}/"


def montar_nome_arquivo(data_referencia=None):
    if data_referencia is None:
        data_referencia = datetime.now()

    return f"diario_oficial_{data_referencia.strftime('%Y_%m_%d')}.pdf"


def validar_pdf(caminho_arquivo):
    if not os.path.exists(caminho_arquivo):
        raise RuntimeError(f"Arquivo nao encontrado: {caminho_arquivo}")

    tamanho_bytes = os.path.getsize(caminho_arquivo)

    if tamanho_bytes == 0:
        raise RuntimeError("Arquivo baixado esta vazio.")

    with open(caminho_arquivo, "rb") as arquivo:
        assinatura = arquivo.read(5)

    if assinatura != b"%PDF-":
        raise RuntimeError(
            f"Arquivo baixado nao parece ser um PDF valido. "
            f"Assinatura encontrada: {assinatura}"
        )

    return tamanho_bytes


def baixar_pdf_diario(logger, data_referencia=None):
    if data_referencia is None:
        data_referencia = datetime.now()

    os.makedirs(PASTA_DOWNLOAD, exist_ok=True)

    url = montar_url_download(data_referencia)
    nome_arquivo = montar_nome_arquivo(data_referencia)
    caminho_arquivo = os.path.join(PASTA_DOWNLOAD, nome_arquivo)

    logger.info("Iniciando download do Diario Oficial.")
    logger.info("URL: %s", url)
    logger.info("Arquivo destino: %s", caminho_arquivo)

    if os.path.exists(caminho_arquivo):
        logger.info(
            "Arquivo ja existe. Download ignorado: %s",
            caminho_arquivo
        )

        tamanho_bytes = validar_pdf(caminho_arquivo)
        tamanho_mb = tamanho_bytes / (1024 * 1024)

        logger.info(
            "Arquivo existente validado: %s (%s bytes / %.2f MB)",
            caminho_arquivo,
            tamanho_bytes,
            tamanho_mb
        )

        return caminho_arquivo

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    resposta = requests.get(
        url,
        headers=headers,
        stream=True,
        timeout=60,
        allow_redirects=True
    )

    logger.info("Status HTTP: %s", resposta.status_code)
    logger.info("Content-Type: %s", resposta.headers.get("content-type"))
    logger.info("URL final apos redirecionamentos: %s", resposta.url)

    if resposta.status_code != 200:
        raise RuntimeError(
            f"Falha ao baixar arquivo. Status HTTP: {resposta.status_code}"
        )

    with open(caminho_arquivo, "wb") as arquivo:
        for bloco in resposta.iter_content(chunk_size=1024 * 1024):
            if bloco:
                arquivo.write(bloco)

    tamanho_bytes = validar_pdf(caminho_arquivo)
    tamanho_mb = tamanho_bytes / (1024 * 1024)

    logger.info(
        "Download concluido com sucesso: %s (%s bytes / %.2f MB)",
        caminho_arquivo,
        tamanho_bytes,
        tamanho_mb
    )

    return caminho_arquivo
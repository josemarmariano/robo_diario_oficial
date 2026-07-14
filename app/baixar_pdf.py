import os
import re
from datetime import datetime
from urllib.parse import urlparse

import requests
from app.config import BASE_URL, PASTA_DOWNLOAD


HOST_ARQUIVOS_DIARIO = "files.pmp.sp.gov.br"
CAMINHO_ARQUIVOS_DIARIO = "/semad/diariooficial/"


def obter_url_base_site():
    url_base = BASE_URL.rstrip("/")

    if url_base.endswith("/download"):
        url_base = url_base[: -len("/download")]

    return url_base


def montar_url_download(data_referencia=None):
    if data_referencia is None:
        data_referencia = datetime.now()

    ano = data_referencia.strftime("%Y")
    mes = data_referencia.strftime("%m")
    nome_pdf = data_referencia.strftime("%Y%m%d")

    return (
        f"https://{HOST_ARQUIVOS_DIARIO}"
        f"{CAMINHO_ARQUIVOS_DIARIO}{ano}/{mes}/{nome_pdf}.pdf"
    )


def montar_url_pagina_mes(data_referencia):
    ano = data_referencia.strftime("%Y")
    mes = data_referencia.strftime("%m")
    return f"{obter_url_base_site()}/{ano}/{mes}/"


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


def validar_url_pdf_diario(url, data_referencia):
    url_analisada = urlparse(url)
    caminho_esperado = (
        f"{CAMINHO_ARQUIVOS_DIARIO}"
        f"{data_referencia.strftime('%Y')}/"
        f"{data_referencia.strftime('%m')}/"
        f"{data_referencia.strftime('%Y%m%d')}.pdf"
    )

    return (
        url_analisada.scheme == "https"
        and url_analisada.netloc == HOST_ARQUIVOS_DIARIO
        and url_analisada.path == caminho_esperado
    )


def extrair_url_pdf_publicado(html, data_referencia):
    ano = data_referencia.strftime("%Y")
    mes = data_referencia.strftime("%m")
    nome_pdf = data_referencia.strftime("%Y%m%d")

    padrao_thumbnail = re.compile(
        rf"https://{re.escape(HOST_ARQUIVOS_DIARIO)}"
        rf"{re.escape(CAMINHO_ARQUIVOS_DIARIO)}"
        rf"{ano}/{mes}/{nome_pdf}-pdf-[^\"'<>\s]+\.jpg"
    )

    match = padrao_thumbnail.search(html)

    if not match:
        return None

    return montar_url_download(data_referencia)


def localizar_url_pdf_diario(logger, data_referencia):
    url_pagina_mes = montar_url_pagina_mes(data_referencia)

    logger.info("Consultando pagina oficial do mes: %s", url_pagina_mes)

    try:
        resposta = requests.get(
            url_pagina_mes,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=60,
            allow_redirects=True
        )
    except requests.RequestException as erro:
        logger.warning(
            "Erro de conexao ao consultar pagina oficial %s: %s",
            url_pagina_mes,
            erro
        )
        return None

    logger.info(
        "Status HTTP da pagina oficial: %s | Content-Type: %s",
        resposta.status_code,
        resposta.headers.get("Content-Type", "")
    )

    if resposta.status_code != 200:
        logger.warning(
            "Falha ao consultar pagina oficial. URL: %s | Status HTTP: %s",
            url_pagina_mes,
            resposta.status_code
        )
        return None

    url_pdf = extrair_url_pdf_publicado(
        html=resposta.text,
        data_referencia=data_referencia
    )

    if url_pdf is None:
        logger.info(
            "Diario Oficial nao publicado para %s na pagina oficial.",
            data_referencia.date().isoformat()
        )
        return None

    if not validar_url_pdf_diario(url_pdf, data_referencia):
        logger.warning("URL de PDF rejeitada pela validacao: %s", url_pdf)
        return None

    return url_pdf


def remover_arquivo_invalido(caminho_arquivo, logger, motivo):
    logger.warning(
        "Arquivo existente invalido sera removido para novo download: %s | Motivo: %s",
        caminho_arquivo,
        motivo
    )

    try:
        os.remove(caminho_arquivo)
    except OSError as erro:
        raise RuntimeError(
            f"Nao foi possivel remover arquivo invalido {caminho_arquivo}: {erro}"
        ) from erro


def baixar_pdf_diario(logger, data_referencia=None):
    if data_referencia is None:
        data_referencia = datetime.now()

    os.makedirs(PASTA_DOWNLOAD, exist_ok=True)

    nome_arquivo = montar_nome_arquivo(data_referencia)
    caminho_arquivo = os.path.join(PASTA_DOWNLOAD, nome_arquivo)
    caminho_temporario = f"{caminho_arquivo}.tmp"

    logger.info("Iniciando download do Diario Oficial.")
    logger.info("Arquivo destino: %s", caminho_arquivo)

    if os.path.exists(caminho_arquivo):
        logger.info(
            "Arquivo ja existe. Download ignorado: %s",
            caminho_arquivo
        )

        try:
            validar_pdf(caminho_arquivo)
        except RuntimeError as erro:
            remover_arquivo_invalido(caminho_arquivo, logger, erro)
        else:
            logger.info(
                "Arquivo existente validado: %s",
                caminho_arquivo
            )

            return caminho_arquivo, montar_url_download(data_referencia)

    url = localizar_url_pdf_diario(logger, data_referencia)

    if url is None:
        return None, None

    logger.info("URL do PDF publicada: %s", url)

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:
        resposta = requests.get(
            url,
            headers=headers,
            stream=True,
            timeout=60,
            allow_redirects=True
        )
    except requests.RequestException as erro:
        logger.warning(
            "Erro de conexao ao baixar %s: %s",
            url, erro
        )
        return None, None

    logger.info("Status HTTP: %s", resposta.status_code)
    logger.info(
        "Content-Type: %s | URL final: %s",
        resposta.headers.get("Content-Type", ""),
        resposta.url
    )

    if resposta.status_code == 404:
        logger.info(
            "PDF nao encontrado para %s (HTTP 404).",
            data_referencia.date().isoformat()
        )
        return None, None

    if resposta.status_code != 200:
        logger.warning(
            "Falha ao baixar PDF. URL: %s | Status HTTP: %s",
            url,
            resposta.status_code
        )
        return None, None

    content_type = resposta.headers.get("Content-Type", "").lower()

    if "application/pdf" not in content_type:
        logger.warning(
            "Resposta nao parece ser PDF. URL: %s | Content-Type: %s",
            url,
            content_type
        )
        return None, None

    if os.path.exists(caminho_temporario):
        os.remove(caminho_temporario)

    with open(caminho_temporario, "wb") as arquivo:
        for bloco in resposta.iter_content(chunk_size=1024 * 1024):
            if bloco:
                arquivo.write(bloco)

    try:
        validar_pdf(caminho_temporario)
    except RuntimeError:
        if os.path.exists(caminho_temporario):
            os.remove(caminho_temporario)
        raise

    os.replace(caminho_temporario, caminho_arquivo)

    logger.info(
        "Download concluido com sucesso: %s",
        caminho_arquivo
    )

    return caminho_arquivo, url

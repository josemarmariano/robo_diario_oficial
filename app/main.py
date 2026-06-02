from datetime import datetime
from app.baixar_pdf import baixar_pdf_diario
from app.config import (
    DATA_TESTE,
    PASTA_RESULTADOS,
    obter_termos_pesquisa,
    validar_configuracoes
)
from app.enviar_email import enviar_email_alerta
from app.extrair_pdf import extrair_texto_completo, obter_total_paginas
from app.logger import configurar_logger
from app.pesquisar_documento import (
    exibir_resultados,
    pesquisar_termos_pasta,
    salvar_resultados_pesquisa
)
from app.processar_documento import processar_documento


def obter_data_referencia(logger):
    if not DATA_TESTE:
        logger.info("DATA_TESTE nao informada. Usando data atual.")
        return None

    try:
        data_referencia = datetime.strptime(DATA_TESTE, "%Y-%m-%d")
        logger.info("DATA_TESTE informada: %s", DATA_TESTE)
        return data_referencia

    except ValueError as erro:
        raise RuntimeError(
            "DATA_TESTE invalida. Use o formato AAAA-MM-DD. "
            "Exemplo: 2026-05-30"
        ) from erro


def executar_download(data_referencia, logger):
    caminho_pdf = baixar_pdf_diario(
        logger=logger,
        data_referencia=data_referencia
    )

    logger.info("PDF disponivel para processamento: %s", caminho_pdf)

    return caminho_pdf


def executar_extracao(caminho_pdf, logger):
    total_paginas = obter_total_paginas(caminho_pdf)
    logger.info("Total de paginas identificado: %s", total_paginas)

    paginas = extrair_texto_completo(
        caminho_pdf=caminho_pdf,
        logger=logger
    )

    paginas_com_texto = [
        pagina for pagina in paginas
        if pagina["qtde_caracteres"] > 0
    ]

    logger.info(
        "Paginas com texto extraido: %s de %s",
        len(paginas_com_texto),
        total_paginas
    )

    return {
        "total_paginas": total_paginas,
        "paginas": paginas
    }


def executar_processamento(caminho_pdf, paginas, logger):
    artefatos_processamento = processar_documento(
        caminho_pdf=caminho_pdf,
        paginas=paginas,
        logger=logger
    )

    logger.info(
        "Artefatos gerados - bruto: %s | documento: %s",
        artefatos_processamento["bruto"],
        artefatos_processamento["documento"]
    )

    return artefatos_processamento


def executar_pesquisa(logger):
    termos = obter_termos_pesquisa()

    if not termos:
        logger.info("Nenhum termo de pesquisa configurado no .env.")
        return {
            "termos": [],
            "total_resultados": 0,
            "resultados": [],
            "arquivo_resultado": None
        }

    logger.info("Iniciando pesquisa nos arquivos JSON.")
    logger.info("Termos configurados para pesquisa: %s", termos)

    resultados = pesquisar_termos_pasta(
        pasta_resultados=PASTA_RESULTADOS,
        termos=termos,
        logger=logger
    )

    logger.info(
        "Pesquisa finalizada. Total de resultados encontrados: %s",
        len(resultados)
    )

    exibir_resultados(resultados)

    caminho_resultado = salvar_resultados_pesquisa(
        pasta_resultados=PASTA_RESULTADOS,
        resultados=resultados,
        termos=termos
    )

    logger.info("Resultado da pesquisa salvo em: %s", caminho_resultado)

    return {
        "termos": termos,
        "total_resultados": len(resultados),
        "resultados": resultados,
        "arquivo_resultado": caminho_resultado
    }


def executar_alerta_email(resultados, logger):
    email_enviado = enviar_email_alerta(
        resultados=resultados,
        logger=logger
    )

    return {
        "email_enviado": email_enviado
    }


def main():
    logger = configurar_logger()
    artefatos = {}

    try:
        validar_configuracoes()

        logger.info("Configuracoes carregadas com sucesso.")
        logger.info("Robo Diario Oficial iniciado.")

        data_referencia = obter_data_referencia(logger)
        artefatos["data_referencia"] = (
            data_referencia.date().isoformat()
            if data_referencia
            else datetime.now().date().isoformat()
        )

        caminho_pdf = executar_download(
            data_referencia=data_referencia,
            logger=logger
        )

        artefatos["pdf"] = caminho_pdf

        extracao = executar_extracao(
            caminho_pdf=caminho_pdf,
            logger=logger
        )

        artefatos["total_paginas"] = extracao["total_paginas"]

        artefatos_processamento = executar_processamento(
            caminho_pdf=caminho_pdf,
            paginas=extracao["paginas"],
            logger=logger
        )

        artefatos["bruto"] = artefatos_processamento["bruto"]
        artefatos["documento"] = artefatos_processamento["documento"]

        pesquisa = executar_pesquisa(logger)

        artefatos["pesquisa"] = pesquisa["arquivo_resultado"]
        artefatos["total_resultados_pesquisa"] = pesquisa["total_resultados"]

        alerta = executar_alerta_email(
            resultados=pesquisa["resultados"],
            logger=logger
        )

        artefatos["email_enviado"] = alerta["email_enviado"]

        logger.info("Resumo dos artefatos gerados: %s", artefatos)
        logger.info("Robo Diario Oficial finalizado com sucesso.")

    except Exception as erro:
        logger.exception("Erro durante execucao do robo: %s", erro)


if __name__ == "__main__":
    main()
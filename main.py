from datetime import datetime, timedelta
from app.baixar_pdf import baixar_pdf_diario
from app.config import (
    DATA_PESQUISA_DE,
    DATA_PESQUISA_ATE,
    PASTA_RESULTADOS,
    obter_termos_pesquisa,
    validar_configuracoes
)
from app.enviar_email import enviar_email_alerta
from app.extrair_pdf import extrair_texto_completo, obter_total_paginas
from app.logger import configurar_logger
from app.pesquisar_documento import (
    exibir_resultados,
    pesquisar_termos_arquivo,
    salvar_resultados_pesquisa
)
from app.processar_documento import processar_documento


def obter_datas_pesquisa(logger):
    if not DATA_PESQUISA_DE and not DATA_PESQUISA_ATE:
        logger.info(
            "DATA_PESQUISA_DE e DATA_PESQUISA_ATE nao informadas. "
            "Usando data atual."
        )
        return [datetime.now()]

    try:
        data_de = (
            datetime.strptime(DATA_PESQUISA_DE, "%Y-%m-%d")
            if DATA_PESQUISA_DE
            else datetime.now()
        )

        data_ate = (
            datetime.strptime(DATA_PESQUISA_ATE, "%Y-%m-%d")
            if DATA_PESQUISA_ATE
            else data_de
        )

        if data_de > data_ate:
            raise RuntimeError(
                "DATA_PESQUISA_DE nao pode ser posterior "
                "a DATA_PESQUISA_ATE."
            )

        datas = []
        delta = timedelta(days=1)
        data_atual = data_de

        while data_atual <= data_ate:
            datas.append(data_atual)
            data_atual += delta

        logger.info(
            "Range de datas: %s a %s (%s dia(s))",
            data_de.date().isoformat(),
            data_ate.date().isoformat(),
            len(datas)
        )

        return datas

    except ValueError as erro:
        raise RuntimeError(
            "DATA_PESQUISA_DE ou DATA_PESQUISA_ATE invalida. "
            "Use o formato AAAA-MM-DD. Exemplo: 2026-05-30"
        ) from erro


def executar_download(data_referencia, logger):
    caminho_pdf, url_download = baixar_pdf_diario(
        logger=logger,
        data_referencia=data_referencia
    )

    if caminho_pdf is None:
        return None

    logger.info("PDF disponivel para processamento: %s", caminho_pdf)

    return caminho_pdf, url_download


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


def executar_alerta_email(resultados, logger):
    termos_pesquisa = obter_termos_pesquisa()
    
    email_enviado = enviar_email_alerta(
        resultados=resultados,
        logger=logger,
        termos=termos_pesquisa
    )

    return {
        "email_enviado": email_enviado
    }


def main():
    logger = configurar_logger()
    resultados_consolidados = []
    datas_processadas = 0
    datas_com_erro = 0
    artefatos = {}

    try:
        validar_configuracoes()

        logger.info("Configuracoes carregadas com sucesso.")
        logger.info("Robo Diario Oficial iniciado.")

        datas = obter_datas_pesquisa(logger)
        logger.info(
            "Total de datas a processar: %s",
            len(datas)
        )

        termos = obter_termos_pesquisa()

        if not termos:
            logger.info(
                "Nenhum termo de pesquisa configurado no .env. "
                "Apenas download e processamento serao realizados."
            )

        for data in datas:
            data_str = data.date().isoformat()
            logger.info(
                "=" * 60
            )
            logger.info("Processando data: %s", data_str)
            logger.info(
                "=" * 60
            )

            try:
                resultado = executar_download(data, logger)

                if resultado is None:
                    logger.info(
                        "Nenhum PDF disponivel para %s. Pulando.",
                        data_str
                    )
                    continue

                caminho_pdf, url_download = resultado

                extracao = executar_extracao(
                    caminho_pdf=caminho_pdf,
                    logger=logger
                )

                artefatos_proc = executar_processamento(
                    caminho_pdf=caminho_pdf,
                    paginas=extracao["paginas"],
                    logger=logger
                )

                if termos and artefatos_proc.get("documento"):
                    resultados_data = pesquisar_termos_arquivo(
                        caminho_json=artefatos_proc["documento"],
                        termos=termos
                    )

                    for r in resultados_data:
                        r["data"] = data_str
                        r["url_download"] = url_download

                    resultados_consolidados.extend(resultados_data)

                    logger.info(
                        "Resultados encontrados para %s: %s",
                        data_str,
                        len(resultados_data)
                    )

                datas_processadas += 1

            except Exception as erro:
                logger.exception(
                    "Erro ao processar data %s: %s",
                    data_str,
                    erro
                )
                datas_com_erro += 1
                continue

        logger.info(
            "Processamento concluido. "
            "Datas processadas: %s | Erros: %s",
            datas_processadas,
            datas_com_erro
        )

        artefatos["datas_processadas"] = datas_processadas
        artefatos["datas_com_erro"] = datas_com_erro
        artefatos["total_resultados_pesquisa"] = len(resultados_consolidados)

        if resultados_consolidados:
            exibir_resultados(resultados_consolidados)

            caminho_resultado = salvar_resultados_pesquisa(
                pasta_resultados=PASTA_RESULTADOS,
                resultados=resultados_consolidados,
                termos=termos
            )

            logger.info(
                "Resultado da pesquisa salvo em: %s",
                caminho_resultado
            )

            artefatos["pesquisa"] = caminho_resultado

            alerta = executar_alerta_email(
                resultados=resultados_consolidados,
                logger=logger
            )

            artefatos["email_enviado"] = alerta["email_enviado"]
        else:
            logger.info(
                "Nenhum resultado encontrado para os termos configurados."
            )
            artefatos["email_enviado"] = False

        logger.info("Resumo dos artefatos: %s", artefatos)
        logger.info("Robo Diario Oficial finalizado com sucesso.")

    except Exception as erro:
        logger.exception(
            "Erro durante execucao do robo: %s",
            erro
        )


if __name__ == "__main__":
    main()

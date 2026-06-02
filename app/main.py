from datetime import datetime
from app.baixar_pdf import baixar_pdf_diario
from app.config import DATA_TESTE, validar_configuracoes
from app.extrair_pdf import extrair_texto_completo, obter_total_paginas
from app.logger import configurar_logger
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


def main():
    logger = configurar_logger()

    try:
        validar_configuracoes()

        logger.info("Configuracoes carregadas com sucesso.")
        logger.info("Robo Diario Oficial iniciado.")

        data_referencia = obter_data_referencia(logger)

        caminho_pdf = baixar_pdf_diario(
            logger=logger,
            data_referencia=data_referencia
        )

        logger.info("PDF disponivel para processamento: %s", caminho_pdf)

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

        artefatos = processar_documento(
            caminho_pdf=caminho_pdf,
            paginas=paginas,
            logger=logger
        )

        logger.info("Arquivo bruto gerado: %s", artefatos["bruto"])
        logger.info("Documento JSON gerado: %s", artefatos["documento"])

        logger.info("Robo Diario Oficial finalizado com sucesso.")

    except Exception as erro:
        logger.exception("Erro durante execucao do robo: %s", erro)


if __name__ == "__main__":
    main()
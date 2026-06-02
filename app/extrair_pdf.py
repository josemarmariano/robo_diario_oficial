import fitz

def obter_total_paginas(caminho_pdf):
    with fitz.open(caminho_pdf) as documento:
        return documento.page_count


def extrair_texto_pagina(caminho_pdf, numero_pagina):
    with fitz.open(caminho_pdf) as documento:
        total_paginas = documento.page_count

        if numero_pagina < 1 or numero_pagina > total_paginas:
            raise ValueError(
                f"Pagina invalida: {numero_pagina}. "
                f"O PDF possui {total_paginas} paginas."
            )

        pagina = documento.load_page(numero_pagina - 1)
        texto = pagina.get_text("text")

        return texto.strip()


def extrair_texto_completo(caminho_pdf, logger=None):
    paginas_extraidas = []

    with fitz.open(caminho_pdf) as documento:
        total_paginas = documento.page_count

        if logger:
            logger.info("Iniciando extracao de texto do PDF.")
            logger.info("Total de paginas: %s", total_paginas)

        for indice in range(total_paginas):
            pagina = documento.load_page(indice)
            texto = pagina.get_text("text").strip()

            paginas_extraidas.append(
                {
                    "pagina": indice + 1,
                    "texto": texto,
                    "qtde_caracteres": len(texto)
                }
            )

            if logger:
                logger.info(
                    "Pagina %s extraida com %s caracteres.",
                    indice + 1,
                    len(texto)
                )

    if logger:
        logger.info("Extracao de texto finalizada.")

    return paginas_extraidas
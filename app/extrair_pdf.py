import io
import fitz
import pytesseract
from PIL import Image


LIMITE_MINIMO_CARACTERES_TEXTO = 300
ZOOM_OCR = 2


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


def pagina_possui_imagens(pagina):
    imagens = pagina.get_images(full=True)
    return len(imagens) > 0


def pagina_suspeita_para_ocr(texto, possui_imagens):
    texto = texto.strip()

    if not possui_imagens:
        return False

    if len(texto) < LIMITE_MINIMO_CARACTERES_TEXTO:
        return True

    return False


def converter_pagina_para_imagem(pagina):
    matriz = fitz.Matrix(ZOOM_OCR, ZOOM_OCR)
    pixmap = pagina.get_pixmap(matrix=matriz, alpha=False)

    imagem_bytes = pixmap.tobytes("png")
    imagem = Image.open(io.BytesIO(imagem_bytes))

    return imagem


def extrair_texto_ocr_pagina(pagina):
    imagem = converter_pagina_para_imagem(pagina)

    texto_ocr = pytesseract.image_to_string(
        imagem,
        lang="por"
    )

    return texto_ocr.strip()


def extrair_texto_completo(caminho_pdf, logger=None):
    paginas_extraidas = []

    with fitz.open(caminho_pdf) as documento:
        total_paginas = documento.page_count

        if logger:
            logger.info("Iniciando extracao de texto do PDF.")
            logger.info("Total de paginas: %s", total_paginas)

        for indice in range(total_paginas):
            numero_pagina = indice + 1
            pagina = documento.load_page(indice)

            texto_extraido = pagina.get_text("text").strip()
            possui_imagens = pagina_possui_imagens(pagina)
            necessita_ocr = pagina_suspeita_para_ocr(
                texto=texto_extraido,
                possui_imagens=possui_imagens
            )

            texto_final = texto_extraido
            origem_texto = "extracao_texto"

            if necessita_ocr:
                if logger:
                    logger.info(
                        "Pagina %s marcada como suspeita para OCR.",
                        numero_pagina
                    )

                try:
                    texto_ocr = extrair_texto_ocr_pagina(pagina)

                    if len(texto_ocr) > len(texto_extraido):
                        texto_final = texto_ocr
                        origem_texto = "ocr"

                        if logger:
                            logger.info(
                                "OCR aplicado na pagina %s com sucesso.",
                                numero_pagina
                            )
                    else:
                        if logger:
                            logger.info(
                                "OCR executado na pagina %s, mas texto original foi mantido.",
                                numero_pagina
                            )

                except Exception as erro:
                    if logger:
                        logger.exception(
                            "Erro ao executar OCR na pagina %s: %s",
                            numero_pagina,
                            erro
                        )

            paginas_extraidas.append(
                {
                    "pagina": numero_pagina,
                    "texto": texto_final,
                    "qtde_caracteres": len(texto_final),
                    "possui_imagens": possui_imagens,
                    "necessitou_ocr": origem_texto == "ocr",
                    "origem_texto": origem_texto
                }
            )

            if logger:
                logger.info(
                    "Pagina %s extraida com %s caracteres. Origem: %s. Possui imagens: %s.",
                    numero_pagina,
                    len(texto_final),
                    origem_texto,
                    possui_imagens
                )

    if logger:
        logger.info("Extracao de texto finalizada.")

    return paginas_extraidas
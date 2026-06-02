import json
import os
import re
import unicodedata
from datetime import datetime
from app.config import PASTA_RESULTADOS


def montar_nome_base(caminho_pdf):
    nome_pdf = os.path.basename(caminho_pdf)
    nome_base, _ = os.path.splitext(nome_pdf)
    return nome_base


def montar_caminho_saida(caminho_pdf, sufixo, extensao):
    os.makedirs(PASTA_RESULTADOS, exist_ok=True)

    nome_base = montar_nome_base(caminho_pdf)
    nome_arquivo = f"{nome_base}_{sufixo}.{extensao}"

    return os.path.join(PASTA_RESULTADOS, nome_arquivo)


def limpar_caracteres_invisiveis(texto):
    if texto is None:
        return ""

    substituicoes = {
        "\u00ad": "",
        "\ufeff": "",
        "\ufffe": "",
        "\xa0": " ",
    }

    for origem, destino in substituicoes.items():
        texto = texto.replace(origem, destino)

    texto = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", " ", texto)
    texto = re.sub(r"[\u200B-\u200F\u202A-\u202E\u2060-\u206F]", "", texto)

    return texto


def remover_cabecalhos_rodapes(texto):
    linhas = texto.splitlines()
    linhas_filtradas = []

    padroes_ignorar = [
        r"^Diário Oficial Eletrônico de Piracicaba",
        r"^Diário Oficial do Município de Piracicaba",
        r"^página\s+\d+$",
        r"^Página:\s*\d+$",
        r"^Para conferência, acesse o site",
        r"^Pág\.\s*\d+\s+de\s+\d+",
        r"^Peça do processo/documento",
    ]

    for linha in linhas:
        linha_limpa = linha.strip()
        ignorar = False

        for padrao in padroes_ignorar:
            if re.search(padrao, linha_limpa, flags=re.IGNORECASE):
                ignorar = True
                break

        if not ignorar:
            linhas_filtradas.append(linha)

    return "\n".join(linhas_filtradas)


def juntar_palavras_quebradas(texto):
    texto = re.sub(
        r"([A-Za-zÁÀÂÃÉÊÍÓÔÕÚÇáàâãéêíóôõúç])-\n([A-Za-zÁÀÂÃÉÊÍÓÔÕÚÇáàâãéêíóôõúç])",
        r"\1\2",
        texto,
    )

    texto = re.sub(
        r"([a-záàâãéêíóôõúç])\n([a-záàâãéêíóôõúç])",
        r"\1\2",
        texto,
    )

    return texto


def normalizar_espacos(texto):
    texto = re.sub(r"[ \t]+", " ", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    return texto.strip()


def normalizar_texto(texto):
    texto = limpar_caracteres_invisiveis(texto)
    texto = remover_cabecalhos_rodapes(texto)
    texto = juntar_palavras_quebradas(texto)
    texto = normalizar_espacos(texto)
    return texto


def normalizar_para_comparacao(texto):
    texto = limpar_caracteres_invisiveis(texto)
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(
        caractere for caractere in texto
        if unicodedata.category(caractere) != "Mn"
    )
    texto = texto.upper()
    texto = re.sub(r"\s+", " ", texto)
    texto = texto.strip()

    return texto


def limpar_linha_sumario(linha):
    linha = limpar_caracteres_invisiveis(linha)
    linha = re.sub(r"[ \t]+", " ", linha)
    return linha.strip()


def linha_eh_numero_pagina(linha):
    return bool(re.fullmatch(r"\d+", linha.strip()))


def extrair_item_sumario_mesma_linha(linha):
    linha = limpar_linha_sumario(linha)

    match = re.match(r"^(?P<secao>.+?)\s+(?P<pagina>\d+)$", linha)

    if not match:
        return None

    secao = match.group("secao").strip()
    pagina = int(match.group("pagina"))

    if len(secao) < 3:
        return None

    return {
        "secao": secao,
        "pagina_inicial": pagina
    }


def salvar_bruto(caminho_pdf, paginas):
    caminho_bruto = montar_caminho_saida(caminho_pdf, "01_bruto", "txt")

    with open(caminho_bruto, "w", encoding="utf-8") as arquivo:
        for pagina in paginas:
            arquivo.write("=" * 80)
            arquivo.write(f"\nPAGINA {pagina['pagina']}\n")
            arquivo.write("=" * 80)
            arquivo.write("\n\n")
            arquivo.write(pagina["texto"])
            arquivo.write("\n\n")

    return caminho_bruto


def extrair_sumario(paginas):
    if not paginas:
        return []

    texto_primeira_pagina = limpar_caracteres_invisiveis(paginas[0]["texto"])
    linhas = texto_primeira_pagina.splitlines()

    sumario = []
    secoes_capturadas = set()
    lendo_sumario = False
    indice = 0

    while indice < len(linhas):
        linha_atual = limpar_linha_sumario(linhas[indice])

        if not lendo_sumario:
            if linha_atual.lower() == "seções":
                lendo_sumario = True

            indice += 1
            continue

        if not linha_atual:
            indice += 1
            continue

        if sumario and linha_atual.upper() in secoes_capturadas:
            break

        item_mesma_linha = extrair_item_sumario_mesma_linha(linha_atual)

        if item_mesma_linha:
            sumario.append(item_mesma_linha)
            secoes_capturadas.add(item_mesma_linha["secao"].upper())

            indice += 1
            continue

        proximo_indice = indice + 1

        while proximo_indice < len(linhas):
            proxima_linha = limpar_linha_sumario(linhas[proximo_indice])

            if proxima_linha:
                break

            proximo_indice += 1

        if proximo_indice < len(linhas):
            proxima_linha = limpar_linha_sumario(linhas[proximo_indice])

            if linha_eh_numero_pagina(proxima_linha):
                item = {
                    "secao": linha_atual,
                    "pagina_inicial": int(proxima_linha)
                }

                sumario.append(item)
                secoes_capturadas.add(linha_atual.upper())

                indice = proximo_indice + 1
                continue

        if sumario:
            break

        indice += 1

    return calcular_paginas_finais_sumario(sumario, len(paginas))


def calcular_paginas_finais_sumario(sumario, total_paginas):
    if not sumario:
        return []

    for indice, item in enumerate(sumario):
        if indice < len(sumario) - 1:
            proxima_pagina = sumario[indice + 1]["pagina_inicial"]
            item["pagina_final"] = max(item["pagina_inicial"], proxima_pagina - 1)
        else:
            item["pagina_final"] = total_paginas

    return sumario


def eh_inicio_conteudo_real(linha):
    padroes = [
        r"^DECRETO\s+N[ºO]",
        r"^PORTARIA",
        r"^LEI\s+N[ºO]",
        r"^LEI COMPLEMENTAR\s+N[ºO]",
        r"^COMUNICADO",
        r"^AVISO DE LICITAÇÃO",
        r"^EDITAL",
        r"^TERMO DE",
        r"^ATA DE",
        r"^EXTRATO",
        r"^DISPENSA DE LICITAÇÃO",
        r"^NOTIFICAÇÃO",
    ]

    linha_limpa = linha.strip()

    for padrao in padroes:
        if re.search(padrao, linha_limpa, flags=re.IGNORECASE):
            return True

    return False


def remover_sumario_primeira_pagina(texto):
    linhas = texto.splitlines()
    indice_inicio_sumario = None

    for indice, linha in enumerate(linhas):
        if linha.strip().lower() == "seções":
            indice_inicio_sumario = indice
            break

    if indice_inicio_sumario is None:
        return texto

    indice_fim_sumario = None

    for indice in range(indice_inicio_sumario + 1, len(linhas)):
        linha_limpa = limpar_linha_sumario(linhas[indice])

        if eh_inicio_conteudo_real(linha_limpa):
            indice_fim_sumario = indice
            break

    if indice_fim_sumario is None:
        linhas_resultado = linhas[:indice_inicio_sumario]
    else:
        linhas_resultado = (
            linhas[:indice_inicio_sumario]
            + linhas[indice_fim_sumario:]
        )

    return "\n".join(linhas_resultado)


def preparar_texto_pagina_para_json(pagina, remover_sumario=False):
    texto = pagina["texto"]

    if remover_sumario:
        texto = remover_sumario_primeira_pagina(texto)

    texto = normalizar_texto(texto)

    return texto


def montar_linhas_documento(paginas):
    linhas_documento = []

    for pagina in paginas:
        numero_pagina = pagina["pagina"]
        remover_sumario = numero_pagina == 1

        texto_normalizado = preparar_texto_pagina_para_json(
            pagina=pagina,
            remover_sumario=remover_sumario
        )

        for linha in texto_normalizado.splitlines():
            linha_limpa = linha.strip()

            if not linha_limpa:
                continue

            linhas_documento.append(
                {
                    "pagina": numero_pagina,
                    "texto": linha_limpa
                }
            )

    return linhas_documento


def combinar_linhas_para_comparacao(linhas_documento, indice_inicio, limite=3):
    partes = []
    indice = indice_inicio

    while indice < len(linhas_documento) and len(partes) < limite:
        texto = linhas_documento[indice]["texto"].strip()

        if texto:
            partes.append(texto)

        combinado = " ".join(partes)

        yield {
            "texto": combinado,
            "indice_fim": indice + 1
        }

        indice += 1


def localizar_titulo_secao(linhas_documento, titulo, pagina_minima, indice_minimo):
    titulo_comparacao = normalizar_para_comparacao(titulo)

    for indice in range(indice_minimo, len(linhas_documento)):
        linha = linhas_documento[indice]

        if linha["pagina"] < pagina_minima:
            continue

        for tentativa in combinar_linhas_para_comparacao(linhas_documento, indice):
            texto_comparacao = normalizar_para_comparacao(tentativa["texto"])

            if texto_comparacao == titulo_comparacao:
                return {
                    "indice_inicio": indice,
                    "indice_fim_titulo": tentativa["indice_fim"],
                    "pagina": linha["pagina"]
                }

    return None


def localizar_inicio_pagina(linhas_documento, pagina):
    for indice, linha in enumerate(linhas_documento):
        if linha["pagina"] >= pagina:
            return indice

    return len(linhas_documento)


def localizar_fim_pagina(linhas_documento, pagina):
    ultimo_indice = len(linhas_documento)

    for indice, linha in enumerate(linhas_documento):
        if linha["pagina"] > pagina:
            return indice

    return ultimo_indice


def localizar_posicoes_secoes(sumario, linhas_documento):
    posicoes = []
    indice_busca = 0

    for item in sumario:
        posicao = localizar_titulo_secao(
            linhas_documento=linhas_documento,
            titulo=item["secao"],
            pagina_minima=item["pagina_inicial"],
            indice_minimo=indice_busca
        )

        if posicao is None:
            indice_inicio = localizar_inicio_pagina(
                linhas_documento,
                item["pagina_inicial"]
            )

            posicao = {
                "indice_inicio": indice_inicio,
                "indice_fim_titulo": indice_inicio,
                "pagina": item["pagina_inicial"],
                "localizado_por_titulo": False
            }
        else:
            posicao["localizado_por_titulo"] = True

        posicao["secao"] = item["secao"]
        posicao["pagina_inicial_sumario"] = item["pagina_inicial"]
        posicao["pagina_final_sumario"] = item["pagina_final"]

        posicoes.append(posicao)

        indice_busca = max(posicao["indice_inicio"] + 1, indice_busca + 1)

    return posicoes


def agrupar_linhas_por_pagina(linhas, paginas_origem):
    paginas = {}
    imagens_por_pagina = {}

    for pagina_origem in paginas_origem:
        imagens_por_pagina[pagina_origem["pagina"]] = (
            pagina_origem.get("possui_imagem", False)
        )

    for linha in linhas:
        numero_pagina = linha["pagina"]

        if numero_pagina not in paginas:
            paginas[numero_pagina] = []

        paginas[numero_pagina].append(linha["texto"])

    resultado = []

    for numero_pagina in sorted(paginas):
        texto = "\n".join(
            paginas[numero_pagina]
        ).strip()

        resultado.append(
            {
                "pagina": numero_pagina,
                "texto": texto,
                "possui_imagem": imagens_por_pagina.get(
                    numero_pagina,
                    False
                )
            }
        )

    return resultado


def montar_secoes(sumario, paginas):
    linhas_documento = montar_linhas_documento(paginas)
    posicoes = localizar_posicoes_secoes(sumario, linhas_documento)

    secoes = []

    for indice, item in enumerate(posicoes):
        indice_inicio = item["indice_inicio"]

        if indice < len(posicoes) - 1:
            indice_fim = posicoes[indice + 1]["indice_inicio"]
        else:
            indice_fim = len(linhas_documento)

        linhas_secao = linhas_documento[indice_inicio:indice_fim]

        paginas_secao = agrupar_linhas_por_pagina(
            linhas_secao,
            paginas
        )        

        if paginas_secao:
            pagina_inicial = paginas_secao[0]["pagina"]
            pagina_final = paginas_secao[-1]["pagina"]
        else:
            pagina_inicial = item["pagina_inicial_sumario"]
            pagina_final = item["pagina_final_sumario"]

        secoes.append(
            {
                "secao": item["secao"],
                "pagina_inicial": pagina_inicial,
                "pagina_final": pagina_final,
                "paginas": paginas_secao,
            }
        )

    return secoes


def montar_documento_json(caminho_pdf, paginas):
    sumario = extrair_sumario(paginas)
    secoes = montar_secoes(sumario, paginas)

    return {
        "arquivo_origem": os.path.basename(caminho_pdf),
        "data_processamento": datetime.now().isoformat(timespec="seconds"),
        "total_paginas": len(paginas),
        "sumario": sumario,
        "secoes": secoes
    }


def salvar_documento_json(caminho_pdf, paginas):
    caminho_documento = montar_caminho_saida(
        caminho_pdf,
        "02_documento",
        "json"
    )

    documento = montar_documento_json(
        caminho_pdf=caminho_pdf,
        paginas=paginas
    )

    with open(caminho_documento, "w", encoding="utf-8") as arquivo:
        json.dump(
            documento,
            arquivo,
            ensure_ascii=False,
            indent=2
        )

    return caminho_documento


def processar_documento(caminho_pdf, paginas, logger=None):
    caminho_bruto = salvar_bruto(
        caminho_pdf=caminho_pdf,
        paginas=paginas
    )

    caminho_documento = salvar_documento_json(
        caminho_pdf=caminho_pdf,
        paginas=paginas
    )

    if logger:
        logger.info("Arquivo bruto salvo em: %s", caminho_bruto)
        logger.info("Documento JSON salvo em: %s", caminho_documento)

    return {
        "bruto": caminho_bruto,
        "documento": caminho_documento
    }
import json
import os
import re
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


def obter_texto_paginas_por_intervalo(paginas, pagina_inicial, pagina_final):
    textos = []

    for pagina in paginas:
        numero_pagina = pagina["pagina"]

        if pagina_inicial <= numero_pagina <= pagina_final:
            texto_bruto = pagina["texto"]
            texto_normalizado = normalizar_texto(texto_bruto)

            textos.append(
                {
                    "pagina": numero_pagina,
                    "texto_bruto": texto_bruto,
                    "texto_normalizado": texto_normalizado,
                    "qtde_caracteres_bruto": len(texto_bruto),
                    "qtde_caracteres_normalizado": len(texto_normalizado)
                }
            )

    return textos


def montar_secoes(sumario, paginas):
    secoes = []

    for item in sumario:
        paginas_secao = obter_texto_paginas_por_intervalo(
            paginas=paginas,
            pagina_inicial=item["pagina_inicial"],
            pagina_final=item["pagina_final"]
        )

        texto_normalizado_secao = "\n\n".join(
            pagina["texto_normalizado"] for pagina in paginas_secao
        ).strip()

        secoes.append(
            {
                "secao": item["secao"],
                "pagina_inicial": item["pagina_inicial"],
                "pagina_final": item["pagina_final"],
                "qtde_paginas": len(paginas_secao),
                "qtde_caracteres_normalizado": len(texto_normalizado_secao),
                "paginas": paginas_secao,
                "texto_normalizado": texto_normalizado_secao
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
        "sumario_extraido": bool(sumario),
        "total_itens_sumario": len(sumario),
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
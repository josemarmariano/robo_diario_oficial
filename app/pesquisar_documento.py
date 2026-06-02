import json
import os
import re
import unicodedata
from datetime import datetime


def carregar_documento_json(caminho_json):
    with open(caminho_json, "r", encoding="utf-8") as arquivo:
        return json.load(arquivo)


def normalizar_texto(texto):
    if texto is None:
        return ""

    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(
        caractere for caractere in texto
        if unicodedata.category(caractere) != "Mn"
    )

    texto = texto.lower()
    texto = re.sub(r"\s+", " ", texto)
    texto = texto.strip()

    return texto


def listar_arquivos_json(pasta_resultados):
    arquivos_json = []

    if not os.path.exists(pasta_resultados):
        return arquivos_json

    for nome_arquivo in sorted(os.listdir(pasta_resultados)):
        nome_lower = nome_arquivo.lower()

        if not nome_lower.endswith(".json"):
            continue

        if nome_lower.startswith("resultado_pesquisa_"):
            continue

        caminho_arquivo = os.path.join(pasta_resultados, nome_arquivo)
        arquivos_json.append(caminho_arquivo)

    return arquivos_json


def montar_regex_termo(termo):
    termo_normalizado = normalizar_texto(termo)

    if not termo_normalizado:
        return None

    return re.compile(
        rf"\b{re.escape(termo_normalizado)}\b",
        flags=re.IGNORECASE
    )


def encontrar_ocorrencias(texto, termo):
    texto_normalizado = normalizar_texto(texto)
    regex = montar_regex_termo(termo)

    if regex is None:
        return []

    return list(regex.finditer(texto_normalizado))


def extrair_trechos(texto, termo, tamanho_contexto=180):
    texto_normalizado = normalizar_texto(texto)
    regex = montar_regex_termo(termo)

    if regex is None:
        return []

    trechos = []

    for match in regex.finditer(texto_normalizado):
        inicio = max(0, match.start() - tamanho_contexto)
        fim = min(len(texto_normalizado), match.end() + tamanho_contexto)

        trecho = texto_normalizado[inicio:fim].strip()

        if inicio > 0:
            trecho = f"...{trecho}"

        if fim < len(texto_normalizado):
            trecho = f"{trecho}..."

        trechos.append(trecho)

    return trechos


def pesquisar_termo_documento(documento, termo):
    resultados = []

    arquivo_origem = documento.get("arquivo_origem", "")
    secoes = documento.get("secoes", [])

    for secao in secoes:
        nome_secao = secao.get("secao", "")
        paginas = secao.get("paginas", [])

        for pagina in paginas:
            numero_pagina = pagina.get("pagina")
            texto = pagina.get("texto", "")
            possui_imagem = pagina.get("possui_imagem", False)

            ocorrencias_encontradas = encontrar_ocorrencias(
                texto=texto,
                termo=termo
            )

            total_ocorrencias = len(ocorrencias_encontradas)

            if total_ocorrencias == 0:
                continue

            resultados.append(
                {
                    "termo": termo,
                    "arquivo": arquivo_origem,
                    "secao": nome_secao,
                    "pagina": numero_pagina,
                    "ocorrencias": total_ocorrencias,
                    "possui_imagem": possui_imagem,
                    "trechos": extrair_trechos(
                        texto=texto,
                        termo=termo
                    )
                }
            )

    return resultados


def pesquisar_termos_documento(documento, termos):
    resultados = []

    for termo in termos:
        resultados.extend(
            pesquisar_termo_documento(
                documento=documento,
                termo=termo
            )
        )

    return resultados


def pesquisar_termos_arquivo(caminho_json, termos):
    documento = carregar_documento_json(caminho_json)

    return pesquisar_termos_documento(
        documento=documento,
        termos=termos
    )


def pesquisar_termos_pasta(pasta_resultados, termos, logger=None):
    resultados = []
    arquivos_json = listar_arquivos_json(pasta_resultados)

    if logger:
        logger.info(
            "Arquivos JSON encontrados para pesquisa: %s",
            len(arquivos_json)
        )

    for caminho_json in arquivos_json:
        try:
            resultados_arquivo = pesquisar_termos_arquivo(
                caminho_json=caminho_json,
                termos=termos
            )

            resultados.extend(resultados_arquivo)

            if logger:
                logger.info(
                    "Pesquisa realizada no arquivo %s. Resultados: %s",
                    caminho_json,
                    len(resultados_arquivo)
                )

        except Exception as erro:
            if logger:
                logger.exception(
                    "Erro ao pesquisar no arquivo %s: %s",
                    caminho_json,
                    erro
                )

    return resultados


def montar_documento_resultado_pesquisa(resultados, termos):
    return {
        "data_processamento": datetime.now().isoformat(timespec="seconds"),
        "termos_pesquisados": termos,
        "total_resultados": len(resultados),
        "resultados": resultados
    }


def salvar_resultados_pesquisa(pasta_resultados, resultados, termos):
    documento_resultado = montar_documento_resultado_pesquisa(
        resultados=resultados,
        termos=termos
    )

    data_arquivo = datetime.now().strftime("%Y%m%d")
    nome_arquivo = f"resultado_pesquisa_{data_arquivo}.json"

    caminho_saida = os.path.join(
        pasta_resultados,
        nome_arquivo
    )

    with open(caminho_saida, "w", encoding="utf-8") as arquivo:
        json.dump(
            documento_resultado,
            arquivo,
            ensure_ascii=False,
            indent=2
        )

    return caminho_saida


def exibir_resultados(resultados):
    if not resultados:
        print("Nenhuma ocorrencia encontrada.")
        return

    print(f"Total de resultados encontrados: {len(resultados)}")
    print("-" * 80)

    for indice, resultado in enumerate(resultados, start=1):
        print(f"Resultado {indice}")
        print(f"Termo: {resultado['termo']}")
        print(f"Arquivo: {resultado['arquivo']}")
        print(f"Secao: {resultado['secao']}")
        print(f"Pagina: {resultado['pagina']}")
        print(f"Ocorrencias: {resultado['ocorrencias']}")
        print(f"Possui imagem: {resultado['possui_imagem']}")
        print("-" * 80)
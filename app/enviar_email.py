import smtplib
from email.message import EmailMessage

from app.config import (
    EMAIL_ATIVO,
    EMAIL_REMETENTE,
    EMAIL_SENHA_APP,
    EMAIL_SMTP_PORTA,
    EMAIL_SMTP_SERVIDOR,
    obter_destinatarios_email
)


def montar_assunto_email(resultados):
    total_resultados = len(resultados)

    if total_resultados == 1:
        return "Alerta - Diário Oficial Piracicaba - Ocorrência Encontrada"

    return "Alerta - Diário Oficial Piracicaba - Ocorrências Encontradas"


def montar_corpo_email(resultados,termos):
    from collections import defaultdict

    linhas = []

    linhas.append("Alerta do Robo Diario Oficial")
    linhas.append("")
    linhas.append(f"Termo(s) procurado(s): {termos}")
    linhas.append("")
    linhas.append(f"Total de resultados encontrados: {len(resultados)}")
    linhas.append("")

    por_data = defaultdict(list)
    for r in resultados:
        por_data[r.get("data", "")].append(r)

    for data in sorted(por_data):
        items = por_data[data]

        linhas.append("=" * 80)
        linhas.append(f"Data: {data} ({len(items)} ocorrencia{'s' if len(items) > 1 else ''})")
        linhas.append("=" * 80)
        linhas.append("")

        por_secao = defaultdict(list)
        for r in items:
            por_secao[r.get("secao", "Sem secao")].append(r)

        for secao, items_secao in sorted(por_secao.items()):
            linhas.append(f"--- Secao: {secao} ---")
            linhas.append("")

            for resultado in items_secao:
                linhas.append(f"Termo: {resultado.get('termo', '')}")
                linhas.append(f"Arquivo: {resultado.get('arquivo', '')}")
                linhas.append(f"Pagina: {resultado.get('pagina', '')}")
                linhas.append(f"Ocorrencias: {resultado.get('ocorrencias', 0)}")
                linhas.append(f"URL: {resultado.get('url_download', '')}")

                trechos = resultado.get("trechos", [])

                if trechos:
                    linhas.append("Trecho:")
                    linhas.append(f"  {trechos[0]}")

                linhas.append("")

        linhas.append("")

    linhas.append("-" * 80)
    linhas.append("Fim do alerta.")

    return "\n".join(linhas)


def enviar_email_alerta(resultados, logger=None, termos=None):
    if not EMAIL_ATIVO:
        if logger:
            logger.info("Envio de e-mail desativado.")
        return False

    if not resultados:
        if logger:
            logger.info("Nenhum resultado encontrado. E-mail nao enviado.")
        return False

    destinatarios = obter_destinatarios_email()

    assunto = montar_assunto_email(resultados)
    corpo = montar_corpo_email(resultados, termos)

    mensagem = EmailMessage()
    mensagem["From"] = EMAIL_REMETENTE
    mensagem["To"] = ", ".join(destinatarios)
    mensagem["Subject"] = assunto
    mensagem.set_content(corpo)

    try:
        with smtplib.SMTP(
            EMAIL_SMTP_SERVIDOR,
            EMAIL_SMTP_PORTA
        ) as servidor:
            servidor.starttls()
            servidor.login(
                EMAIL_REMETENTE,
                EMAIL_SENHA_APP
            )
            servidor.send_message(mensagem)

        if logger:
            logger.info(
                "E-mail de alerta enviado para: %s",
                destinatarios
            )

        return True

    except Exception as erro:
        if logger:
            logger.exception(
                "Erro ao enviar e-mail de alerta: %s",
                erro
            )

        raise
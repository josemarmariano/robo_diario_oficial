import logging
import os
from logging.handlers import RotatingFileHandler

from app.config import PASTA_LOGS


def configurar_logger():
    os.makedirs(PASTA_LOGS, exist_ok=True)

    caminho_log = os.path.join(PASTA_LOGS, "robo_diario_oficial.log")

    logger = logging.getLogger("robo_diario_oficial")
    logger.setLevel(logging.INFO)

    if logger.handlers:
        return logger

    formato = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    arquivo_handler = RotatingFileHandler(
        caminho_log,
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8"
    )
    arquivo_handler.setFormatter(formato)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formato)

    logger.addHandler(arquivo_handler)
    logger.addHandler(console_handler)

    return logger
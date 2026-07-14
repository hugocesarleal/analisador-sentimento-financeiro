import logging
import os

from config import PASTA_BASE

_CONFIGURADO = False


def _configurar_uma_vez():
    """Configura o logging na primeira vez que for necessário. Escreve tanto
    no console (avisos e erros, pra visibilidade imediata) quanto num arquivo
    persistente (todos os níveis, pra investigação posterior de falhas que
    aconteceram durante um lote longo e já saíram da tela)."""
    global _CONFIGURADO

    if _CONFIGURADO:
        return

    os.makedirs(PASTA_BASE, exist_ok=True)
    caminho_log = os.path.join(PASTA_BASE, "pipeline.log")

    logger_raiz = logging.getLogger("analisador_sentimento")
    logger_raiz.setLevel(logging.INFO)

    if not logger_raiz.handlers:
        formato = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

        handler_arquivo = logging.FileHandler(caminho_log, encoding="utf-8")
        handler_arquivo.setLevel(logging.INFO)
        handler_arquivo.setFormatter(formato)
        logger_raiz.addHandler(handler_arquivo)

    _CONFIGURADO = True


def obter_logger(nome: str) -> logging.Logger:
    """Retorna um logger nomeado (use `obter_logger(__name__)` em cada
    módulo), já configurado para persistir em `base_dados/pipeline.log`.

    Isso substitui falhas que hoje são só engolidas silenciosamente (ex:
    tradução que falha e cai de volta pro texto original sem deixar rastro)
    por um registro persistente — útil pra auditar, depois de um lote
    longo, quantas vezes e por quê algo deu errado no meio do caminho.
    """
    _configurar_uma_vez()
    return logging.getLogger(f"analisador_sentimento.{nome}")

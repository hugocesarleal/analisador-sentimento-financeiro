import uuid
from datetime import datetime
from importlib.metadata import version, PackageNotFoundError

from config import QUANTIDADE_NOTICIAS, LIMIAR_RECOMENDACAO
from base_dados import salvar_execucao


def gerar_run_id() -> str:
    """Gera um identificador único e ordenável cronologicamente para UMA
    execução (uma análise atual, um backtesting manual, ou um lote inteiro).

    Formato: AAAAMMDD_HHMMSS_xxxxxxxx — o prefixo de data/hora permite ordenar
    execuções cronologicamente só de bater o olho no CSV, e o sufixo aleatório
    evita colisão entre execuções disparadas no mesmo segundo.
    """
    return f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"


def _versao_pacote(nome: str) -> str:
    try:
        return version(nome)
    except PackageNotFoundError:
        return "desconhecida"


def capturar_metadados_ambiente() -> dict:
    """Versões das bibliotecas relevantes, capturadas em tempo de execução.

    Isso importa porque a tradução (Google Translate, via deep_translator) e
    os modelos de NLP podem se comportar de forma diferente entre versões
    das bibliotecas, mesmo sem nenhuma mudança no nosso código — então saber
    a versão exata usada em cada execução é parte da reprodutibilidade.
    """
    return {
        "versao_transformers": _versao_pacote("transformers"),
        "versao_torch": _versao_pacote("torch"),
        "versao_pysentimiento": _versao_pacote("pysentimiento"),
        "versao_deep_translator": _versao_pacote("deep-translator"),
        "versao_yfinance": _versao_pacote("yfinance"),
        "versao_feedparser": _versao_pacote("feedparser"),
    }


def registrar_execucao(
    run_id: str,
    tipo_execucao: str,
    usar_comparativo: bool,
    parametros_extra: dict | None = None
) -> dict:
    """Registra os metadados de UMA execução: qual config estava ativa, quais
    versões de bibliotecas/modelos foram usadas, timestamp.

    Deve ser chamado UMA vez por execução — uma vez por análise atual, uma
    vez por backtesting manual, ou uma vez por LOTE INTEIRO (não uma vez por
    janela dentro do lote, já que todas as janelas de um mesmo lote
    compartilham a mesma configuração e o mesmo run_id).

    É isso que permite, meses depois, reconstruir com qual configuração e
    quais versões de modelo um determinado resultado no CSV foi gerado —
    essencial pra reprodutibilidade num artigo científico.
    """
    linha = {
        "run_id": run_id,
        "tipo_execucao": tipo_execucao,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "usar_comparativo": usar_comparativo,
        "modelo_finbert": "ProsusAI/finbert",
        "modelo_pysentimiento": "pysentimiento (lang=pt)" if usar_comparativo else None,
        "quantidade_noticias": QUANTIDADE_NOTICIAS,
        "limiar_recomendacao": LIMIAR_RECOMENDACAO,
        **capturar_metadados_ambiente(),
        **(parametros_extra or {})
    }

    salvar_execucao(linha)

    return linha

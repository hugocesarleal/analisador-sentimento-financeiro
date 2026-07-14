from deep_translator import GoogleTranslator
from config import LIMIAR_RECOMENDACAO
from cache_traducao import obter_traducao_cacheada, salvar_traducao_no_cache
from logging_config import obter_logger

logger = obter_logger(__name__)


def traduzir_para_ingles(texto: str) -> str:
    """Traduz um texto de português para inglês.

    Usa um cache local em disco (`cache_traducao.py`) por dois motivos:
    1) REPRODUTIBILIDADE — rodar o mesmo experimento duas vezes deve produzir
       exatamente a mesma tradução, mesmo que o comportamento do Google
       Translate mude entre as duas execuções (é um serviço externo, fora do
       nosso controle de versionamento).
    2) PERFORMANCE — manchetes se repetem entre janelas de tempo vizinhas
       (a mesma notícia pode aparecer em buscas de semanas diferentes), então
       o cache reduz bastante o número de chamadas externas em experimentos
       em lote.
    """
    traducao_cacheada = obter_traducao_cacheada(texto)

    if traducao_cacheada is not None:
        return traducao_cacheada

    try:
        traducao = GoogleTranslator(source="pt", target="en").translate(texto)
    except Exception as e:
        logger.warning(f"Falha ao traduzir texto (usando original, sem tradução): {texto!r} — {e}")
        traducao = texto

    salvar_traducao_no_cache(texto, traducao)
    return traducao


def analisar_finbert(texto_en: str, finbert_pipeline) -> dict:
    resultado = finbert_pipeline(texto_en, truncation=True, max_length=512)[0]
    return resultado


def analisar_pysentimiento(texto_pt: str, analyzer) -> dict:
    res = analyzer.predict(texto_pt)

    return {
        "label": res.output,
        "pos": res.probas.get("POS", 0.0),
        "neg": res.probas.get("NEG", 0.0),
        "neu": res.probas.get("NEU", 0.0),
    }


def calcular_score_individual_finbert(resultado_finbert: dict) -> float:
    label = resultado_finbert["label"].lower()
    score = resultado_finbert["score"]

    if label == "positive":
        return score
    elif label == "negative":
        return -score
    else:
        return 0.0


def calcular_score_individual_pysentimiento(resultado_py: dict | None) -> float | None:
    if resultado_py is None:
        return None

    return resultado_py["pos"] - resultado_py["neg"]


def calcular_score_finbert(resultados_finbert: list[dict]) -> float:
    if not resultados_finbert:
        return 0.0

    total = 0.0

    for resultado in resultados_finbert:
        total += calcular_score_individual_finbert(resultado)

    return total / len(resultados_finbert)


def calcular_score_pysentimiento(resultados_py: list[dict]) -> float:
    if not resultados_py:
        return 0.0

    total = 0.0

    for resultado in resultados_py:
        total += resultado["pos"] - resultado["neg"]

    return total / len(resultados_py)


def score_para_recomendacao(score: float, limiar: float = LIMIAR_RECOMENDACAO) -> str:
    if score > limiar:
        return "COMPRAR"
    elif score < -limiar:
        return "VENDER"
    else:
        return "NEUTRO / AGUARDAR"

from deep_translator import GoogleTranslator
from config import LIMIAR_RECOMENDACAO


def traduzir_para_ingles(texto: str) -> str:
    try:
        return GoogleTranslator(source="pt", target="en").translate(texto)
    except Exception:
        return texto


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
from transformers import pipeline
from pysentimiento import create_analyzer


def carregar_modelos(usar_comparativo: bool):
    """Carrega os modelos de NLP conforme o modo selecionado."""
    modelos = {}

    print("\n[1/2] Carregando FinBERT (ProsusAI)...")
    modelos["finbert"] = pipeline("sentiment-analysis", model="ProsusAI/finbert")
    print("      FinBERT carregado!")

    if usar_comparativo:
        print("[2/2] Carregando PySentimiento (pt-BR)...")
        modelos["pysentimiento"] = create_analyzer(task="sentiment", lang="pt")
        print("      PySentimiento carregado!")
    else:
        print("[2/2] Modo comparativo DESATIVADO — PySentimiento não será carregado.")

    print("\nModelos prontos.\n")
    return modelos

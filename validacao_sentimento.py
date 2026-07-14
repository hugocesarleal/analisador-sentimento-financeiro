import os
import pandas as pd

from config import PASTA_BASE, LIMIAR_CONFIANCA_BAIXA

MAPA_FINBERT = {"positive": "POS", "negative": "NEG", "neutral": "NEU"}


def _normalizar_label_finbert(label: str) -> str:
    """Converte os rótulos do FinBERT (positive/negative/neutral) para o
    mesmo alfabeto de 3 letras usado pelo PySentimiento (POS/NEG/NEU), pra
    poder comparar os dois diretamente."""
    return MAPA_FINBERT.get(str(label).lower(), str(label).upper())


def _cohen_kappa(rotulos_a: pd.Series, rotulos_b: pd.Series) -> float:
    """Calcula o coeficiente Kappa de Cohen entre dois conjuntos de rótulos
    categóricos pareados, sem depender do scikit-learn.

    Kappa corrige a taxa de concordância bruta pela concordância esperada
    só por acaso — é por isso que é preferível a simplesmente reportar
    '% de concordância', que infla a percepção de confiabilidade quando uma
    categoria (ex: NEUTRO) domina a amostra.
    """
    n = len(rotulos_a)
    if n == 0:
        return float("nan")

    p_o = (rotulos_a.values == rotulos_b.values).mean()

    categorias = sorted(set(rotulos_a) | set(rotulos_b))
    p_e = 0.0
    for cat in categorias:
        p_a = (rotulos_a == cat).mean()
        p_b = (rotulos_b == cat).mean()
        p_e += p_a * p_b

    if p_e >= 1.0:
        return 1.0

    return (p_o - p_e) / (1 - p_e)


def _interpretar_kappa(kappa: float) -> str:
    """Interpretação convencional da magnitude do Kappa (Landis & Koch, 1977)."""
    if pd.isna(kappa):
        return "não calculável"
    elif kappa < 0:
        return "concordância pior que o acaso"
    elif kappa < 0.20:
        return "concordância insignificante"
    elif kappa < 0.40:
        return "concordância fraca"
    elif kappa < 0.60:
        return "concordância moderada"
    elif kappa < 0.80:
        return "concordância substancial"
    else:
        return "concordância quase perfeita"


def gerar_relatorio_concordancia(nome_arquivo: str = "base_noticias_sentimento.csv") -> dict | None:
    """Gera um relatório de confiabilidade AUTOMÁTICA do sentimento extraído,
    baseado em duas fontes que NÃO exigem rótulo humano:

    1. Concordância entre FinBERT e PySentimiento nas mesmas notícias
       (taxa de concordância bruta + Kappa de Cohen + matriz de confusão);
    2. Distribuição de confiança do FinBERT (média e % de classificações
       de baixa confiança).

    LIMITAÇÃO IMPORTANTE, que deve constar no artigo: concordância entre
    dois modelos não prova que ambos estão certos — só que são consistentes
    entre si. Os dois modelos podem compartilhar o mesmo viés (por exemplo,
    ambos classificando mal o mesmo tipo de manchete ambígua) e ainda assim
    concordar. Isso é uma medida indireta e mais fraca de confiabilidade do
    que validação contra um gabarito humano — mas é o que temos disponível
    sem rotulagem manual.
    """
    caminho = os.path.join(PASTA_BASE, nome_arquivo)

    if not os.path.exists(caminho):
        print(f"⚠️  Arquivo não encontrado: {caminho}")
        return None

    df = pd.read_csv(caminho, encoding="utf-8-sig")

    if "sentimento_pysentimiento" not in df.columns:
        print("⚠️  A base não tem a coluna 'sentimento_pysentimiento' — "
              "parece que nenhuma execução rodou em modo comparativo ainda.")
        return None

    df_comp = df[df["sentimento_pysentimiento"].notna()].copy()

    if df_comp.empty:
        print("⚠️  Nenhuma linha com os dois modelos rodados (modo comparativo) foi encontrada.")
        return None

    df_comp["finbert_norm"] = df_comp["sentimento_finbert"].apply(_normalizar_label_finbert)
    df_comp["pysentimiento_norm"] = df_comp["sentimento_pysentimiento"].astype(str).str.upper()

    concordancia = (df_comp["finbert_norm"] == df_comp["pysentimiento_norm"]).mean()
    kappa = _cohen_kappa(df_comp["finbert_norm"], df_comp["pysentimiento_norm"])

    matriz_confusao = pd.crosstab(
        df_comp["finbert_norm"], df_comp["pysentimiento_norm"],
        rownames=["FinBERT"], colnames=["PySentimiento"]
    )

    confianca_media = df_comp["confianca_finbert"].mean()
    confianca_baixa_pct = (df_comp["confianca_finbert"] < LIMIAR_CONFIANCA_BAIXA).mean() * 100

    print("═" * 70)
    print("  RELATÓRIO DE CONFIABILIDADE AUTOMÁTICA (sem gabarito humano)")
    print("═" * 70)
    print(f"  Notícias analisadas (modo comparativo) : {len(df_comp)}")
    print(f"  Concordância FinBERT x PySentimiento    : {100 * concordancia:.1f}%")
    print(f"  Kappa de Cohen                          : {kappa:.3f} ({_interpretar_kappa(kappa)})")
    print(f"  Confiança média do FinBERT               : {confianca_media:.3f}")
    print(f"  % de classificações com confiança < {LIMIAR_CONFIANCA_BAIXA}  : {confianca_baixa_pct:.1f}%")
    print("─" * 70)
    print("  Matriz de confusão (linhas=FinBERT, colunas=PySentimiento):")
    print(matriz_confusao.to_string())
    print("═" * 70)
    print("  ⚠️  LIMITAÇÃO: isto mede CONCORDÂNCIA entre dois modelos, não")
    print("     ACURÁCIA contra um gabarito humano. Documentar isso no artigo.")
    print("═" * 70)

    return {
        "n_noticias_comparadas": len(df_comp),
        "concordancia_pct": concordancia * 100,
        "kappa_cohen": kappa,
        "interpretacao_kappa": _interpretar_kappa(kappa),
        "confianca_media_finbert": confianca_media,
        "pct_confianca_baixa": confianca_baixa_pct,
        "matriz_confusao": matriz_confusao
    }

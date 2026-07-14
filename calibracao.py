import numpy as np
import pandas as pd

from config import LIMIAR_RECOMENDACAO
from base_dados import carregar_base_backtesting


def _dividir_calibracao_teste(df: pd.DataFrame, coluna_data: str = "data_fim_noticias", proporcao_teste: float = 0.3):
    """Divide os dados CRONOLOGICAMENTE (não aleatoriamente) em calibração/teste.

    Uma divisão aleatória (como o train_test_split padrão) vazaria informação
    do futuro para o passado em dados de série temporal — durante a
    calibração, o limiar teria acesso indireto a exemplos de datas
    posteriores às que estamos tentando prever, inflando artificialmente o
    desempenho reportado. A divisão cronológica evita isso: só o período
    mais antigo é usado pra calibrar, e o período mais recente fica
    reservado como teste genuinamente não visto.
    """
    df = df.copy()
    df[coluna_data] = pd.to_datetime(df[coluna_data])
    df = df.sort_values(coluna_data).reset_index(drop=True)

    corte = int(len(df) * (1 - proporcao_teste))
    calibracao = df.iloc[:corte]
    teste = df.iloc[corte:]

    return calibracao, teste


def _score_para_recomendacao(score: float, limiar: float) -> str:
    if score > limiar:
        return "COMPRAR"
    elif score < -limiar:
        return "VENDER"
    else:
        return "NEUTRO / AGUARDAR"


def _avaliar_recomendacoes(df: pd.DataFrame, limiar: float, limiar_neutro_pct: float, coluna_score: str):
    """Aplica um limiar de recomendação e um limiar de 'variação neutra' a um
    conjunto de linhas de backtesting, e retorna a taxa de acerto resultante."""
    df_valido = df.dropna(subset=[coluna_score, "variacao_pct"])

    if df_valido.empty:
        return None, 0

    recomendacoes = df_valido[coluna_score].apply(lambda s: _score_para_recomendacao(s, limiar))
    variacoes = df_valido["variacao_pct"]

    acertos = 0
    for rec, var in zip(recomendacoes, variacoes):
        if rec == "COMPRAR":
            acertos += int(var > 0)
        elif rec == "VENDER":
            acertos += int(var < 0)
        else:
            acertos += int(abs(var) < limiar_neutro_pct)

    total = len(df_valido)
    return acertos / total, total


def calibrar_limiar_recomendacao(
    coluna_score: str = "score_finbert_medio",
    candidatos_limiar=None,
    limiar_neutro_pct: float | None = None,
    proporcao_teste: float = 0.3
):
    """Encontra o limiar de recomendação que maximiza a taxa de acerto no
    CONJUNTO DE CALIBRAÇÃO, e reporta honestamente o desempenho desse limiar
    escolhido no CONJUNTO DE TESTE (nunca usado durante a busca).

    Isso evita o problema do limiar atual (0.15 fixo): sem essa separação,
    qualquer taxa de acerto reportada seria inflada, porque o limiar teria
    sido escolhido (mesmo que informalmente) olhando pros mesmos dados que
    estão sendo usados pra medir o desempenho.

    Também substitui o critério fixo de 'variação neutra' (5%, hoje solto e
    sem relação com o limiar de score) por um valor calculado a partir da
    própria distribuição empírica de variação de preço da amostra (mediana
    do valor absoluto), a menos que um valor seja passado explicitamente.

    IMPORTANTE: esta função só REPORTA o limiar recomendado — ela não
    atualiza `config.py` sozinha. Trocar o LIMIAR_RECOMENDACAO em produção é
    uma decisão que você deve tomar conscientemente, depois de ver o
    resultado.
    """
    df = carregar_base_backtesting()

    if df is None or df.empty:
        print("⚠️  Nenhum dado de backtesting encontrado em base_dados/base_backtesting.csv. "
              "Rode o modo em lote (opção 4) primeiro.")
        return None

    if coluna_score not in df.columns:
        print(f"⚠️  Coluna '{coluna_score}' não encontrada na base de backtesting.")
        return None

    if candidatos_limiar is None:
        candidatos_limiar = np.round(np.arange(0.02, 0.31, 0.01), 2)

    calibracao, teste = _dividir_calibracao_teste(df, proporcao_teste=proporcao_teste)

    if limiar_neutro_pct is None:
        # Calculado só a partir da calibração (não do teste, pra não vazar
        # informação): mediana do valor absoluto da variação de preço.
        limiar_neutro_pct = calibracao["variacao_pct"].abs().median()

    if len(calibracao) < 10 or len(teste) < 5:
        print(f"⚠️  Amostra pequena pra calibrar com confiança "
              f"(calibração={len(calibracao)} linhas, teste={len(teste)} linhas). "
              f"O resultado abaixo é só ilustrativo — rode um lote maior antes de decidir de verdade.")

    resultados = []
    for limiar in candidatos_limiar:
        acc, n = _avaliar_recomendacoes(calibracao, limiar, limiar_neutro_pct, coluna_score)
        if acc is not None:
            resultados.append({"limiar": limiar, "acuracia_calibracao": acc, "n_calibracao": n})

    df_resultados = pd.DataFrame(resultados)

    if df_resultados.empty:
        print("⚠️  Não foi possível calcular acurácia para nenhum limiar candidato.")
        return None

    melhor = df_resultados.loc[df_resultados["acuracia_calibracao"].idxmax()]
    limiar_escolhido = float(melhor["limiar"])

    acc_teste, n_teste = _avaliar_recomendacoes(teste, limiar_escolhido, limiar_neutro_pct, coluna_score)
    acc_teste_atual, _ = _avaliar_recomendacoes(teste, LIMIAR_RECOMENDACAO, limiar_neutro_pct, coluna_score)

    print("═" * 70)
    print(f"  CALIBRAÇÃO DO LIMIAR DE RECOMENDAÇÃO — coluna: {coluna_score}")
    print("═" * 70)
    print(f"  Linhas de calibração            : {len(calibracao)} "
          f"({calibracao['data_fim_noticias'].min()} a {calibracao['data_fim_noticias'].max()})")
    print(f"  Linhas de teste (não visto)      : {len(teste)} "
          f"({teste['data_fim_noticias'].min()} a {teste['data_fim_noticias'].max()})")
    print(f"  Limiar de 'variação neutra' usado : {limiar_neutro_pct:.2f}% (mediana |variação| da calibração)")
    print("─" * 70)
    print(f"  Melhor limiar NA CALIBRAÇÃO       : {limiar_escolhido:.2f} "
          f"(acurácia calibração = {melhor['acuracia_calibracao']*100:.1f}%)")
    if acc_teste is not None:
        print(f"  Acurácia desse limiar NO TESTE     : {acc_teste*100:.1f}%  <- estimativa honesta")
    if acc_teste_atual is not None:
        print(f"  Acurácia do limiar atual ({LIMIAR_RECOMENDACAO}) NO TESTE : {acc_teste_atual*100:.1f}%")
    print("═" * 70)
    print("  ⚠️  A acurácia de CALIBRAÇÃO tende a ser otimista (o limiar foi")
    print("     escolhido justamente pra maximizá-la). A acurácia de TESTE é")
    print("     a estimativa que deve ir pro artigo.")
    print("  Esta função NÃO altera config.py automaticamente.")
    print("═" * 70)

    return {
        "coluna_score": coluna_score,
        "limiar_escolhido": limiar_escolhido,
        "limiar_neutro_pct": float(limiar_neutro_pct),
        "acuracia_calibracao": float(melhor["acuracia_calibracao"]),
        "acuracia_teste": acc_teste,
        "acuracia_teste_limiar_atual": acc_teste_atual,
        "n_calibracao": len(calibracao),
        "n_teste": n_teste,
        "tabela_candidatos": df_resultados
    }


def calibrar_ambos_modelos(proporcao_teste: float = 0.3):
    """Roda a calibração separadamente para FinBERT e PySentimiento (se
    presente) — cada modelo pode ter uma escala de score diferente, então
    compartilhar um único limiar entre os dois (como hoje) não é garantido
    fazer sentido."""
    resultado_fb = calibrar_limiar_recomendacao("score_finbert_medio", proporcao_teste=proporcao_teste)

    df = carregar_base_backtesting()
    resultado_py = None
    if df is not None and "score_pysentimiento_medio" in df.columns and df["score_pysentimiento_medio"].notna().any():
        print()
        resultado_py = calibrar_limiar_recomendacao("score_pysentimiento_medio", proporcao_teste=proporcao_teste)

    return {"finbert": resultado_fb, "pysentimiento": resultado_py}

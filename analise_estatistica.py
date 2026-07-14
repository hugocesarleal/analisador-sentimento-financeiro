import os
import math
import pandas as pd

from config import PASTA_BASE, TICKER_BENCHMARK
from base_dados import carregar_base_backtesting
from mercado import buscar_historico_precos, variacao_da_janela, avaliar_backtesting


def enriquecer_com_benchmark(
    nome_arquivo: str = "base_backtesting.csv",
    nome_saida: str = "base_backtesting_enriquecido.csv"
):
    """Busca o histórico do benchmark (Ibovespa) UMA VEZ, cobrindo todo o
    período coberto pelos dados de backtesting já salvos, e calcula o
    RETORNO EXCEDENTE de cada janela (variação do ativo menos variação do
    benchmark no mesmo período).

    Isso importa porque 'acertar' com o retorno BRUTO durante um período de
    alta generalizada do mercado não prova que o sentimento tem nenhum
    poder preditivo — o ativo podia ter subido de qualquer jeito, junto com
    o mercado inteiro. O retorno excedente isola o que aconteceu ALÉM do
    movimento geral do mercado, que é o que de fato testaria se a análise
    de sentimento agrega informação.

    Salva o resultado em um arquivo SEPARADO (`nome_saida`) — o CSV bruto
    original não é sobrescrito, dados coletados não devem ser misturados
    com colunas derivadas de análise.
    """
    df = carregar_base_backtesting(nome_arquivo)

    if df is None or df.empty:
        print(f"⚠️  Nenhum dado encontrado em {nome_arquivo}. Rode o modo em lote primeiro.")
        return None

    df = df.copy()
    df["data_inicio_preco"] = pd.to_datetime(df["data_inicio_preco"])
    df["data_fim_preco"] = pd.to_datetime(df["data_fim_preco"])

    data_min = df["data_inicio_preco"].min().strftime("%Y-%m-%d")
    data_max = df["data_fim_preco"].max().strftime("%Y-%m-%d")

    print(f"🔍 Buscando histórico do benchmark ({TICKER_BENCHMARK}) de {data_min} a {data_max}...")
    df_benchmark = buscar_historico_precos(TICKER_BENCHMARK, data_min, data_max)

    if df_benchmark is None:
        print(f"⚠️  Não foi possível obter dados do benchmark {TICKER_BENCHMARK}.")
        return None

    variacoes_benchmark = []
    for _, linha in df.iterrows():
        dados_bench = variacao_da_janela(
            df_benchmark,
            linha["data_inicio_preco"].strftime("%Y-%m-%d"),
            linha["data_fim_preco"].strftime("%Y-%m-%d")
        )
        variacoes_benchmark.append(dados_bench["variacao_pct"] if dados_bench else None)

    df["variacao_benchmark_pct"] = variacoes_benchmark
    df["retorno_excedente_pct"] = df["variacao_pct"] - df["variacao_benchmark_pct"]

    def _reavaliar(row, coluna_recomendacao):
        recomendacao = row.get(coluna_recomendacao)
        excedente = row["retorno_excedente_pct"]

        if pd.isna(excedente) or pd.isna(recomendacao):
            return pd.Series([None, None])

        resultado = avaliar_backtesting(recomendacao, excedente)
        return pd.Series([resultado["acertou"], resultado["ganho_pct"]])

    df[["acerto_finbert_excedente", "ganho_pct_finbert_excedente"]] = df.apply(
        lambda r: _reavaliar(r, "recomendacao_finbert"), axis=1
    )

    if "recomendacao_pysentimiento" in df.columns:
        df[["acerto_pysentimiento_excedente", "ganho_pct_pysentimiento_excedente"]] = df.apply(
            lambda r: _reavaliar(r, "recomendacao_pysentimiento"), axis=1
        )

    caminho_saida = os.path.join(PASTA_BASE, nome_saida)
    df.to_csv(caminho_saida, index=False, encoding="utf-8-sig")
    print(f"✅ Dados enriquecidos com retorno excedente salvos em: {caminho_saida}")

    return df


# ---------------------------------------------------------------------------
# Baselines
# ---------------------------------------------------------------------------

def calcular_baseline_aleatorio(df: pd.DataFrame, coluna_variacao: str, limiar_neutro: float = 5.0):
    """Acurácia ESPERADA de um classificador aleatório uniforme entre as 3
    recomendações possíveis (COMPRAR/VENDER/NEUTRO), calculada
    analiticamente — não simulada, então é determinística e sem ruído de
    amostragem extra atrapalhando a comparação."""
    variacoes = df[coluna_variacao].dropna()

    if variacoes.empty:
        return None

    hit_comprar = (variacoes > 0).astype(int)
    hit_vender = (variacoes < 0).astype(int)
    hit_neutro = (variacoes.abs() < limiar_neutro).astype(int)

    return ((hit_comprar + hit_vender + hit_neutro) / 3).mean()


def _acertos_buy_and_hold(df: pd.DataFrame, coluna_variacao: str) -> pd.Series:
    """Série booleana (mesmo índice de `df`) indicando se buy-and-hold
    acertaria em cada janela — usada tanto pra acurácia agregada quanto
    pro teste pareado de McNemar contra o modelo."""
    return df[coluna_variacao] > 0


def calcular_baseline_buy_and_hold(df: pd.DataFrame, coluna_variacao: str):
    """Acurácia de uma estratégia trivial: sempre recomendar COMPRAR."""
    variacoes = df[coluna_variacao].dropna()

    if variacoes.empty:
        return None

    return _acertos_buy_and_hold(df.dropna(subset=[coluna_variacao]), coluna_variacao).mean()


def _acertos_momentum(df: pd.DataFrame, coluna_variacao: str, limiar_neutro: float = 5.0) -> pd.Series:
    """Série booleana (realinhada ao índice original de `df`) indicando se o
    baseline de momentum acertaria em cada janela — usada tanto pra
    acurácia agregada quanto pro teste pareado de McNemar contra o modelo.
    Entradas sem janela anterior disponível (primeira semana de cada ativo)
    ficam como NaN."""
    if "ticker" not in df.columns or "data_fim_noticias" not in df.columns:
        return pd.Series([None] * len(df), index=df.index, dtype=object)

    df_ordenado = df.copy()
    df_ordenado["data_fim_noticias"] = pd.to_datetime(df_ordenado["data_fim_noticias"])
    df_ordenado = df_ordenado.sort_values(["ticker", "data_fim_noticias"])
    df_ordenado["variacao_anterior"] = df_ordenado.groupby("ticker")[coluna_variacao].shift(1)

    def _acerto(row):
        anterior = row["variacao_anterior"]
        atual = row[coluna_variacao]

        if pd.isna(anterior) or pd.isna(atual):
            return None

        if anterior > limiar_neutro:
            return atual > 0
        elif anterior < -limiar_neutro:
            return atual < 0
        else:
            return abs(atual) < limiar_neutro

    resultado = df_ordenado.apply(_acerto, axis=1)
    return resultado.reindex(df.index)


def calcular_baseline_momentum(df: pd.DataFrame, coluna_variacao: str, limiar_neutro: float = 5.0):
    """Acurácia de um baseline de momentum: recomenda na mesma direção do
    retorno da JANELA ANTERIOR do mesmo ativo (requer ordenação cronológica
    por ticker). Testa se o sentimento agrega algo além de simplesmente
    extrapolar a tendência recente do próprio preço."""
    serie = _acertos_momentum(df, coluna_variacao, limiar_neutro)
    serie_valida = serie.dropna()

    if serie_valida.empty:
        return None

    return serie_valida.astype(bool).mean()


# ---------------------------------------------------------------------------
# Testes estatísticos (implementados sem depender de scipy)
# ---------------------------------------------------------------------------

_Z_SCORES = {0.90: 1.6448536269514722, 0.95: 1.959963984540054, 0.99: 2.5758293035489004}


def intervalo_confianca_wilson(acertos: int, total: int, confianca: float = 0.95):
    """Intervalo de confiança de Wilson para uma proporção — mais preciso
    que o intervalo normal simples em amostras pequenas ou proporções perto
    de 0 ou 1 (comuns aqui, já que 'NEUTRO' pode dominar a amostra)."""
    if total == 0:
        return None, None

    z = _Z_SCORES.get(round(confianca, 2), 1.959963984540054)
    p_hat = acertos / total

    denom = 1 + z**2 / total
    centro = p_hat + z**2 / (2 * total)
    margem = z * math.sqrt((p_hat * (1 - p_hat) + z**2 / (4 * total)) / total)

    return (centro - margem) / denom, (centro + margem) / denom


def teste_binomial_normal(acertos: int, total: int, p_nulo: float):
    """Teste Z de uma proporção contra um valor de referência (ex: 0.5 =
    acaso, ou a acurácia de um baseline), com correção de continuidade.

    Aproximação normal válida quando total*p_nulo >= 5 e
    total*(1-p_nulo) >= 5; com amostras bem pequenas, interprete o p-valor
    com cautela adicional.

    Retorna (estatística z, p-valor bicaudal).
    """
    if total == 0 or p_nulo is None or p_nulo <= 0 or p_nulo >= 1:
        return None, None

    p_hat = acertos / total
    erro_padrao = math.sqrt(p_nulo * (1 - p_nulo) / total)
    correcao = 0.5 / total

    diferenca = max(abs(p_hat - p_nulo) - correcao, 0)
    z = diferenca / erro_padrao
    p_valor = math.erfc(z / math.sqrt(2))

    return z, p_valor


def teste_mcnemar(acertos_modelo: pd.Series, acertos_baseline: pd.Series):
    """Teste de McNemar para comparar duas estratégias PAREADAS (o MESMO
    conjunto de janelas, avaliado sob duas regras de decisão diferentes).

    Mais apropriado que dois testes binomiais independentes aqui, porque as
    observações de modelo e baseline não são independentes entre si — são
    o mesmo exemplo avaliado de duas formas. Usa correção de continuidade
    de Yates. Retorna (estatística, p-valor).
    """
    validos = acertos_modelo.notna() & acertos_baseline.notna()
    a = acertos_modelo[validos].astype(bool)
    b = acertos_baseline[validos].astype(bool)

    n10 = int((a & ~b).sum())  # modelo acertou, baseline errou
    n01 = int((~a & b).sum())  # baseline acertou, modelo errou

    if n10 + n01 == 0:
        return 0.0, 1.0

    estatistica = (abs(n10 - n01) - 1) ** 2 / (n10 + n01)
    p_valor = math.erfc(math.sqrt(estatistica / 2))

    return estatistica, p_valor


# ---------------------------------------------------------------------------
# Relatório consolidado
# ---------------------------------------------------------------------------

def _relatar_comparacao(df: pd.DataFrame, coluna_acerto: str, coluna_variacao: str, rotulo: str):
    if coluna_acerto not in df.columns or coluna_variacao not in df.columns:
        return None

    df_validos = df.dropna(subset=[coluna_acerto, coluna_variacao])

    if df_validos.empty:
        return None

    acertos_modelo = df_validos[coluna_acerto].astype(bool)
    acertos = int(acertos_modelo.sum())
    total = len(df_validos)
    acuracia = acertos / total

    ic_low, ic_high = intervalo_confianca_wilson(acertos, total)

    baseline_aleatorio = calcular_baseline_aleatorio(df_validos, coluna_variacao)
    baseline_bh = calcular_baseline_buy_and_hold(df_validos, coluna_variacao)
    baseline_momentum = calcular_baseline_momentum(df_validos, coluna_variacao)

    # "vs acaso" usa teste Z: não há uma sequência realizada de previsões
    # aleatórias pra parear, só uma expectativa analítica (50%).
    z_acaso, p_acaso = teste_binomial_normal(acertos, total, 0.5)

    # "vs buy-and-hold" e "vs momentum" usam McNemar (pareado): modelo e
    # baseline avaliam EXATAMENTE as mesmas janelas, então as observações
    # não são independentes entre si — McNemar é o teste correto aqui,
    # mais apropriado que dois testes binomiais tratados como amostras
    # independentes.
    acertos_bh = _acertos_buy_and_hold(df_validos, coluna_variacao)
    _, p_bh = teste_mcnemar(acertos_modelo, acertos_bh)

    acertos_momentum = _acertos_momentum(df_validos, coluna_variacao)
    _, p_momentum = teste_mcnemar(acertos_modelo, acertos_momentum)

    print("═" * 70)
    print(f"  COMPARAÇÃO COM BASELINES — retorno {rotulo.upper()}")
    print("═" * 70)
    print(f"  N (janelas válidas)            : {total}")
    print(f"  Acurácia do modelo              : {100*acuracia:.1f}%  "
          f"[IC 95%: {100*ic_low:.1f}% – {100*ic_high:.1f}%]")
    print(f"  Baseline aleatório              : "
          f"{f'{100*baseline_aleatorio:.1f}%' if baseline_aleatorio is not None else 'N/A'}")
    print(f"  Baseline buy-and-hold           : "
          f"{f'{100*baseline_bh:.1f}%' if baseline_bh is not None else 'N/A'}")
    print(f"  Baseline momentum               : "
          f"{f'{100*baseline_momentum:.1f}%' if baseline_momentum is not None else 'N/A (dados sequenciais insuficientes)'}")
    print("─" * 70)

    if p_acaso is not None:
        sig = "significativo, p<0.05" if p_acaso < 0.05 else "NÃO significativo"
        print(f"  Modelo vs acaso (50%, teste Z)        -> z={z_acaso:.2f}, p={p_acaso:.4f}  ({sig})")

    if p_bh is not None:
        sig = "significativo, p<0.05" if p_bh < 0.05 else "NÃO significativo"
        print(f"  Modelo vs buy-and-hold (McNemar)       -> p={p_bh:.4f}  ({sig})")

    if p_momentum is not None:
        sig = "significativo, p<0.05" if p_momentum < 0.05 else "NÃO significativo"
        melhor_pior = "modelo PERDE pro momentum" if (baseline_momentum or 0) > acuracia else "modelo bate o momentum"
        print(f"  Modelo vs momentum (McNemar)           -> p={p_momentum:.4f}  ({sig}; {melhor_pior})")

    print("═" * 70)

    return {
        "n": total,
        "acuracia": acuracia,
        "ic_95_low": ic_low,
        "ic_95_high": ic_high,
        "baseline_aleatorio": baseline_aleatorio,
        "baseline_buy_and_hold": baseline_bh,
        "baseline_momentum": baseline_momentum,
        "p_valor_vs_acaso": p_acaso,
        "p_valor_vs_buy_and_hold": p_bh,
        "p_valor_vs_momentum": p_momentum
    }


def gerar_relatorio_estatistico(usar_benchmark: bool = True):
    """Relatório completo da Fase 5: acurácia do modelo com intervalo de
    confiança, comparação com baselines (aleatório, buy-and-hold, momentum),
    e testes de significância — calculado tanto sobre o retorno BRUTO
    quanto sobre o retorno EXCEDENTE ao Ibovespa (se `usar_benchmark=True`).
    """
    if usar_benchmark:
        df = enriquecer_com_benchmark()
    else:
        df = carregar_base_backtesting()

    if df is None or df.empty:
        return None

    resultado = {"bruto": _relatar_comparacao(df, "acerto_finbert", "variacao_pct", "bruto")}

    if usar_benchmark:
        resultado["excedente"] = _relatar_comparacao(
            df, "acerto_finbert_excedente", "retorno_excedente_pct", "excedente (vs Ibovespa)"
        )

    print("\n⚠️  Nota sobre múltiplas comparações: cada teste acima é separado.")
    print("   Se for reportar vários ativos individualmente no artigo (em vez de")
    print("   só o resultado agregado), aplique correção de Bonferroni (divida o")
    print("   alfa de 0.05 pelo número de testes) antes de declarar significância.")

    return resultado

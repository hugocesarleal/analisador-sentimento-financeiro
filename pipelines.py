import time
from datetime import datetime, timedelta

from tqdm import tqdm

from config import ATIVOS, QUANTIDADE_NOTICIAS, LOTE_MESES_HISTORICO, LOTE_GRANULARIDADE_DIAS, LOTE_PAUSA_SEGUNDOS
from noticias import buscar_noticias, buscar_noticias_historicas
from sentimentos import (
    traduzir_para_ingles,
    analisar_finbert,
    analisar_pysentimiento,
    calcular_score_individual_finbert,
    calcular_score_individual_pysentimiento,
    calcular_score_finbert,
    calcular_score_pysentimiento,
    score_para_recomendacao
)
from mercado import (
    buscar_variacao_ativo,
    buscar_historico_precos,
    variacao_da_janela,
    avaliar_backtesting
)
from base_dados import salvar_base_noticias, salvar_base_backtesting
from interface import (
    menu_ativo,
    menu_intervalo,
    selecionar_data_visual,
    separador,
    exibir_analise_noticia,
    exibir_resumo,
    exibir_backtesting
)


def executar_analise_atual(modelos: dict, usar_comparativo: bool):
    """Fluxo 1: análise de notícias recentes."""
    ativo = menu_ativo()
    intervalo = menu_intervalo()

    print(f"\n🔍 Buscando notícias recentes sobre '{ativo['busca']}' (intervalo: {intervalo})...")

    noticias = buscar_noticias(
        ativo["busca"],
        intervalo,
        QUANTIDADE_NOTICIAS
    )

    if not noticias:
        print("⚠️  Nenhuma notícia recente encontrada.")
        return

    print(f"   {len(noticias)} notícias encontradas.\n")

    resultados_finbert = []
    resultados_pysentimento = []
    linhas_base_noticias = []

    for i, noticia in enumerate(noticias, start=1):
        titulo_pt = noticia["titulo"]
        titulo_en = traduzir_para_ingles(titulo_pt)

        res_fb = analisar_finbert(titulo_en, modelos["finbert"])

        res_py = (
            analisar_pysentimiento(titulo_pt, modelos["pysentimiento"])
            if usar_comparativo
            else None
        )

        resultados_finbert.append(res_fb)

        if res_py:
            resultados_pysentimento.append(res_py)

        score_individual_fb = calcular_score_individual_finbert(res_fb)
        score_individual_py = calcular_score_individual_pysentimiento(res_py)

        linhas_base_noticias.append({
            "tipo_execucao": "analise_atual",
            "ativo_nome": ativo["nome"],
            "ticker": ativo["ticker"],
            "termo_busca": ativo["busca"],
            "data_coleta": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "intervalo_busca": intervalo,
            "data_inicio_noticias": None,
            "data_fim_noticias": None,
            "titulo_noticia": titulo_pt,
            "fonte": noticia["fonte"],
            "data_publicacao": noticia["data"],
            "titulo_traduzido_en": titulo_en,
            "sentimento_finbert": res_fb["label"],
            "confianca_finbert": res_fb["score"],
            "score_finbert": score_individual_fb,
            "sentimento_pysentimiento": res_py["label"] if res_py else None,
            "prob_pos_pysentimiento": res_py["pos"] if res_py else None,
            "prob_neg_pysentimiento": res_py["neg"] if res_py else None,
            "prob_neu_pysentimiento": res_py["neu"] if res_py else None,
            "score_pysentimiento": score_individual_py,
            "score_finbert_medio_periodo": None,
            "score_pysentimiento_medio_periodo": None,
            "recomendacao_finbert": None,
            "recomendacao_pysentimiento": None
        })

        exibir_analise_noticia(i, noticia, res_fb, res_py, titulo_en)

    score_fb = calcular_score_finbert(resultados_finbert)
    rec_fb = score_para_recomendacao(score_fb)

    score_py = (
        calcular_score_pysentimiento(resultados_pysentimento)
        if usar_comparativo
        else None
    )

    rec_py = (
        score_para_recomendacao(score_py)
        if score_py is not None
        else None
    )

    for linha in linhas_base_noticias:
        linha["score_finbert_medio_periodo"] = score_fb
        linha["score_pysentimiento_medio_periodo"] = score_py
        linha["recomendacao_finbert"] = rec_fb
        linha["recomendacao_pysentimiento"] = rec_py

    exibir_resumo(
        ativo["nome"],
        len(noticias),
        score_fb,
        rec_fb,
        score_py,
        rec_py,
        usar_comparativo
    )

    salvar_base_noticias(linhas_base_noticias)


def _processar_periodo_backtesting(
    ativo: dict,
    modelos: dict,
    usar_comparativo: bool,
    data_ini_noticias: str,
    data_fim_noticias: str,
    data_ini_preco: str,
    data_fim_preco: str,
    verbose: bool = True,
    df_precos_precarregado=None
):
    """Núcleo do backtesting para UM ativo em UMA janela de tempo.

    Não depende de input()/tkinter — é usado tanto pelo fluxo interativo
    (menu + calendário) quanto pelo modo em lote (batch). Retorna um
    dicionário-resumo da execução, ou None se não houver notícias ou dados
    de preço suficientes para essa janela.

    Se `df_precos_precarregado` for informado (um DataFrame já obtido via
    `buscar_historico_precos`), a variação de preço é recortada localmente
    em vez de disparar uma nova chamada ao yfinance — essencial no modo em
    lote, onde a mesma ação é reaproveitada em dezenas de janelas semanais.
    """
    if verbose:
        print(
            f"\n🔍 Buscando notícias de '{ativo['busca']}' "
            f"entre {data_ini_noticias} e {data_fim_noticias}..."
        )

    noticias = buscar_noticias_historicas(
        ativo["busca"],
        data_ini_noticias,
        data_fim_noticias,
        QUANTIDADE_NOTICIAS
    )

    if not noticias:
        if verbose:
            print("⚠️  Nenhuma notícia encontrada para este período histórico.")
            print("   Dica: O RSS do Google News pode ter limitações para datas muito antigas.")
        return None

    if verbose:
        print(f"   {len(noticias)} notícias encontradas.\n")

    resultados_finbert = []
    resultados_pysentimento = []
    linhas_base_noticias = []

    for i, noticia in enumerate(noticias, start=1):
        titulo_pt = noticia["titulo"]
        titulo_en = traduzir_para_ingles(titulo_pt)

        res_fb = analisar_finbert(titulo_en, modelos["finbert"])

        res_py = (
            analisar_pysentimiento(titulo_pt, modelos["pysentimiento"])
            if usar_comparativo
            else None
        )

        resultados_finbert.append(res_fb)

        if res_py:
            resultados_pysentimento.append(res_py)

        score_individual_fb = calcular_score_individual_finbert(res_fb)
        score_individual_py = calcular_score_individual_pysentimiento(res_py)

        linhas_base_noticias.append({
            "tipo_execucao": "backtesting",
            "ativo_nome": ativo["nome"],
            "ticker": ativo["ticker"],
            "termo_busca": ativo["busca"],
            "data_coleta": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "intervalo_busca": f"{data_ini_noticias} a {data_fim_noticias}",
            "data_inicio_noticias": data_ini_noticias,
            "data_fim_noticias": data_fim_noticias,
            "titulo_noticia": titulo_pt,
            "fonte": noticia["fonte"],
            "data_publicacao": noticia["data"],
            "titulo_traduzido_en": titulo_en,
            "sentimento_finbert": res_fb["label"],
            "confianca_finbert": res_fb["score"],
            "score_finbert": score_individual_fb,
            "sentimento_pysentimiento": res_py["label"] if res_py else None,
            "prob_pos_pysentimiento": res_py["pos"] if res_py else None,
            "prob_neg_pysentimiento": res_py["neg"] if res_py else None,
            "prob_neu_pysentimiento": res_py["neu"] if res_py else None,
            "score_pysentimiento": score_individual_py,
            "score_finbert_medio_periodo": None,
            "score_pysentimiento_medio_periodo": None,
            "recomendacao_finbert": None,
            "recomendacao_pysentimiento": None
        })

        if verbose:
            exibir_analise_noticia(i, noticia, res_fb, res_py, titulo_en)

    score_fb = calcular_score_finbert(resultados_finbert)
    rec_fb = score_para_recomendacao(score_fb)

    score_py = (
        calcular_score_pysentimiento(resultados_pysentimento)
        if usar_comparativo
        else None
    )

    rec_py = (
        score_para_recomendacao(score_py)
        if score_py is not None
        else None
    )

    for linha in linhas_base_noticias:
        linha["score_finbert_medio_periodo"] = score_fb
        linha["score_pysentimiento_medio_periodo"] = score_py
        linha["recomendacao_finbert"] = rec_fb
        linha["recomendacao_pysentimiento"] = rec_py

    if verbose:
        exibir_resumo(
            ativo["nome"], len(noticias), score_fb, rec_fb, score_py, rec_py, usar_comparativo
        )

    salvar_base_noticias(linhas_base_noticias)

    if verbose:
        print(f"\n📊 Validando recomendação com preços entre {data_ini_preco} e {data_fim_preco}...")

    if df_precos_precarregado is not None:
        dados = variacao_da_janela(df_precos_precarregado, data_ini_preco, data_fim_preco)
    else:
        dados = buscar_variacao_ativo(ativo["ticker"], data_ini_preco, data_fim_preco)

    if not dados:
        if verbose:
            print(f"⚠️  Não foi possível obter dados históricos para {ativo['ticker']}.")
        return None

    if verbose:
        exibir_backtesting(ativo["nome"], ativo["ticker"], dados, rec_fb, rec_py, usar_comparativo)

    bt_fb = avaliar_backtesting(rec_fb, dados["variacao_pct"])

    bt_py = None
    if usar_comparativo and rec_py:
        bt_py = avaliar_backtesting(rec_py, dados["variacao_pct"])

    linha_backtesting = {
        "ativo_nome": ativo["nome"],
        "ticker": ativo["ticker"],
        "termo_busca": ativo["busca"],
        "data_execucao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "data_inicio_noticias": data_ini_noticias,
        "data_fim_noticias": data_fim_noticias,
        "data_inicio_preco": data_ini_preco,
        "data_fim_preco": data_fim_preco,
        "qtd_noticias": len(noticias),
        "score_finbert_medio": score_fb,
        "recomendacao_finbert": rec_fb,
        "score_pysentimiento_medio": score_py,
        "recomendacao_pysentimiento": rec_py,
        "preco_inicio": dados["preco_inicio"],
        "preco_fim": dados["preco_fim"],
        "data_real_inicio_preco": dados["data_inicio"],
        "data_real_fim_preco": dados["data_fim"],
        "variacao_pct": dados["variacao_pct"],
        "acerto_finbert": bt_fb["acertou"],
        "ganho_pct_finbert": bt_fb["ganho_pct"],
        "acerto_pysentimiento": bt_py["acertou"] if bt_py else None,
        "ganho_pct_pysentimiento": bt_py["ganho_pct"] if bt_py else None
    }

    salvar_base_backtesting(linha_backtesting)

    return {
        "qtd_noticias": len(noticias),
        "score_finbert": score_fb,
        "recomendacao_finbert": rec_fb,
        "score_pysentimiento": score_py,
        "recomendacao_pysentimiento": rec_py,
        "variacao_pct": dados["variacao_pct"],
        "acerto_finbert": bt_fb["acertou"],
        "acerto_pysentimiento": bt_py["acertou"] if bt_py else None,
    }


def executar_backtesting(modelos: dict, usar_comparativo: bool):
    """Fluxo 2: análise histórica com validação por preço futuro (modo interativo,
    com seleção manual de ativo e datas via calendário)."""
    ativo = menu_ativo()

    separador()
    print("  CONFIGURAÇÃO DO BACKTESTING")
    separador()

    print("  1. Período das notícias (o que o modelo vai 'ler'):")
    print("     [Abrindo calendário...] Selecione a Data Início das notícias.")
    data_ini_noticias = selecionar_data_visual("Data Início (Notícias)")

    if not data_ini_noticias:
        print("  Operação cancelada.")
        return

    print(f"     Data Início: {data_ini_noticias}")

    print("     [Abrindo calendário...] Selecione a Data Fim das notícias.")
    data_fim_noticias = selecionar_data_visual("Data Fim (Notícias)")

    if not data_fim_noticias:
        print("  Operação cancelada.")
        return

    print(f"     Data Fim   : {data_fim_noticias}")

    print("\n  2. Período de observação do preço (logo após as notícias):")

    data_ini_preco = data_fim_noticias

    print(f"     A avaliação de preço começará automaticamente em {data_ini_preco}")
    print("     [Abrindo calendário...] Selecione a Data Fim da avaliação do preço.")
    data_fim_preco = selecionar_data_visual("Data Fim (Avaliação de Preço)")

    if not data_fim_preco:
        print("  Operação cancelada.")
        return

    print(f"     Data Fim da avaliação: {data_fim_preco}")

    print(
        f"\n🔍 Buscando notícias de '{ativo['busca']}' "
        f"entre {data_ini_noticias} e {data_fim_noticias}..."
    )

    _processar_periodo_backtesting(
        ativo,
        modelos,
        usar_comparativo,
        data_ini_noticias,
        data_fim_noticias,
        data_ini_preco,
        data_fim_preco,
        verbose=True
    )


def gerar_janelas_semanais(data_inicio_total: datetime, data_fim_total: datetime, granularidade_dias: int = 7):
    """Gera as janelas walk-forward do experimento em lote.

    Cada janela é composta por:
    - um período de notícias de `granularidade_dias` dias (o que o modelo "lê");
    - seguido por um período de preço com o MESMO tamanho, imediatamente após
      o fim das notícias (o que o modelo está tentando prever).

    A cada iteração o cursor avança `granularidade_dias`, criando uma
    sequência de janelas semanais consecutivas cobrindo todo o intervalo
    [data_inicio_total, data_fim_total].
    """
    janelas = []
    cursor = data_inicio_total

    while True:
        data_fim_noticias = cursor + timedelta(days=granularidade_dias)
        data_fim_preco = data_fim_noticias + timedelta(days=granularidade_dias)

        if data_fim_preco > data_fim_total:
            break

        janelas.append({
            "data_ini_noticias": cursor.strftime("%Y-%m-%d"),
            "data_fim_noticias": data_fim_noticias.strftime("%Y-%m-%d"),
            "data_ini_preco": data_fim_noticias.strftime("%Y-%m-%d"),
            "data_fim_preco": data_fim_preco.strftime("%Y-%m-%d"),
        })

        cursor += timedelta(days=granularidade_dias)

    return janelas


def executar_backtesting_lote(
    modelos: dict,
    usar_comparativo: bool,
    ativos: list | None = None,
    meses_historico: int = LOTE_MESES_HISTORICO,
    granularidade_dias: int = LOTE_GRANULARIDADE_DIAS,
    pausa_entre_requisicoes: float = LOTE_PAUSA_SEGUNDOS
):
    """Fluxo 4 (NOVO): experimento em lote, totalmente automatizado.

    Roda o backtesting para vários ativos, em várias janelas semanais
    consecutivas cobrindo `meses_historico` meses, sem NENHUMA intervenção
    manual (sem menu, sem calendário). Isso é o que permite gerar uma
    amostra grande o suficiente para análise estatística (Fase 5), em vez
    de um único ponto de dado por execução manual.

    Otimização importante: o histórico de preço de cada ativo é buscado
    UMA ÚNICA VEZ (não uma vez por janela semanal) e reaproveitado
    localmente — isso evita ~50 chamadas ao yfinance por ativo.

    Limitações conhecidas desta primeira versão (a resolver nos próximos
    passos da Fase 1):
    - os resultados ainda não carregam um identificador de execução (run_id)
      para diferenciar lotes distintos na mesma tabela CSV;
    - a tradução (Google Translate) ainda não tem cache, então rodar este
      lote duas vezes pode gerar pequenas variações e é relativamente lento
      (até QUANTIDADE_NOTICIAS × nº de janelas traduções por ativo).
    """
    if ativos is None:
        ativos = [v for v in ATIVOS.values() if v["ticker"] is not None]

    # Margem de segurança para garantir que o preço final de cada janela
    # já esteja disponível no yfinance (evita janelas "no fio" do dia atual).
    data_fim_total = datetime.now() - timedelta(days=3)
    data_inicio_total = data_fim_total - timedelta(days=30 * meses_historico)

    janelas = gerar_janelas_semanais(data_inicio_total, data_fim_total, granularidade_dias)

    separador("═")
    print("  EXPERIMENTO EM LOTE — BACKTESTING AUTOMATIZADO")
    separador("═")
    print(f"  Período total       : {data_inicio_total.strftime('%Y-%m-%d')} → {data_fim_total.strftime('%Y-%m-%d')}")
    print(f"  Ativos              : {len(ativos)}")
    print(f"  Janelas por ativo   : {len(janelas)}")
    print(f"  Total de execuções  : {len(ativos) * len(janelas)}")
    separador("═")

    resumo_execucoes = []

    for ativo in ativos:
        print(f"\n📈 {ativo['nome']} ({ativo['ticker']})")

        df_precos = buscar_historico_precos(
            ativo["ticker"],
            data_inicio_total.strftime("%Y-%m-%d"),
            data_fim_total.strftime("%Y-%m-%d")
        )

        if df_precos is None:
            print(f"   ⚠️  Sem dados de preço para {ativo['ticker']}, pulando ativo.")
            continue

        for janela in tqdm(janelas, desc=f"   {ativo['ticker']}"):
            try:
                resultado = _processar_periodo_backtesting(
                    ativo,
                    modelos,
                    usar_comparativo,
                    janela["data_ini_noticias"],
                    janela["data_fim_noticias"],
                    janela["data_ini_preco"],
                    janela["data_fim_preco"],
                    verbose=False,
                    df_precos_precarregado=df_precos
                )

                if resultado:
                    resumo_execucoes.append({
                        "ativo": ativo["nome"],
                        "ticker": ativo["ticker"],
                        **janela,
                        **resultado
                    })

            except Exception as e:
                print(f"   ⚠️  Falhou janela {janela['data_ini_noticias']}–{janela['data_fim_noticias']}: {e}")

            time.sleep(pausa_entre_requisicoes)

    total_esperado = len(ativos) * len(janelas)
    print(f"\n✅ Lote finalizado: {len(resumo_execucoes)}/{total_esperado} execuções concluídas com sucesso.")

    if resumo_execucoes:
        acertos_fb = sum(1 for r in resumo_execucoes if r["acerto_finbert"])
        print(f"📈 Taxa de acerto (FinBERT) neste lote: {acertos_fb}/{len(resumo_execucoes)} "
              f"= {100 * acertos_fb / len(resumo_execucoes):.1f}%")

        if usar_comparativo:
            validos_py = [r for r in resumo_execucoes if r["acerto_pysentimiento"] is not None]
            if validos_py:
                acertos_py = sum(1 for r in validos_py if r["acerto_pysentimiento"])
                print(f"📈 Taxa de acerto (PySentimiento) neste lote: {acertos_py}/{len(validos_py)} "
                      f"= {100 * acertos_py / len(validos_py):.1f}%")

        print("\n⚠️  Nota: esta é uma taxa de acerto BRUTA, só pra ter um sinal rápido.")
        print("   Ainda não tem baseline de comparação nem significância estatística —")
        print("   isso é o que vamos resolver na Fase 5.")

    return resumo_execucoes

import time
from datetime import datetime, timedelta

from tqdm import tqdm

from config import (
    ATIVOS,
    QUANTIDADE_NOTICIAS,
    LOTE_MESES_HISTORICO,
    LOTE_GRANULARIDADE_DIAS,
    LOTE_PAUSA_SEGUNDOS,
    VALIDAR_PERIODO_NOTICIAS_HISTORICAS,
    MARGEM_TOLERANCIA_DIAS_NOTICIAS
)
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
from experimento import gerar_run_id, registrar_execucao
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
    run_id = gerar_run_id()

    ativo = menu_ativo()
    intervalo = menu_intervalo()

    registrar_execucao(
        run_id,
        tipo_execucao="analise_atual",
        usar_comparativo=usar_comparativo,
        parametros_extra={
            "ativo_nome": ativo["nome"],
            "ticker": ativo["ticker"],
            "intervalo": intervalo
        }
    )

    print(f"\n🔖 Run ID desta execução: {run_id}")
    print(f"🔍 Buscando notícias recentes sobre '{ativo['busca']}' (intervalo: {intervalo})...")

    noticias, descartadas_duplicadas = buscar_noticias(
        ativo["busca"],
        intervalo,
        QUANTIDADE_NOTICIAS
    )

    if descartadas_duplicadas > 0:
        print(f"   ℹ️  {descartadas_duplicadas} notícia(s) duplicada(s) descartada(s).")

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
            "data_publicacao_verificada": noticia.get("data_verificada"),
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

    salvar_base_noticias(linhas_base_noticias, run_id=run_id)


def _processar_periodo_backtesting(
    ativo: dict,
    modelos: dict,
    usar_comparativo: bool,
    data_ini_noticias: str,
    data_fim_noticias: str,
    data_ini_preco: str,
    data_fim_preco: str,
    run_id: str,
    verbose: bool = True,
    df_precos_precarregado=None,
    titulos_ja_processados: set | None = None
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

    Se `titulos_ja_processados` for informado (um `set()` compartilhado entre
    todas as janelas do MESMO ativo dentro de um lote), notícias já vistas em
    uma janela anterior desse ativo são descartadas como duplicadas — evita
    que a mesma notícia "vaze" pra semana seguinte por imprecisão do RSS.
    """
    if verbose:
        print(
            f"\n🔍 Buscando notícias de '{ativo['busca']}' "
            f"entre {data_ini_noticias} e {data_fim_noticias}..."
        )

    noticias, descartadas_fora_periodo, descartadas_duplicadas = buscar_noticias_historicas(
        ativo["busca"],
        data_ini_noticias,
        data_fim_noticias,
        QUANTIDADE_NOTICIAS,
        validar_periodo=VALIDAR_PERIODO_NOTICIAS_HISTORICAS,
        margem_dias=MARGEM_TOLERANCIA_DIAS_NOTICIAS,
        verbose=verbose,
        titulos_ja_processados=titulos_ja_processados
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
            "data_publicacao_verificada": noticia.get("data_verificada"),
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

    salvar_base_noticias(linhas_base_noticias, run_id=run_id)

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

    salvar_base_backtesting(linha_backtesting, run_id=run_id)

    return {
        "run_id": run_id,
        "qtd_noticias": len(noticias),
        "noticias_descartadas_fora_periodo": descartadas_fora_periodo,
        "noticias_descartadas_duplicadas": descartadas_duplicadas,
        "taxa_cobertura_noticias": len(noticias) / QUANTIDADE_NOTICIAS,
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
    run_id = gerar_run_id()

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

    registrar_execucao(
        run_id,
        tipo_execucao="backtesting_manual",
        usar_comparativo=usar_comparativo,
        parametros_extra={
            "ativo_nome": ativo["nome"],
            "ticker": ativo["ticker"],
            "data_inicio_noticias": data_ini_noticias,
            "data_fim_noticias": data_fim_noticias,
            "data_inicio_preco": data_ini_preco,
            "data_fim_preco": data_fim_preco,
        }
    )

    print(f"\n🔖 Run ID desta execução: {run_id}")
    print(
        f"🔍 Buscando notícias de '{ativo['busca']}' "
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
        run_id=run_id,
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
    """Fluxo 4: experimento em lote, totalmente automatizado.

    Roda o backtesting para vários ativos, em várias janelas semanais
    consecutivas cobrindo `meses_historico` meses, sem NENHUMA intervenção
    manual (sem menu, sem calendário). Isso é o que permite gerar uma
    amostra grande o suficiente para análise estatística (Fase 5), em vez
    de um único ponto de dado por execução manual.

    Otimização importante: o histórico de preço de cada ativo é buscado
    UMA ÚNICA VEZ (não uma vez por janela semanal) e reaproveitado
    localmente — isso evita ~50 chamadas ao yfinance por ativo.

    Todas as janelas de todos os ativos deste lote compartilham o MESMO
    run_id (o lote inteiro é uma única "execução" do ponto de vista de
    reprodutibilidade — todas rodaram com a mesma config e mesmas versões
    de biblioteca). Isso permite depois filtrar no CSV `df[df.run_id == X]`
    pra isolar exatamente os resultados gerados por este lote.

    Limitação conhecida ainda em aberto (próximo passo da Fase 1):
    a tradução (Google Translate) ainda não tem cache, então rodar este
    lote duas vezes pode gerar pequenas variações e é relativamente lento
    (até QUANTIDADE_NOTICIAS × nº de janelas traduções por ativo).
    """
    run_id = gerar_run_id()

    if ativos is None:
        ativos = [v for v in ATIVOS.values() if v["ticker"] is not None]

    # Margem de segurança para garantir que o preço final de cada janela
    # já esteja disponível no yfinance (evita janelas "no fio" do dia atual).
    data_fim_total = datetime.now() - timedelta(days=3)
    data_inicio_total = data_fim_total - timedelta(days=30 * meses_historico)

    janelas = gerar_janelas_semanais(data_inicio_total, data_fim_total, granularidade_dias)

    registrar_execucao(
        run_id,
        tipo_execucao="backtesting_lote",
        usar_comparativo=usar_comparativo,
        parametros_extra={
            "qtd_ativos": len(ativos),
            "meses_historico": meses_historico,
            "granularidade_dias": granularidade_dias,
            "pausa_entre_requisicoes": pausa_entre_requisicoes,
            "data_inicio_total": data_inicio_total.strftime("%Y-%m-%d"),
            "data_fim_total": data_fim_total.strftime("%Y-%m-%d"),
            "total_janelas_por_ativo": len(janelas),
        }
    )

    separador("═")
    print("  EXPERIMENTO EM LOTE — BACKTESTING AUTOMATIZADO")
    separador("═")
    print(f"  Run ID              : {run_id}")
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

        # Um set por ativo (não global entre ativos): o mesmo título pode
        # legitimamente aparecer nas buscas de dois ativos diferentes (ex:
        # uma notícia que menciona Petrobras E Bradesco), então não deve ser
        # descartado nesse caso — só entre janelas semanais DESTE ativo.
        titulos_processados_ativo = set()
        resumo_execucoes_ativo = []

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
                    run_id=run_id,
                    verbose=False,
                    df_precos_precarregado=df_precos,
                    titulos_ja_processados=titulos_processados_ativo
                )

                if resultado:
                    linha_resumo = {
                        "ativo": ativo["nome"],
                        "ticker": ativo["ticker"],
                        **janela,
                        **resultado
                    }
                    resumo_execucoes.append(linha_resumo)
                    resumo_execucoes_ativo.append(linha_resumo)

            except Exception as e:
                print(f"   ⚠️  Falhou janela {janela['data_ini_noticias']}–{janela['data_fim_noticias']}: {e}")

            time.sleep(pausa_entre_requisicoes)

        if resumo_execucoes_ativo:
            cobertura_media_ativo = sum(r["taxa_cobertura_noticias"] for r in resumo_execucoes_ativo) / len(resumo_execucoes_ativo)
            qtd_media_ativo = sum(r["qtd_noticias"] for r in resumo_execucoes_ativo) / len(resumo_execucoes_ativo)
            duplicadas_ativo = sum(r.get("noticias_descartadas_duplicadas", 0) for r in resumo_execucoes_ativo)
            print(
                f"   📋 Cobertura média de notícias: {100 * cobertura_media_ativo:.1f}% "
                f"(méd. {qtd_media_ativo:.1f}/{QUANTIDADE_NOTICIAS} por semana"
                + (f", {duplicadas_ativo} duplicada(s) descartada(s) no total" if duplicadas_ativo > 0 else "")
                + ")"
            )

    total_esperado = len(ativos) * len(janelas)
    print(f"\n✅ Lote finalizado ({run_id}): {len(resumo_execucoes)}/{total_esperado} execuções concluídas com sucesso.")

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

        total_descartadas_periodo = sum(r.get("noticias_descartadas_fora_periodo", 0) for r in resumo_execucoes)
        total_descartadas_duplicadas = sum(r.get("noticias_descartadas_duplicadas", 0) for r in resumo_execucoes)
        total_noticias_validas = sum(r.get("qtd_noticias", 0) for r in resumo_execucoes)
        cobertura_media_geral = sum(r["taxa_cobertura_noticias"] for r in resumo_execucoes) / len(resumo_execucoes)

        print(f"\n📋 Cobertura média de notícias (todo o lote): {100 * cobertura_media_geral:.1f}% "
              f"da quantidade solicitada ({QUANTIDADE_NOTICIAS}/janela)")

        if total_descartadas_periodo > 0:
            print(f"📋 Notícias descartadas por estarem confirmadamente fora do período: "
                  f"{total_descartadas_periodo}")

        if total_descartadas_duplicadas > 0:
            print(f"📋 Notícias descartadas por duplicidade: {total_descartadas_duplicadas}")

        print("\n⚠️  Nota: esta é uma taxa de acerto BRUTA, só pra ter um sinal rápido.")
        print("   Ainda não tem baseline de comparação nem significância estatística —")
        print("   isso é o que vamos resolver na Fase 5.")

    return resumo_execucoes

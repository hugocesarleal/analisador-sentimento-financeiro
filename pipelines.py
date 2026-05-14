from datetime import datetime

from config import QUANTIDADE_NOTICIAS
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
from mercado import buscar_variacao_ativo, avaliar_backtesting
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


def executar_backtesting(modelos: dict, usar_comparativo: bool):
    """Fluxo 2: análise histórica com validação por preço futuro."""
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

    noticias = buscar_noticias_historicas(
        ativo["busca"],
        data_ini_noticias,
        data_fim_noticias,
        QUANTIDADE_NOTICIAS
    )

    if not noticias:
        print("⚠️  Nenhuma notícia encontrada para este período histórico.")
        print("   Dica: O RSS do Google News pode ter limitações para datas muito antigas.")
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

    print(f"\n📊 Validando recomendação com preços entre {data_ini_preco} e {data_fim_preco}...")

    dados = buscar_variacao_ativo(
        ativo["ticker"],
        data_ini_preco,
        data_fim_preco
    )

    if dados:
        exibir_backtesting(
            ativo["nome"],
            ativo["ticker"],
            dados,
            rec_fb,
            rec_py,
            usar_comparativo
        )

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

    else:
        print(f"⚠️  Não foi possível obter dados históricos para {ativo['ticker']}.")
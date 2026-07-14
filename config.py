ATIVOS = {
    "1": {"nome": "Petrobras",       "ticker": "PETR4.SA", "busca": "Petrobras PETR4"},
    "2": {"nome": "Vale",            "ticker": "VALE3.SA", "busca": "Vale VALE3"},
    "3": {"nome": "Itaú Unibanco",   "ticker": "ITUB4.SA", "busca": "Itaú Unibanco ITUB4"},
    "4": {"nome": "Ambev",           "ticker": "ABEV3.SA", "busca": "Ambev ABEV3"},
    "5": {"nome": "Magazine Luiza",  "ticker": "MGLU3.SA", "busca": "Magazine Luiza MGLU3"},
    "6": {"nome": "Bradesco",        "ticker": "BBDC4.SA", "busca": "Bradesco BBDC4"},
    "7": {"nome": "WEG",             "ticker": "WEGE3.SA", "busca": "WEG WEGE3"},
    "8": {"nome": "Embraer",         "ticker": "EMBJ3.SA", "busca": "Embraer"},
    "9": {"nome": "Outro (digitar)", "ticker": None,        "busca": None},
}

PASTA_BASE = "base_dados"

QUANTIDADE_NOTICIAS = 10

LIMIAR_RECOMENDACAO = 0.15

# ---------------------------------------------------------------------------
# Configurações do modo de EXPERIMENTO EM LOTE (batch/backtesting automatizado)
# ---------------------------------------------------------------------------
# Quantos meses de histórico cobrir a partir de hoje (janela total do experimento)
LOTE_MESES_HISTORICO = 12

# Tamanho de cada janela walk-forward, em dias (7 = semanal)
LOTE_GRANULARIDADE_DIAS = 7

# Pausa entre requisições de notícias, em segundos (evita bloqueio/rate-limit do Google News RSS)
LOTE_PAUSA_SEGUNDOS = 1.5

# ---------------------------------------------------------------------------
# Validação de confiabilidade das datas de notícias históricas
# ---------------------------------------------------------------------------
# O Google News RSS não garante que os operadores after:/before: retornem
# apenas notícias publicadas dentro do período pedido. Quando True, cada
# notícia é auditada contra sua própria data de publicação reportada no feed,
# e notícias CONFIRMADAMENTE fora do período são descartadas.
VALIDAR_PERIODO_NOTICIAS_HISTORICAS = True

# Margem de tolerância (em dias) ao redor do período pedido, pra absorver
# pequenas discrepâncias de fuso horário/indexação do próprio Google News.
MARGEM_TOLERANCIA_DIAS_NOTICIAS = 1

# ---------------------------------------------------------------------------
# Cache de traduções (pt -> en)
# ---------------------------------------------------------------------------
# Garante reprodutibilidade (a mesma tradução é usada em execuções repetidas,
# mesmo que o Google Translate mude de comportamento) e reduz drasticamente
# o número de chamadas externas em experimentos em lote com manchetes repetidas.
USAR_CACHE_TRADUCAO = True

# ---------------------------------------------------------------------------
# Validação automática de confiabilidade do sentimento (sem gabarito humano)
# ---------------------------------------------------------------------------
# Limiar abaixo do qual uma classificação do FinBERT é considerada de baixa
# confiança (usado só para fins de relatório/diagnóstico, não filtra nada).
LIMIAR_CONFIANCA_BAIXA = 0.6

# ---------------------------------------------------------------------------
# Benchmark de mercado (para retorno excedente)
# ---------------------------------------------------------------------------
# Ticker do Ibovespa no Yahoo Finance, usado para calcular o retorno
# EXCEDENTE de cada recomendação (variação do ativo menos variação do
# índice no mesmo período) — isola o que aconteceu além do movimento geral
# do mercado.
TICKER_BENCHMARK = "^BVSP"

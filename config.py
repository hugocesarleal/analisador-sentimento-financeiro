ATIVOS = {
    "1": {"nome": "Petrobras",       "ticker": "PETR4.SA", "busca": "Petrobras PETR4"},
    "2": {"nome": "Vale",            "ticker": "VALE3.SA", "busca": "Vale VALE3"},
    "3": {"nome": "Itaú Unibanco",   "ticker": "ITUB4.SA", "busca": "Itaú Unibanco ITUB4"},
    "4": {"nome": "Ambev",           "ticker": "ABEV3.SA", "busca": "Ambev ABEV3"},
    "5": {"nome": "Magazine Luiza",  "ticker": "MGLU3.SA", "busca": "Magazine Luiza MGLU3"},
    "6": {"nome": "Bradesco",        "ticker": "BBDC4.SA", "busca": "Bradesco BBDC4"},
    "7": {"nome": "WEG",             "ticker": "WEGE3.SA", "busca": "WEG WEGE3"},
    "8": {"nome": "Embraer",         "ticker": "EMBR3.SA", "busca": "Embraer EMBR3"},
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

import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

from logging_config import obter_logger

logger = obter_logger(__name__)


def buscar_variacao_ativo(ticker: str, data_inicio: str, data_fim: str) -> dict | None:
    """Busca a variação de preço de um ativo para UMA janela específica.
    Faz uma chamada ao yfinance por execução — usado no fluxo interativo,
    onde só existe uma janela por vez."""
    try:
        data_fim_yf = (
            datetime.strptime(data_fim, "%Y-%m-%d") + timedelta(days=1)
        ).strftime("%Y-%m-%d")

        df = yf.download(
            ticker,
            start=data_inicio,
            end=data_fim_yf,
            progress=False,
            auto_adjust=True
        )

        if df.empty or len(df) < 2:
            return None

        precos = df["Close"].squeeze()

        preco_inicio = float(precos.iloc[0])
        preco_fim = float(precos.iloc[-1])
        variacao_pct = ((preco_fim - preco_inicio) / preco_inicio) * 100

        return {
            "preco_inicio": preco_inicio,
            "preco_fim": preco_fim,
            "variacao_pct": variacao_pct,
            "data_inicio": df.index[0].strftime("%d/%m/%Y"),
            "data_fim": df.index[-1].strftime("%d/%m/%Y"),
        }

    except Exception as e:
        logger.error(f"Falha ao buscar variação do ativo {ticker} ({data_inicio} a {data_fim}): {e}")
        print(f"  [ERRO yfinance] {e}")
        return None


def buscar_historico_precos(ticker: str, data_inicio: str, data_fim: str) -> pd.DataFrame | None:
    """Busca o histórico de preços de um ativo UMA ÚNICA VEZ, cobrindo todo o
    período do experimento. Usado no modo em lote para evitar centenas de
    chamadas repetidas ao yfinance (uma por janela semanal) — em vez disso,
    cada janela é recortada localmente a partir deste histórico único."""
    try:
        data_fim_yf = (
            datetime.strptime(data_fim, "%Y-%m-%d") + timedelta(days=1)
        ).strftime("%Y-%m-%d")

        df = yf.download(
            ticker,
            start=data_inicio,
            end=data_fim_yf,
            progress=False,
            auto_adjust=True
        )

        if df.empty:
            return None

        return df

    except Exception as e:
        logger.error(f"Falha ao buscar histórico de preços de {ticker} ({data_inicio} a {data_fim}): {e}")
        print(f"  [ERRO yfinance] {ticker}: {e}")
        return None


def variacao_da_janela(df_precos: pd.DataFrame, data_ini: str, data_fim: str) -> dict | None:
    """Recorta uma janela específica [data_ini, data_fim] a partir de um
    histórico de preços já carregado (via buscar_historico_precos), sem fazer
    nenhuma nova chamada de rede. Usado no modo em lote."""
    if df_precos is None or df_precos.empty:
        return None

    dt_ini = pd.Timestamp(data_ini)
    dt_fim = pd.Timestamp(data_fim)

    janela = df_precos.loc[(df_precos.index >= dt_ini) & (df_precos.index <= dt_fim)]

    if janela.empty or len(janela) < 2:
        return None

    precos = janela["Close"].squeeze()

    preco_inicio = float(precos.iloc[0])
    preco_fim = float(precos.iloc[-1])
    variacao_pct = ((preco_fim - preco_inicio) / preco_inicio) * 100

    return {
        "preco_inicio": preco_inicio,
        "preco_fim": preco_fim,
        "variacao_pct": variacao_pct,
        "data_inicio": janela.index[0].strftime("%d/%m/%Y"),
        "data_fim": janela.index[-1].strftime("%d/%m/%Y"),
    }

#T

def avaliar_backtesting(recomendacao: str, variacao_pct: float) -> dict:
    acertou = False
    ganho_pct = 0.0

    if recomendacao == "COMPRAR":
        ganho_pct = variacao_pct
        acertou = variacao_pct > 0

    elif recomendacao == "VENDER":
        ganho_pct = -variacao_pct
        acertou = variacao_pct < 0

    else:
        ganho_pct = 0.0
        acertou = abs(variacao_pct) < 5

    return {
        "acertou": acertou,
        "ganho_pct": ganho_pct
    }

import yfinance as yf
from datetime import datetime, timedelta


def buscar_variacao_ativo(ticker: str, data_inicio: str, data_fim: str) -> dict | None:
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
        print(f"  [ERRO yfinance] {e}")
        return None

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
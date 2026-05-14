import os
import pandas as pd
from config import PASTA_BASE


def garantir_pasta_base():
    """Cria a pasta da base de dados caso ela ainda não exista."""
    os.makedirs(PASTA_BASE, exist_ok=True)


def salvar_base_noticias(linhas: list[dict], nome_arquivo: str = "base_noticias_sentimento.csv"):
    """Salva ou acrescenta registros de notícias analisadas em CSV."""
    if not linhas:
        return

    garantir_pasta_base()

    caminho = os.path.join(PASTA_BASE, nome_arquivo)
    df = pd.DataFrame(linhas)

    if os.path.exists(caminho):
        df.to_csv(caminho, mode="a", header=False, index=False, encoding="utf-8-sig")
    else:
        df.to_csv(caminho, index=False, encoding="utf-8-sig")

    print(f"\n✅ Base de notícias salva em: {caminho}")


def salvar_base_backtesting(linha: dict, nome_arquivo: str = "base_backtesting.csv"):
    """Salva ou acrescenta um registro consolidado de backtesting em CSV."""
    if not linha:
        return

    garantir_pasta_base()

    caminho = os.path.join(PASTA_BASE, nome_arquivo)
    df = pd.DataFrame([linha])

    if os.path.exists(caminho):
        df.to_csv(caminho, mode="a", header=False, index=False, encoding="utf-8-sig")
    else:
        df.to_csv(caminho, index=False, encoding="utf-8-sig")

    print(f"\n✅ Base de backtesting salva em: {caminho}")
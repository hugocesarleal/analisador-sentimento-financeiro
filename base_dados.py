import os
import pandas as pd
from config import PASTA_BASE


def garantir_pasta_base():
    """Cria a pasta da base de dados caso ela ainda não exista."""
    os.makedirs(PASTA_BASE, exist_ok=True)


def _salvar_dataframe(df: pd.DataFrame, caminho: str):
    """Salva um DataFrame em CSV, alinhando corretamente com o schema já
    existente no arquivo.

    Se o arquivo já existir com colunas DIFERENTES das do DataFrame atual —
    por exemplo, porque a coluna `run_id` foi adicionada numa versão mais
    recente do pipeline, e o arquivo antigo não tem essa coluna — um append
    cego (mode='a', header=False) desalinharia todas as colunas silenciosamente,
    corrompendo os dados já salvos sem gerar nenhum erro visível.

    Em vez disso: se o schema mudou, lê o arquivo inteiro, faz a união das
    colunas (linhas antigas ganham vazio nas colunas novas) e reescreve tudo.
    Se o schema é igual, faz o append rápido de sempre.
    """
    if os.path.exists(caminho):
        df_existente = pd.read_csv(caminho, encoding="utf-8-sig")

        if list(df_existente.columns) == list(df.columns):
            df.to_csv(caminho, mode="a", header=False, index=False, encoding="utf-8-sig")
            return

        df_final = pd.concat([df_existente, df], ignore_index=True, sort=False)
        df_final.to_csv(caminho, index=False, encoding="utf-8-sig")
    else:
        df.to_csv(caminho, index=False, encoding="utf-8-sig")


def salvar_base_noticias(
    linhas: list[dict],
    run_id: str | None = None,
    nome_arquivo: str = "base_noticias_sentimento.csv"
):
    """Salva ou acrescenta registros de notícias analisadas em CSV."""
    if not linhas:
        return

    garantir_pasta_base()

    if run_id:
        for linha in linhas:
            linha.setdefault("run_id", run_id)

    caminho = os.path.join(PASTA_BASE, nome_arquivo)
    df = pd.DataFrame(linhas)

    _salvar_dataframe(df, caminho)

    print(f"\n✅ Base de notícias salva em: {caminho}")


def salvar_base_backtesting(
    linha: dict,
    run_id: str | None = None,
    nome_arquivo: str = "base_backtesting.csv"
):
    """Salva ou acrescenta um registro consolidado de backtesting em CSV."""
    if not linha:
        return

    garantir_pasta_base()

    if run_id:
        linha = {**linha, "run_id": run_id}

    caminho = os.path.join(PASTA_BASE, nome_arquivo)
    df = pd.DataFrame([linha])

    _salvar_dataframe(df, caminho)

    print(f"\n✅ Base de backtesting salva em: {caminho}")


def salvar_execucao(linha: dict, nome_arquivo: str = "execucoes.csv"):
    """Salva um registro de metadados de execução (run_id, config ativa,
    versões de bibliotecas/modelos, timestamp) — usado pelo módulo
    `experimento.py` para garantir reprodutibilidade entre execuções."""
    if not linha:
        return

    garantir_pasta_base()

    caminho = os.path.join(PASTA_BASE, nome_arquivo)
    df = pd.DataFrame([linha])

    _salvar_dataframe(df, caminho)

    print(f"📝 Metadados da execução registrados em: {caminho}")


def carregar_base_backtesting(nome_arquivo: str = "base_backtesting.csv", deduplicar: bool = True):
    """Carrega a base de backtesting salva, removendo duplicatas por padrão.

    Duplicatas acontecem sempre que o modo em lote é rodado mais de uma vez
    sem limpar `base_dados/` entre as execuções (ex: um piloto, depois uma
    correção de bug, gerando linhas para a MESMA janela ticker+período mais
    de uma vez). Sem deduplicar, essas linhas repetidas contaminam qualquer
    análise que dependa de ordenação cronológica única por ativo — em
    especial o baseline de momentum, que pode parecer artificialmente quase
    perfeito ao comparar uma janela com uma cópia quase idêntica de si
    mesma vinda de outra execução, em vez da semana anterior de verdade.

    Quando há duplicatas (mesmo ticker + mesma data_inicio_noticias + mesma
    data_fim_noticias), mantém apenas a linha da execução MAIS RECENTE
    (maior `data_execucao`).
    """
    caminho = os.path.join(PASTA_BASE, nome_arquivo)

    if not os.path.exists(caminho):
        return None

    df = pd.read_csv(caminho, encoding="utf-8-sig")

    if not deduplicar or df.empty:
        return df

    chave_janela = ["ticker", "data_inicio_noticias", "data_fim_noticias"]

    if not all(c in df.columns for c in chave_janela) or "data_execucao" not in df.columns:
        return df

    df_ordenado = df.copy()
    df_ordenado["_data_execucao_dt"] = pd.to_datetime(df_ordenado["data_execucao"], errors="coerce")
    df_ordenado = df_ordenado.sort_values("_data_execucao_dt")

    n_duplicatas = int(df_ordenado.duplicated(subset=chave_janela, keep="last").sum())

    df_dedup = df_ordenado.drop_duplicates(subset=chave_janela, keep="last").drop(columns=["_data_execucao_dt"])

    if n_duplicatas > 0:
        print(f"ℹ️  {n_duplicatas} linha(s) duplicada(s) removida(s) de {nome_arquivo} "
              f"(mesma janela ticker+período repetida entre execuções — mantida a mais recente).")

    return df_dedup.reset_index(drop=True)

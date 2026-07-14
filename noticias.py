import re
import feedparser
from datetime import datetime, timedelta
from urllib.parse import quote


def _normalizar_titulo(titulo: str) -> str:
    """Normaliza um título de notícia para fins de comparação/deduplicação
    (não altera o título original salvo na base de dados — só é usado
    internamente para decidir se duas notícias são 'a mesma')."""
    return re.sub(r"\s+", " ", titulo.strip().lower())


def buscar_noticias(termo_busca: str, intervalo: str = "7d", quantidade: int = 10):
    """Busca notícias recentes no Google News RSS.

    Retorna uma tupla (lista_de_noticias, quantidade_descartada_por_duplicidade).
    A deduplicação aqui é só INTRA-busca: o Google News às vezes retorna a
    mesma notícia mais de uma vez (reposts de agregadores diferentes com o
    mesmo título) dentro do mesmo resultado de busca.
    """
    termo_fmt = quote(termo_busca)

    url = (
        f"https://news.google.com/rss/search?"
        f"q={termo_fmt}+when:{intervalo}"
        f"&hl=pt-BR&gl=BR&ceid=BR:pt-419"
    )

    feed = feedparser.parse(url)
    noticias = []
    titulos_vistos = set()
    descartadas_duplicadas = 0

    for entry in feed.entries:
        if len(noticias) >= quantidade:
            break

        titulo = entry.title.rsplit(" - ", 1)[0]
        titulo_norm = _normalizar_titulo(titulo)

        if titulo_norm in titulos_vistos:
            descartadas_duplicadas += 1
            continue

        titulos_vistos.add(titulo_norm)

        fonte = entry.source.get("title", "Desconhecida") if hasattr(entry, "source") else "Desconhecida"
        data = entry.get("published", "Data desconhecida")

        noticias.append({
            "titulo": titulo,
            "fonte": fonte,
            "data": data,
            # Não aplicável neste fluxo: usa janela relativa (when:Xd), não
            # after:/before:, então não há um período fixo pra auditar contra.
            "data_verificada": None
        })

    return noticias, descartadas_duplicadas


def _parse_data_publicacao(entry):
    """Extrai a data de publicação como datetime, a partir do campo
    estruturado do feed (`published_parsed`) — mais confiável do que tentar
    reinterpretar a string de texto (`published`), que vem em formatos
    variados dependendo da fonte."""
    published_parsed = entry.get("published_parsed")

    if not published_parsed:
        return None

    return datetime(*published_parsed[:6])


def _dentro_do_periodo(data_publicacao, data_inicio: str, data_fim: str, margem_dias: int):
    """Verifica se a data de publicação está dentro de [data_inicio, data_fim],
    com uma margem de tolerância.

    Retorna:
    - True  -> confirmado dentro do período;
    - False -> confirmado FORA do período;
    - None  -> não foi possível determinar (sem data estruturada no feed).

    A margem de tolerância existe porque o Google News RSS reporta datas em
    GMT e os operadores after:/before: da busca do Google nem sempre batem
    exatamente com a data de publicação reportada no feed — é uma limitação
    conhecida e documentada do RSS do Google News, não um bug do nosso código.
    """
    if data_publicacao is None:
        return None

    dt_inicio = datetime.strptime(data_inicio, "%Y-%m-%d") - timedelta(days=margem_dias)
    dt_fim = datetime.strptime(data_fim, "%Y-%m-%d") + timedelta(days=margem_dias)

    return dt_inicio <= data_publicacao <= dt_fim


def buscar_noticias_historicas(
    termo_busca: str,
    data_inicio: str,
    data_fim: str,
    quantidade: int = 10,
    validar_periodo: bool = True,
    margem_dias: int = 1,
    verbose: bool = True,
    titulos_ja_processados: set | None = None
):
    """Busca notícias antigas usando operadores after e before do Google News.

    LIMITAÇÃO CONHECIDA DO GOOGLE NEWS RSS (validação de período): os
    operadores after:/before: NÃO garantem que a notícia retornada tenha sido
    de fato publicada dentro do período pedido. Por isso, cada notícia é
    auditada aqui contra sua própria data de publicação reportada no feed
    (`published_parsed`):

    - notícias CONFIRMADAMENTE fora do período são descartadas (evita
      contaminar o backtesting com notícias de fora da janela, o que seria
      uma forma de look-ahead bias / vazamento de dados);
    - notícias sem data verificável são mantidas, mas marcadas com
      `data_verificada=None`, deixando visível na base de dados que aquele
      registro não pôde ser auditado.

    DEDUPLICAÇÃO: duas camadas.
    1. Intra-busca: remove notícias com título idêntico dentro do mesmo
       resultado de busca (mesmo problema de reposts do Google News).
    2. Entre janelas do mesmo ativo (opcional, via `titulos_ja_processados`):
       se o MESMO título já apareceu numa janela semanal anterior deste
       mesmo ativo no mesmo lote, é descartado aqui também. Isso existe
       porque a imprecisão dos operadores after:/before: pode fazer a mesma
       notícia "vazar" para a janela seguinte — sem isso, o mesmo sinal de
       sentimento contaminaria duas semanas diferentes do experimento.
       Passe um `set()` vazio criado fora do loop de janelas (um por ativo)
       para ativar essa checagem; ele é atualizado em código (side effect).

    Retorna uma tupla (lista_de_noticias, descartadas_fora_periodo, descartadas_duplicadas).
    """
    query = f"{termo_busca} after:{data_inicio} before:{data_fim}"
    termo_fmt = quote(query)

    url = (
        f"https://news.google.com/rss/search?"
        f"q={termo_fmt}"
        f"&hl=pt-BR&gl=BR&ceid=BR:pt-419"
    )

    feed = feedparser.parse(url)
    noticias = []
    titulos_desta_busca = set()
    descartadas_fora_periodo = 0
    descartadas_duplicadas = 0

    # Quando vamos validar (e possivelmente descartar), olhamos mais
    # candidatos do que `quantidade`, pra compensar o descarte esperado
    # (tanto por período quanto por duplicidade).
    candidatos = feed.entries[: quantidade * 3] if validar_periodo else feed.entries[:quantidade]

    for entry in candidatos:
        if len(noticias) >= quantidade:
            break

        titulo = entry.title.rsplit(" - ", 1)[0]
        titulo_norm = _normalizar_titulo(titulo)

        if titulo_norm in titulos_desta_busca:
            descartadas_duplicadas += 1
            continue

        if titulos_ja_processados is not None and titulo_norm in titulos_ja_processados:
            descartadas_duplicadas += 1
            continue

        fonte = entry.source.get("title", "Desconhecida") if hasattr(entry, "source") else "Desconhecida"
        data_str = entry.get("published", "Data desconhecida")

        data_verificada = None

        if validar_periodo:
            data_publicacao = _parse_data_publicacao(entry)
            dentro = _dentro_do_periodo(data_publicacao, data_inicio, data_fim, margem_dias)

            if dentro is False:
                descartadas_fora_periodo += 1
                continue

            data_verificada = dentro  # True (confirmado) ou None (não verificável)

        titulos_desta_busca.add(titulo_norm)

        if titulos_ja_processados is not None:
            titulos_ja_processados.add(titulo_norm)

        noticias.append({
            "titulo": titulo,
            "fonte": fonte,
            "data": data_str,
            "data_verificada": data_verificada
        })

    if verbose:
        if descartadas_fora_periodo > 0:
            print(
                f"   ℹ️  {descartadas_fora_periodo} notícia(s) descartada(s) por estarem "
                f"confirmadamente fora do período solicitado (limitação conhecida do RSS do Google News)."
            )
        if descartadas_duplicadas > 0:
            print(f"   ℹ️  {descartadas_duplicadas} notícia(s) duplicada(s) descartada(s).")

    return noticias, descartadas_fora_periodo, descartadas_duplicadas

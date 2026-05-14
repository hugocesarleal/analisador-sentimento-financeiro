import feedparser
from urllib.parse import quote


def buscar_noticias(termo_busca: str, intervalo: str = "7d", quantidade: int = 10) -> list[dict]:
    """Busca notícias recentes no Google News RSS."""
    termo_fmt = quote(termo_busca)

    url = (
        f"https://news.google.com/rss/search?"
        f"q={termo_fmt}+when:{intervalo}"
        f"&hl=pt-BR&gl=BR&ceid=BR:pt-419"
    )

    feed = feedparser.parse(url)
    noticias = []

    for entry in feed.entries[:quantidade]:
        titulo = entry.title.rsplit(" - ", 1)[0]
        fonte = entry.source.get("title", "Desconhecida") if hasattr(entry, "source") else "Desconhecida"
        data = entry.get("published", "Data desconhecida")

        noticias.append({
            "titulo": titulo,
            "fonte": fonte,
            "data": data
        })

    return noticias


def buscar_noticias_historicas(
    termo_busca: str,
    data_inicio: str,
    data_fim: str,
    quantidade: int = 10
) -> list[dict]:
    """Busca notícias antigas usando operadores after e before do Google News."""
    query = f"{termo_busca} after:{data_inicio} before:{data_fim}"
    termo_fmt = quote(query)

    url = (
        f"https://news.google.com/rss/search?"
        f"q={termo_fmt}"
        f"&hl=pt-BR&gl=BR&ceid=BR:pt-419"
    )

    feed = feedparser.parse(url)
    noticias = []

    for entry in feed.entries[:quantidade]:
        titulo = entry.title.rsplit(" - ", 1)[0]
        fonte = entry.source.get("title", "Desconhecida") if hasattr(entry, "source") else "Desconhecida"
        data = entry.get("published", "Data desconhecida")

        noticias.append({
            "titulo": titulo,
            "fonte": fonte,
            "data": data
        })

    return noticias
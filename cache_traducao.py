import json
import os

from config import PASTA_BASE, USAR_CACHE_TRADUCAO

CAMINHO_CACHE = os.path.join(PASTA_BASE, "cache_traducoes.json")

_cache_em_memoria: dict | None = None


def _carregar_cache() -> dict:
    """Carrega o cache do disco na primeira vez que for necessário, e depois
    mantém em memória para o resto da execução (evita reler o arquivo a cada
    tradução)."""
    global _cache_em_memoria

    if _cache_em_memoria is not None:
        return _cache_em_memoria

    if os.path.exists(CAMINHO_CACHE):
        try:
            with open(CAMINHO_CACHE, "r", encoding="utf-8") as f:
                _cache_em_memoria = json.load(f)
        except (json.JSONDecodeError, OSError):
            _cache_em_memoria = {}
    else:
        _cache_em_memoria = {}

    return _cache_em_memoria


def obter_traducao_cacheada(texto_pt: str) -> str | None:
    """Retorna a tradução já cacheada para este texto, ou None se ainda não
    foi traduzido antes.

    O cache é CUMULATIVO entre todas as execuções (não é por run_id) porque
    a tradução de um texto não depende de quando ou em qual experimento ela
    foi feita — é uma propriedade do próprio texto, não da execução."""
    if not USAR_CACHE_TRADUCAO:
        return None

    return _carregar_cache().get(texto_pt)


def salvar_traducao_no_cache(texto_pt: str, texto_en: str):
    """Persiste uma nova tradução no cache em disco, pra ficar disponível
    imediatamente (mesmo que o processo seja interrompido no meio de um
    experimento em lote longo)."""
    if not USAR_CACHE_TRADUCAO:
        return

    cache = _carregar_cache()
    cache[texto_pt] = texto_en

    os.makedirs(PASTA_BASE, exist_ok=True)

    with open(CAMINHO_CACHE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

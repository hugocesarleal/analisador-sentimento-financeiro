import pytest

import cache_traducao


@pytest.fixture
def cache_isolado(tmp_path, monkeypatch):
    monkeypatch.setattr(cache_traducao, "CAMINHO_CACHE", str(tmp_path / "cache_teste.json"))
    monkeypatch.setattr(cache_traducao, "_cache_em_memoria", None)
    monkeypatch.setattr(cache_traducao, "USAR_CACHE_TRADUCAO", True)
    yield
    monkeypatch.setattr(cache_traducao, "_cache_em_memoria", None)


class TestCacheTraducao:
    def test_texto_nao_cacheado_retorna_none(self, cache_isolado):
        assert cache_traducao.obter_traducao_cacheada("texto que nunca foi visto") is None

    def test_salvar_e_recuperar(self, cache_isolado):
        cache_traducao.salvar_traducao_no_cache("Ola mundo", "Hello world")
        assert cache_traducao.obter_traducao_cacheada("Ola mundo") == "Hello world"

    def test_persiste_em_disco_entre_recarregamentos(self, cache_isolado):
        cache_traducao.salvar_traducao_no_cache("teste", "test")
        cache_traducao._cache_em_memoria = None  # força reler do disco, simulando novo processo
        assert cache_traducao.obter_traducao_cacheada("teste") == "test"

    def test_desligado_por_config_nao_le_nem_escreve(self, cache_isolado, monkeypatch):
        monkeypatch.setattr(cache_traducao, "USAR_CACHE_TRADUCAO", False)

        cache_traducao.salvar_traducao_no_cache("Ola mundo", "Hello world")
        assert cache_traducao.obter_traducao_cacheada("Ola mundo") is None

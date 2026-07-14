import time

import noticias as noticias_mod
from noticias import (
    _parse_data_publicacao,
    _dentro_do_periodo,
    _normalizar_titulo,
    buscar_noticias_historicas,
)


def _struct(ano, mes, dia):
    return time.struct_time((ano, mes, dia, 12, 0, 0, 0, 0, 0))


class FakeSource(dict):
    def get(self, k, default=None):
        return dict.get(self, k, default)


class FakeFeedEntry(dict):
    """Mimetiza o FeedParserDict de verdade: acesso por chave E por atributo."""

    def get(self, k, default=None):
        return dict.get(self, k, default)

    def __getattr__(self, k):
        try:
            return self[k]
        except KeyError:
            raise AttributeError(k)


class FakeFeed:
    def __init__(self, entries):
        self.entries = entries


def _fake_entry(titulo, fonte, ano, mes, dia, com_data=True):
    d = {
        "title": f"{titulo} - {fonte}",
        "source": FakeSource(title=fonte),
        "published": f"{dia:02d}/{mes:02d}/{ano}",
    }
    if com_data:
        d["published_parsed"] = _struct(ano, mes, dia)
    return FakeFeedEntry(d)


class TestNormalizarTitulo:
    def test_ignora_case(self):
        assert _normalizar_titulo("Petrobras Anuncia") == _normalizar_titulo("PETROBRAS ANUNCIA")

    def test_colapsa_espacos_multiplos(self):
        assert _normalizar_titulo("A   B") == "a b"


class TestDentroDoPeriodo:
    def test_data_confirmada_dentro(self):
        dt = _parse_data_publicacao(_fake_entry("x", "y", 2026, 6, 5))
        assert _dentro_do_periodo(dt, "2026-06-01", "2026-06-08", margem_dias=1) is True

    def test_data_confirmada_fora(self):
        dt = _parse_data_publicacao(_fake_entry("x", "y", 2026, 5, 1))
        assert _dentro_do_periodo(dt, "2026-06-01", "2026-06-08", margem_dias=1) is False

    def test_sem_data_nao_verificavel(self):
        assert _dentro_do_periodo(None, "2026-06-01", "2026-06-08", margem_dias=1) is None

    def test_margem_de_tolerancia_inclui_um_dia_antes(self):
        dt = _parse_data_publicacao(_fake_entry("x", "y", 2026, 5, 31))
        assert _dentro_do_periodo(dt, "2026-06-01", "2026-06-08", margem_dias=1) is True
        assert _dentro_do_periodo(dt, "2026-06-01", "2026-06-08", margem_dias=0) is False


class TestBuscarNoticiasHistoricas:
    def test_dedup_intra_busca(self, monkeypatch):
        entries = [
            _fake_entry("Noticia Repetida", "Fonte1", 2026, 6, 2),
            _fake_entry("noticia   repetida", "Fonte2", 2026, 6, 2),
            _fake_entry("Outra Noticia", "Fonte3", 2026, 6, 3),
        ]
        monkeypatch.setattr(noticias_mod.feedparser, "parse", lambda url: FakeFeed(entries))

        noticias, descartadas_periodo, descartadas_dup = buscar_noticias_historicas(
            "termo", "2026-06-01", "2026-06-08", quantidade=10, verbose=False
        )

        assert len(noticias) == 2
        assert descartadas_dup == 1

    def test_descarta_confirmadamente_fora_do_periodo(self, monkeypatch):
        entries = [
            _fake_entry("Dentro", "F1", 2026, 6, 3),
            _fake_entry("Fora", "F2", 2026, 3, 1),
        ]
        monkeypatch.setattr(noticias_mod.feedparser, "parse", lambda url: FakeFeed(entries))

        noticias, descartadas_periodo, descartadas_dup = buscar_noticias_historicas(
            "termo", "2026-06-01", "2026-06-08", quantidade=10, verbose=False
        )

        assert len(noticias) == 1
        assert descartadas_periodo == 1

    def test_mantem_sem_data_verificavel_mas_marca(self, monkeypatch):
        entries = [_fake_entry("Sem data", "F1", 2026, 6, 3, com_data=False)]
        monkeypatch.setattr(noticias_mod.feedparser, "parse", lambda url: FakeFeed(entries))

        noticias, descartadas_periodo, _ = buscar_noticias_historicas(
            "termo", "2026-06-01", "2026-06-08", quantidade=10, verbose=False
        )

        assert len(noticias) == 1
        assert noticias[0]["data_verificada"] is None
        assert descartadas_periodo == 0

    def test_dedup_entre_janelas_do_mesmo_ativo(self, monkeypatch):
        titulos_ativo = set()

        entries_semana1 = [_fake_entry("Noticia A", "F1", 2026, 6, 2)]
        monkeypatch.setattr(noticias_mod.feedparser, "parse", lambda url: FakeFeed(entries_semana1))
        n1, _, d1 = buscar_noticias_historicas(
            "t", "2026-06-01", "2026-06-08", quantidade=10,
            titulos_ja_processados=titulos_ativo, verbose=False
        )
        assert len(n1) == 1 and d1 == 0

        # mesma notícia "vaza" pra semana seguinte (imprecisão do RSS)
        entries_semana2 = [_fake_entry("Noticia A", "F1", 2026, 6, 2)]
        monkeypatch.setattr(noticias_mod.feedparser, "parse", lambda url: FakeFeed(entries_semana2))
        n2, _, d2 = buscar_noticias_historicas(
            "t", "2026-06-08", "2026-06-15", quantidade=10,
            titulos_ja_processados=titulos_ativo, verbose=False
        )
        assert len(n2) == 0 and d2 == 1

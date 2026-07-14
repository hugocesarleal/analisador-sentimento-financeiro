import pandas as pd
import pytest

import base_dados
from base_dados import salvar_base_noticias, salvar_base_backtesting, salvar_execucao


@pytest.fixture
def pasta_temporaria(tmp_path, monkeypatch):
    monkeypatch.setattr(base_dados, "PASTA_BASE", str(tmp_path))
    return tmp_path


class TestMigracaoDeSchema:
    def test_run_id_adicionado_preserva_linhas_antigas_sem_a_coluna(self, pasta_temporaria):
        caminho = pasta_temporaria / "base_noticias_sentimento.csv"
        pd.DataFrame([{"titulo_noticia": "Antiga", "score_finbert": 0.5}]).to_csv(
            caminho, index=False, encoding="utf-8-sig"
        )

        salvar_base_noticias(
            [{"titulo_noticia": "Nova", "score_finbert": 0.8}],
            run_id="abc123",
            nome_arquivo="base_noticias_sentimento.csv"
        )

        df = pd.read_csv(caminho, encoding="utf-8-sig")

        assert len(df) == 2
        assert "run_id" in df.columns
        assert df.iloc[1]["run_id"] == "abc123"
        assert pd.isna(df.iloc[0]["run_id"])
        # nenhuma coluna antiga foi perdida na migração
        assert "titulo_noticia" in df.columns
        assert "score_finbert" in df.columns

    def test_append_rapido_quando_schema_ja_bate(self, pasta_temporaria):
        salvar_base_backtesting({"ticker": "A", "acerto_finbert": True}, run_id="run1")
        salvar_base_backtesting({"ticker": "B", "acerto_finbert": False}, run_id="run2")

        caminho = pasta_temporaria / "base_backtesting.csv"
        df = pd.read_csv(caminho, encoding="utf-8-sig")

        assert len(df) == 2
        assert list(df["run_id"]) == ["run1", "run2"]

    def test_salvar_execucao_cria_arquivo(self, pasta_temporaria):
        salvar_execucao({"run_id": "x1", "tipo_execucao": "teste"})

        caminho = pasta_temporaria / "execucoes.csv"
        assert caminho.exists()

        df = pd.read_csv(caminho, encoding="utf-8-sig")
        assert df.iloc[0]["run_id"] == "x1"

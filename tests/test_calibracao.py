import pandas as pd

from calibracao import _dividir_calibracao_teste, _score_para_recomendacao, _avaliar_recomendacoes


class TestDividirCalibracaoTeste:
    def test_divisao_cronologica_sem_sobreposicao(self):
        df = pd.DataFrame({
            "data_fim_noticias": pd.date_range("2025-01-01", periods=100, freq="7D").astype(str),
            "score_finbert_medio": range(100),
            "variacao_pct": range(100),
        })
        calib, teste = _dividir_calibracao_teste(df, proporcao_teste=0.3)

        assert len(calib) == 70
        assert len(teste) == 30
        assert pd.to_datetime(calib["data_fim_noticias"]).max() < pd.to_datetime(teste["data_fim_noticias"]).min()


class TestScoreParaRecomendacao:
    def test_comprar(self):
        assert _score_para_recomendacao(0.5, 0.15) == "COMPRAR"

    def test_vender(self):
        assert _score_para_recomendacao(-0.5, 0.15) == "VENDER"

    def test_neutro(self):
        assert _score_para_recomendacao(0.05, 0.15) == "NEUTRO / AGUARDAR"


class TestAvaliarRecomendacoes:
    def test_acuracia_100_por_cento(self):
        df = pd.DataFrame({
            "score_finbert_medio": [0.5, -0.5],
            "variacao_pct": [10, -10],
        })
        acc, n = _avaliar_recomendacoes(df, limiar=0.15, limiar_neutro_pct=5, coluna_score="score_finbert_medio")
        assert acc == 1.0
        assert n == 2

    def test_ignora_linhas_com_valores_ausentes(self):
        df = pd.DataFrame({
            "score_finbert_medio": [0.5, None, -0.5],
            "variacao_pct": [10, 5, -10],
        })
        acc, n = _avaliar_recomendacoes(df, limiar=0.15, limiar_neutro_pct=5, coluna_score="score_finbert_medio")
        assert n == 2

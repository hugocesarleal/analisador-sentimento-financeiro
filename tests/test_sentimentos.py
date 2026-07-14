import pytest

from sentimentos import (
    calcular_score_individual_finbert,
    calcular_score_individual_pysentimiento,
    calcular_score_finbert,
    calcular_score_pysentimiento,
    score_para_recomendacao,
)


class TestScoreIndividualFinbert:
    def test_positivo(self):
        assert calcular_score_individual_finbert({"label": "positive", "score": 0.9}) == 0.9

    def test_negativo(self):
        assert calcular_score_individual_finbert({"label": "negative", "score": 0.8}) == -0.8

    def test_neutro_e_sempre_zero(self):
        assert calcular_score_individual_finbert({"label": "neutral", "score": 0.95}) == 0.0

    def test_case_insensitive(self):
        assert calcular_score_individual_finbert({"label": "POSITIVE", "score": 0.7}) == 0.7


class TestScoreIndividualPysentimiento:
    def test_none_retorna_none(self):
        assert calcular_score_individual_pysentimiento(None) is None

    def test_calculo_pos_menos_neg(self):
        resultado = calcular_score_individual_pysentimiento({"pos": 0.7, "neg": 0.2, "neu": 0.1})
        assert resultado == pytest.approx(0.5)


class TestScoreParaRecomendacao:
    def test_comprar_acima_do_limiar(self):
        assert score_para_recomendacao(0.5, limiar=0.15) == "COMPRAR"

    def test_vender_abaixo_do_limiar_negativo(self):
        assert score_para_recomendacao(-0.5, limiar=0.15) == "VENDER"

    def test_neutro_dentro_da_zona(self):
        assert score_para_recomendacao(0.05, limiar=0.15) == "NEUTRO / AGUARDAR"

    def test_limite_exato_nao_conta_como_comprar(self):
        # score == limiar não deve virar COMPRAR (a comparação é > estrito)
        assert score_para_recomendacao(0.15, limiar=0.15) == "NEUTRO / AGUARDAR"


class TestScoreFinbertMedio:
    def test_lista_vazia_retorna_zero(self):
        assert calcular_score_finbert([]) == 0.0

    def test_media_correta(self):
        resultados = [
            {"label": "positive", "score": 1.0},
            {"label": "negative", "score": 1.0},
        ]
        assert calcular_score_finbert(resultados) == pytest.approx(0.0)


class TestScorePysentimientoMedio:
    def test_lista_vazia_retorna_zero(self):
        assert calcular_score_pysentimiento([]) == 0.0

    def test_media_correta(self):
        resultados = [
            {"pos": 0.8, "neg": 0.1, "neu": 0.1},
            {"pos": 0.2, "neg": 0.7, "neu": 0.1},
        ]
        # scores individuais: 0.7 e -0.5 -> média = 0.1
        assert calcular_score_pysentimiento(resultados) == pytest.approx(0.1)

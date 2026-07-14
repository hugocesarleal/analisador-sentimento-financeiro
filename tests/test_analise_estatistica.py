import pandas as pd
import pytest

from analise_estatistica import (
    intervalo_confianca_wilson,
    teste_binomial_normal as calcular_teste_binomial_normal,
    teste_mcnemar as calcular_teste_mcnemar,
    calcular_baseline_aleatorio,
    calcular_baseline_buy_and_hold,
    calcular_baseline_momentum,
)


class TestIntervaloConfiancaWilson:
    def test_intervalo_contem_o_ponto_central_em_50_por_cento(self):
        low, high = intervalo_confianca_wilson(50, 100)
        assert low < 0.5 < high

    def test_100_de_100_limite_superior_e_1(self):
        low, high = intervalo_confianca_wilson(100, 100)
        assert high == pytest.approx(1.0)

    def test_zero_de_dez_nao_e_negativo(self):
        low, high = intervalo_confianca_wilson(0, 10)
        assert low >= 0

    def test_total_zero_retorna_none(self):
        assert intervalo_confianca_wilson(0, 0) == (None, None)


class TestTesteBinomialNormal:
    def test_igual_ao_nulo_nao_e_significativo(self):
        z, p = calcular_teste_binomial_normal(50, 100, 0.5)
        assert p > 0.05

    def test_muito_diferente_do_nulo_e_significativo(self):
        z, p = calcular_teste_binomial_normal(90, 100, 0.5)
        assert p < 0.001


class TestTesteMcnemar:
    def test_concordancia_total_da_p_igual_a_1(self):
        a = pd.Series([True] * 10)
        b = pd.Series([True] * 10)
        stat, p = calcular_teste_mcnemar(a, b)
        assert p == 1.0

    def test_divergencia_grande_e_significativa(self):
        a = pd.Series([True] * 20 + [False] * 5)
        b = pd.Series([False] * 20 + [False] * 5)
        stat, p = calcular_teste_mcnemar(a, b)
        assert p < 0.05


class TestBaselineAleatorio:
    def test_calculo_conhecido(self):
        df = pd.DataFrame({"variacao": [10, -8, 3, -3, 12, -15]})
        resultado = calcular_baseline_aleatorio(df, "variacao", limiar_neutro=5)
        assert resultado == pytest.approx(8 / 18)


class TestBaselineBuyAndHold:
    def test_metade_positivo(self):
        df = pd.DataFrame({"variacao": [10, -8, 3, -3, 12, -15]})
        assert calcular_baseline_buy_and_hold(df, "variacao") == pytest.approx(0.5)


class TestBaselineMomentum:
    def test_calculo_conhecido_com_zona_neutra(self):
        df = pd.DataFrame({
            "ticker": ["A"] * 6,
            "data_fim_noticias": pd.date_range("2026-01-01", periods=6, freq="7D"),
            "variacao": [10, -8, 3, -3, 12, -15],
        })
        resultado = calcular_baseline_momentum(df, "variacao", limiar_neutro=5)
        assert resultado == pytest.approx(0.2)

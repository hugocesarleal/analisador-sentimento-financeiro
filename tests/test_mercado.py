import pandas as pd
import pytest

from mercado import variacao_da_janela, avaliar_backtesting


class TestVariacaoDaJanela:
    def test_recorte_correto(self):
        datas = pd.date_range("2025-01-01", "2025-01-31", freq="D")
        precos = pd.DataFrame({"Close": [100 + i for i in range(len(datas))]}, index=datas)

        resultado = variacao_da_janela(precos, "2025-01-05", "2025-01-12")

        assert resultado is not None
        assert resultado["preco_inicio"] == 104
        assert resultado["preco_fim"] == 111
        assert resultado["variacao_pct"] == pytest.approx((111 - 104) / 104 * 100)

    def test_janela_fora_do_range_retorna_none(self):
        datas = pd.date_range("2025-01-01", "2025-01-31", freq="D")
        precos = pd.DataFrame({"Close": [100] * len(datas)}, index=datas)

        assert variacao_da_janela(precos, "2026-01-01", "2026-01-08") is None

    def test_dataframe_none_retorna_none(self):
        assert variacao_da_janela(None, "2025-01-01", "2025-01-08") is None

    def test_dataframe_vazio_retorna_none(self):
        vazio = pd.DataFrame({"Close": []})
        assert variacao_da_janela(vazio, "2025-01-01", "2025-01-08") is None


class TestAvaliarBacktesting:
    def test_comprar_com_alta_acerta(self):
        resultado = avaliar_backtesting("COMPRAR", 5.0)
        assert resultado["acertou"] is True
        assert resultado["ganho_pct"] == 5.0

    def test_comprar_com_queda_erra(self):
        resultado = avaliar_backtesting("COMPRAR", -3.0)
        assert resultado["acertou"] is False
        assert resultado["ganho_pct"] == -3.0

    def test_vender_com_queda_acerta(self):
        resultado = avaliar_backtesting("VENDER", -4.0)
        assert resultado["acertou"] is True
        assert resultado["ganho_pct"] == 4.0

    def test_vender_com_alta_erra(self):
        resultado = avaliar_backtesting("VENDER", 4.0)
        assert resultado["acertou"] is False

    def test_neutro_dentro_da_margem_acerta(self):
        resultado = avaliar_backtesting("NEUTRO / AGUARDAR", 2.0)
        assert resultado["acertou"] is True

    def test_neutro_fora_da_margem_erra(self):
        resultado = avaliar_backtesting("NEUTRO / AGUARDAR", 8.0)
        assert resultado["acertou"] is False

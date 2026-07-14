from datetime import datetime, timedelta

from pipelines import gerar_janelas_semanais


class TestGerarJanelasSemanais:
    def test_nenhuma_janela_ultrapassa_o_limite(self):
        fim = datetime(2026, 7, 10)
        inicio = fim - timedelta(days=365)
        janelas = gerar_janelas_semanais(inicio, fim, granularidade_dias=7)

        assert len(janelas) > 0
        for j in janelas:
            data_fim_preco = datetime.strptime(j["data_fim_preco"], "%Y-%m-%d")
            assert data_fim_preco <= fim

    def test_continuidade_noticia_para_preco(self):
        fim = datetime(2026, 7, 10)
        inicio = fim - timedelta(days=30)
        janelas = gerar_janelas_semanais(inicio, fim, granularidade_dias=7)

        for j in janelas:
            assert j["data_fim_noticias"] == j["data_ini_preco"]

    def test_quantidade_esperada_para_um_ano(self):
        fim = datetime(2026, 7, 10)
        inicio = fim - timedelta(days=365)
        janelas = gerar_janelas_semanais(inicio, fim, granularidade_dias=7)

        # ~365/7 - 1 (a última semana de preço precisa caber dentro do limite)
        assert 45 <= len(janelas) <= 52

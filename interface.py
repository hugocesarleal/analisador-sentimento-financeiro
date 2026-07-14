import tkinter as tk
from tkcalendar import Calendar
from config import ATIVOS


def separador(char="═", largura=70):
    print(char * largura)


def menu_ativo() -> dict:
    separador()
    print("  SELEÇÃO DE ATIVO")
    separador()

    for k, v in ATIVOS.items():
        ticker_str = f"({v['ticker']})" if v["ticker"] else ""
        print(f"  [{k}] {v['nome']} {ticker_str}")

    separador()

    while True:
        escolha = input("Digite o número do ativo: ").strip()

        if escolha in ATIVOS:
            ativo = ATIVOS[escolha].copy()

            if ativo["ticker"] is None:
                ativo["nome"] = input("Nome da empresa/ativo: ").strip()
                ativo["ticker"] = input("Ticker Yahoo Finance (ex: XPTO3.SA): ").strip().upper()
                ativo["busca"] = input("Termos de busca para notícias: ").strip()

            return ativo

        print("  Opção inválida. Tente novamente.")


def menu_intervalo() -> str:
    opcoes = {
        "1": "1d",
        "2": "3d",
        "3": "7d",
        "4": "30d"
    }

    separador()
    print("  INTERVALO DE TEMPO DAS NOTÍCIAS")
    separador()
    print("  [1] Último dia")
    print("  [2] Últimos 3 dias")
    print("  [3] Última semana (7 dias)  ← recomendado")
    print("  [4] Último mês (30 dias)")
    separador()

    while True:
        escolha = input("Escolha: ").strip()

        if escolha in opcoes:
            return opcoes[escolha]

        print("  Opção inválida.")


def menu_comparativo() -> bool:
    separador()
    print("  MODO COMPARATIVO")
    separador()
    print("  [1] ATIVADO  — usa PySentimiento + FinBERT e compara os dois")
    print("  [2] DESATIVADO — usa apenas FinBERT")
    separador()

    while True:
        escolha = input("Escolha: ").strip()

        if escolha == "1":
            return True

        if escolha == "2":
            return False

        print("  Opção inválida.")


def selecionar_data_visual(titulo="Selecione uma data"):
    """Abre uma janela pop-up com calendário para o usuário escolher a data."""
    root = tk.Tk()
    root.title(titulo)
    root.geometry("300x300")

    root.attributes("-topmost", True)
    root.eval("tk::PlaceWindow . center")

    cal = Calendar(root, selectmode="day", date_pattern="yyyy-mm-dd")
    cal.pack(pady=20, fill="both", expand=True)

    data_escolhida = [None]

    def confirmar():
        data_escolhida[0] = cal.get_date()
        root.destroy()

    btn = tk.Button(root, text="Confirmar Data", command=confirmar, bg="lightblue")
    btn.pack(pady=10)

    root.mainloop()

    return data_escolhida[0]


def exibir_analise_noticia(i, noticia, res_finbert, res_py, titulo_en):
    separador("─")
    print(f"  Notícia {i}: {noticia['titulo']}")
    print(f"  Fonte: {noticia['fonte']}  |  {noticia['data']}")

    if res_py:
        print(f"  Tradução (EN): {titulo_en}")

    separador("─")

    if res_py:
        label_py = res_py["label"]
        emoji_py = "📈" if label_py == "POS" else ("📉" if label_py == "NEG" else "➡️")

        print(
            f"  PySentimiento : {emoji_py} {label_py:3s}  | "
            f"POS: {res_py['pos']:.2f}  "
            f"NEG: {res_py['neg']:.2f}  "
            f"NEU: {res_py['neu']:.2f}"
        )

    label_fb = res_finbert["label"].upper()
    emoji_fb = "📈" if label_fb == "POSITIVE" else ("📉" if label_fb == "NEGATIVE" else "➡️")

    print(
        f"  FinBERT       : {emoji_fb} {label_fb:8s}  | "
        f"Confiança: {res_finbert['score']:.4f}"
    )


def exibir_resumo(
    ativo_nome,
    n_noticias,
    score_fb,
    rec_fb,
    score_py,
    rec_py,
    usar_comparativo
):
    separador("═")
    print(f"  RESUMO — {ativo_nome.upper()}  ({n_noticias} notícias analisadas)")
    separador("═")

    if usar_comparativo and score_py is not None:
        print(f"  Score PySentimiento : {score_py:+.4f}")
        print(f"  Score FinBERT       : {score_fb:+.4f}")
        separador("─")

        rec_emoji_py = (
            "🟢 COMPRAR" if rec_py == "COMPRAR"
            else ("🔴 VENDER" if rec_py == "VENDER" else "🟡 NEUTRO")
        )

        rec_emoji_fb = (
            "🟢 COMPRAR" if rec_fb == "COMPRAR"
            else ("🔴 VENDER" if rec_fb == "VENDER" else "🟡 NEUTRO")
        )

        print(f"  Recomendação PySentimiento : {rec_emoji_py}")
        print(f"  Recomendação FinBERT       : {rec_emoji_fb}")

        if rec_py == rec_fb:
            print(f"\n  ✅ CONSENSO entre os modelos: {rec_emoji_fb}")
        else:
            print("\n  ⚠️  DIVERGÊNCIA entre os modelos — use o FinBERT como referência principal.")

    else:
        print(f"  Score FinBERT : {score_fb:+.4f}")
        separador("─")

        rec_emoji = (
            "🟢 COMPRAR" if rec_fb == "COMPRAR"
            else ("🔴 VENDER" if rec_fb == "VENDER" else "🟡 NEUTRO")
        )

        print(f"  Recomendação  : {rec_emoji}")

    separador("═")


def exibir_backtesting(
    ativo_nome,
    ticker,
    dados_historicos,
    recomendacao_fb,
    recomendacao_py,
    usar_comparativo
):
    from mercado import avaliar_backtesting

    separador("═")
    print(f"  BACKTESTING — {ativo_nome} ({ticker})")
    separador("═")

    print(f"  Período analisado : {dados_historicos['data_inicio']} → {dados_historicos['data_fim']}")
    print(f"  Preço no início   : R$ {dados_historicos['preco_inicio']:.2f}")
    print(f"  Preço no fim      : R$ {dados_historicos['preco_fim']:.2f}")

    var = dados_historicos["variacao_pct"]
    sinal = "+" if var >= 0 else ""

    print(f"  Variação real     : {sinal}{var:.2f}%")
    separador("─")

    def linha_bt(modelo, recomendacao):
        bt = avaliar_backtesting(recomendacao, var)
        ganho = bt["ganho_pct"]
        sinal_g = "+" if ganho >= 0 else ""
        resultado = "✅ ACERTO" if bt["acertou"] else "❌ ERRO"

        print(
            f"  {modelo:20s}: Recomendou {recomendacao:18s} "
            f"→ Resultado {sinal_g}{ganho:.2f}%  {resultado}"
        )

    linha_bt("FinBERT", recomendacao_fb)

    if usar_comparativo and recomendacao_py:
        linha_bt("PySentimiento", recomendacao_py)

    separador("═")

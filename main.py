from modelos import carregar_modelos
from interface import separador, menu_comparativo
from pipelines import executar_analise_atual, executar_backtesting, executar_backtesting_lote
from validacao_sentimento import gerar_relatorio_concordancia
from calibracao import calibrar_ambos_modelos
from analise_estatistica import gerar_relatorio_estatistico


def main():
    separador("═")
    print("  ANALISADOR DE SENTIMENTO FINANCEIRO")
    print("  Computação Aplicada ao Mercado Financeiro")
    separador("═")

    usar_comparativo = menu_comparativo()
    modelos = carregar_modelos(usar_comparativo)

    while True:
        separador()
        print("  MENU PRINCIPAL")
        separador()
        print("  [1] Análise Atual (Recomendação baseada em notícias de hoje)")
        print("  [2] Backtesting (Testar o modelo com dados do passado)")
        print("  [3] Alterar modo comparativo (recarrega modelos)")
        print("  [4] Experimento em lote (backtesting automatizado — todos os ativos)")
        print("  [5] Relatório de confiabilidade (concordância entre modelos)")
        print("  [6] Calibrar limiar de recomendação (usa dados de backtesting já salvos)")
        print("  [7] Relatório estatístico (baselines + retorno excedente + significância)")
        print("  [0] Sair")
        separador()

        opcao = input("Escolha: ").strip()

        if opcao == "1":
            executar_analise_atual(modelos, usar_comparativo)

        elif opcao == "2":
            executar_backtesting(modelos, usar_comparativo)

        elif opcao == "3":
            usar_comparativo = menu_comparativo()
            modelos = carregar_modelos(usar_comparativo)

        elif opcao == "4":
            executar_backtesting_lote(modelos, usar_comparativo)

        elif opcao == "5":
            gerar_relatorio_concordancia()

        elif opcao == "6":
            calibrar_ambos_modelos()

        elif opcao == "7":
            gerar_relatorio_estatistico()

        elif opcao == "0":
            print("\n  Encerrando. Até logo!\n")
            break

        else:
            print("  Opção inválida.")

        print()


if __name__ == "__main__":
    main()

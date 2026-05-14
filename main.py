from modelos import carregar_modelos
from interface import separador, menu_comparativo
from pipelines import executar_analise_atual, executar_backtesting


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

        elif opcao == "0":
            print("\n  Encerrando. Até logo!\n")
            break

        else:
            print("  Opção inválida.")

        print()


if __name__ == "__main__":
    main()
# Analisador de Sentimento Financeiro

Sistema em Python para análise de sentimento em notícias financeiras de ativos negociados na B3, com geração de recomendações experimentais (compra/venda/neutralidade) e validação via backtesting histórico contra dados de preço.

Desenvolvido no contexto da disciplina de Tópicos Especiais em Engenharia de Computação.

> **Aviso:** projeto de finalidade acadêmica e experimental. As recomendações geradas não constituem recomendação financeira.

---

## Visão geral

O sistema executa o seguinte fluxo:

1. Coleta de notícias recentes ou históricas associadas a um ativo, via Google News RSS.
2. Tradução automática dos títulos para o inglês (pré-requisito de idioma do FinBERT).
3. Inferência de sentimento por um ou dois modelos de NLP.
4. Agregação dos scores individuais em um score consolidado e mapeamento para uma recomendação (`COMPRAR` / `VENDER` / `NEUTRO`).
5. Validação opcional da recomendação contra a variação de preço observada no período (backtesting).
6. Execução em lote da etapa 5 para múltiplos ativos e múltiplas janelas temporais consecutivas.
7. Geração de relatórios de concordância entre modelos, calibração de limiar de decisão, e avaliação estatística contra baselines de comparação.

## Modelos de sentimento

| Modelo | Domínio | Idioma | Observação |
|---|---|---|---|
| FinBERT (`ProsusAI/finbert`) | Financeiro | Inglês | Requer tradução prévia do título |
| PySentimiento | Geral | Português | Usado apenas em modo comparativo |

## Fontes de dados

| Dado | Fonte |
|---|---|
| Notícias | Google News RSS |
| Preços históricos | [`yfinance`](https://pypi.org/project/yfinance/) |
| Benchmark de mercado | Ibovespa (`^BVSP`) |

## Ativos pré-configurados

| Empresa | Ticker | Termo de busca |
|---|---|---|
| Petrobras | `PETR4.SA` | Petrobras PETR4 |
| Vale | `VALE3.SA` | Vale VALE3 |
| Itaú Unibanco | `ITUB4.SA` | Itaú Unibanco ITUB4 |
| Ambev | `ABEV3.SA` | Ambev ABEV3 |
| Magazine Luiza | `MGLU3.SA` | Magazine Luiza MGLU3 |
| Bradesco | `BBDC4.SA` | Bradesco BBDC4 |
| WEG | `WEGE3.SA` | WEG WEGE3 |
| Embraer | `EMBJ3.SA` | Embraer |

Ativos adicionais podem ser especificados em tempo de execução (nome, ticker Yahoo Finance, termo de busca).

---

## Requisitos

- Python 3.10+
- Dependências listadas em `requirements.txt`

## Instalação

```bash
pip install -r requirements.txt --break-system-packages
```

## Execução

```bash
python main.py
```

Na inicialização, o programa solicita se o modo comparativo (FinBERT + PySentimiento) deve ser ativado, carrega os modelos correspondentes, e expõe o menu principal:

| Opção | Fluxo |
|---|---|
| `1` | Análise atual — recomendação baseada em notícias recentes |
| `2` | Backtesting manual — testa o modelo em um período histórico definido via calendário |
| `3` | Alternar modo comparativo (recarrega os modelos) |
| `4` | Experimento em lote — backtesting automatizado para todos os ativos configurados |
| `5` | Relatório de concordância entre FinBERT e PySentimiento |
| `6` | Calibração do limiar de recomendação |
| `7` | Relatório estatístico — baselines de comparação e testes de significância |
| `0` | Encerrar |

## Testes

```bash
pytest tests/ -v
```

---

## Estrutura do repositório

```text
.
├── main.py                    # Ponto de entrada e menu principal
├── config.py                  # Configuração centralizada (ativos, limiares, parâmetros do lote)
├── modelos.py                 # Carregamento dos modelos de NLP
├── noticias.py                 # Coleta de notícias (Google News RSS)
├── sentimentos.py               # Tradução e inferência de sentimento
├── mercado.py                    # Obtenção de preços e avaliação de backtesting
├── pipelines.py                  # Orquestração dos fluxos de análise e backtesting
├── interface.py                  # Camada de interação (CLI e calendário via tkinter)
├── experimento.py                 # Identificação e metadados de execução (run_id)
├── base_dados.py                  # Persistência dos resultados em CSV
├── cache_traducao.py               # Cache de traduções em disco
├── logging_config.py                # Configuração de logging
├── validacao_sentimento.py           # Relatório de concordância entre modelos
├── calibracao.py                      # Calibração do limiar de recomendação
├── analise_estatistica.py              # Baselines e testes estatísticos
├── tests/                               # Suíte de testes (pytest)
├── requirements.txt
└── base_dados/                          # Diretório gerado em tempo de execução
    ├── base_noticias_sentimento.csv
    ├── base_backtesting.csv
    ├── execucoes.csv
    ├── cache_traducoes.json
    └── pipeline.log
```

## Stack

Python · `transformers` · `pysentimiento` · `deep-translator` · `feedparser` · `yfinance` · `pandas` · `tkcalendar` · `pytest`
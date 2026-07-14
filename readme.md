# Analisador de Sentimento Financeiro

Sistema em Python para análise de sentimento em notícias financeiras, com validação por backtesting histórico e comparação contra ativos da B3. Desenvolvido para a disciplina de Tópicos Especiais em Engenharia de Computação.

O sistema coleta notícias sobre ativos financeiros, aplica modelos de análise de sentimento, gera recomendações experimentais de compra/venda/neutralidade, e valida essas recomendações de forma estatisticamente rigorosa — com baselines de comparação, retorno ajustado por benchmark, e testes de significância.

> **Aviso:** este projeto tem finalidade exclusivamente acadêmica e experimental. As recomendações geradas não devem ser interpretadas como recomendação financeira real.

---

## Objetivo

Investigar, de forma experimental e estatisticamente rigorosa, se o sentimento de notícias financeiras carrega informação preditiva sobre a variação futura de preços de ativos da B3 — e, caso carregue, se esse sinal é melhor do que alternativas triviais (chute aleatório, comprar-e-segurar, ou simplesmente seguir a tendência recente do próprio preço).

---

## Funcionalidades

O sistema é operado via `main.py`, com 7 fluxos:

| # | Fluxo | O que faz |
|---|---|---|
| 1 | Análise Atual | Recomendação a partir de notícias recentes de um ativo |
| 2 | Backtesting (manual) | Testa o modelo num período histórico escolhido via calendário |
| 3 | Alterar modo comparativo | Liga/desliga o PySentimiento (recarrega os modelos) |
| 4 | Experimento em lote | Backtesting automatizado, todos os ativos, janelas semanais consecutivas cobrindo até 12 meses — sem intervenção manual |
| 5 | Relatório de confiabilidade | Concordância FinBERT × PySentimiento (Kappa de Cohen, matriz de confusão) |
| 6 | Calibração de limiar | Encontra o melhor limiar de recomendação por busca em grade, com separação cronológica calibração/teste |
| 7 | Relatório estatístico | Retorno excedente vs. Ibovespa, baselines (aleatório/buy-and-hold/momentum), testes de significância pareados |

### Modo Comparativo

Compara dois modelos de sentimento em paralelo:

- **FinBERT** (`ProsusAI/finbert`) — especializado em textos financeiros em inglês; os títulos coletados em português são traduzidos antes da análise.
- **PySentimiento** — modelo geral de sentimento em português.

**Achado relevante já documentado (ver Limitações):** os dois modelos concordam entre si em nível estatisticamente equivalente ao acaso (Kappa de Cohen ≈ 0,01 em ~3.700 notícias analisadas). Não devem ser tratados como intercambiáveis.

---

## Fontes de Dados

- **Notícias**: Google News RSS. Cada notícia histórica tem sua data de publicação auditada contra o período pedido (o Google News não garante que os operadores `after:`/`before:` retornem só notícias daquele período) — notícias confirmadamente fora do período são descartadas, e o descarte é reportado.
- **Preços**: `yfinance` (Yahoo Finance).
- **Benchmark**: Ibovespa (`^BVSP`), usado para calcular retorno excedente.

---

## Ativos Disponíveis

| Empresa | Ticker | Termo de busca |
|---|---|---|
| Petrobras | PETR4.SA | Petrobras PETR4 |
| Vale | VALE3.SA | Vale VALE3 |
| Itaú Unibanco | ITUB4.SA | Itaú Unibanco ITUB4 |
| Ambev | ABEV3.SA | Ambev ABEV3 |
| Magazine Luiza | MGLU3.SA | Magazine Luiza MGLU3 |
| Bradesco | BBDC4.SA | Bradesco BBDC4 |
| WEG | WEGE3.SA | WEG WEGE3 |
| Embraer | EMBJ3.SA | Embraer |

> A Embraer trocou de código na B3 em 03/11/2025 (`EMBR3` → `EMBJ3`). O termo de busca usa só o nome da empresa porque o período do experimento atravessa essa transição, e notícias antigas ainda mencionam o código anterior.

Também é possível informar manualmente outro ativo (nome, ticker Yahoo Finance, termo de busca).

---

## Metodologia — o que este projeto faz para ser cientificamente defensável

Isso não é só uma coleção de scripts: cada um dos pontos abaixo resolve um problema metodológico específico.

- **Reprodutibilidade**: toda execução gera um `run_id`, e a configuração + versões de bibliotecas usadas são registradas em `base_dados/execucoes.csv`. Traduções são cacheadas (`cache_traducao.py`), então o mesmo texto sempre traduz para o mesmo resultado entre execuções.
- **Confiabilidade da coleta**: datas de notícias históricas são auditadas contra o período pedido (limitação conhecida do RSS do Google News); duplicatas são removidas tanto dentro de uma busca quanto entre janelas semanais consecutivas do mesmo ativo; cobertura (% da quantidade de notícias pedida que foi de fato obtida) é medida e reportada.
- **Qualidade do sentimento**: concordância entre FinBERT e PySentimiento é medida via Kappa de Cohen (não só % de concordância bruta, que infla a percepção de confiabilidade quando uma classe domina a amostra). Documentado como limitação: isto mede consistência entre modelos, não acurácia contra gabarito humano (rotulagem manual foi deliberadamente deixada fora do escopo deste projeto).
- **Calibração do limiar de decisão**: o limiar que converte score em COMPRAR/VENDER/NEUTRO é escolhido por busca em grade num conjunto de calibração, e reportado honestamente num conjunto de teste **cronologicamente posterior e nunca visto durante a busca** — evita inflar a acurácia reportada.
- **Rigor estatístico**: taxa de acerto é sempre acompanhada de intervalo de confiança (Wilson), comparada contra baselines (aleatório calculado analiticamente, buy-and-hold, momentum de preço da própria janela anterior), com testes pareados de McNemar (mais apropriado que testes independentes, já que modelo e baseline avaliam as mesmas janelas) — e contra o retorno **excedente ao Ibovespa**, não só o retorno bruto do ativo.
- **Testes automatizados**: 61 testes (`pytest`) cobrem as funções determinísticas de todo o pipeline — scores, backtesting, deduplicação, validação de datas, divisão cronológica, testes estatísticos, migração de schema do CSV.
- **Deduplicação de execuções**: se o modo em lote for rodado mais de uma vez sem limpar `base_dados/`, o carregador de dados mantém automaticamente só a execução mais recente por janela (ticker + período), evitando que resultados de tentativas antigas contaminem a análise.

---

## Resultados Preliminares

Resultado de um experimento completo (8 ativos, 12 meses, janelas semanais, N=400):

| Comparação | Retorno bruto | Retorno excedente (vs. Ibovespa) |
|---|---|---|
| Acurácia do FinBERT | 59,5% [IC 95%: 54,6–64,2%] | 62,0% [IC 95%: 57,2–66,6%] |
| Baseline aleatório | 58,9% | 61,8% |
| Baseline buy-and-hold | 54,0% | 49,0% |
| Baseline momentum | 74,5% | 82,7% |
| Modelo vs. acaso | ✅ significativo (p=0,0002) | ✅ significativo (p<0,0001) |
| Modelo vs. buy-and-hold | ❌ não significativo (p=0,076) | ✅ significativo (p<0,0001) |
| Modelo vs. momentum | ✅ significativo — **modelo perde** (p<0,0001) | ✅ significativo — **modelo perde** (p<0,0001) |

Leitura honesta: o FinBERT capta algo além do acaso, e esse sinal só se distingue de "comprar e esperar" quando isolado do movimento geral do mercado — mas em nenhum cenário ele supera a simples extrapolação da tendência recente de preço do próprio ativo (momentum). Todas essas conclusões se mantêm mesmo aplicando correção de Bonferroni para múltiplas comparações.

*(Estes números vêm de uma execução específica e servem de referência — rode o pipeline você mesmo para números atualizados; veja `GUIA_EXECUCAO.md`.)*

---

## Limitações Conhecidas

- **Sem validação contra gabarito humano**: a qualidade do sentimento extraído é aferida só indiretamente (concordância entre modelos, confiança do FinBERT), não contra rótulos humanos. Decisão deliberada de escopo, documentada para transparência.
- **Tradução automática como intermediária**: o FinBERT opera sobre títulos traduzidos automaticamente (pt→en), não sobre o português original — qualquer erro de tradução se propaga para a classificação de sentimento.
- **RSS do Google News não é uma fonte 100% confiável**: mesmo com a auditoria de datas implementada, é uma fonte de dados não oficial e sujeita a mudanças de comportamento fora do nosso controle.
- **Amostra de ativos limitada**: 8 ativos da B3, período de 12 meses — generalização para outros mercados ou horizontes de tempo não testada.
- **Sinal de sentimento perde para momentum de preço**: ver seção de Resultados acima — isto é reportado como achado, não escondido.

---

## Organização do Projeto

```text
trabalho/
│
├── main.py                     # Ponto de entrada (menu interativo)
├── config.py                   # Toda a configuração centralizada
│
├── modelos.py                  # Carregamento dos modelos de NLP
├── noticias.py                 # Coleta de notícias (Google News RSS) + validação de data + dedup
├── sentimentos.py               # Tradução + análise de sentimento + scores
├── mercado.py                   # Preços via yfinance + avaliação de backtesting
├── pipelines.py                 # Orquestração dos fluxos 1, 2 e 4 (inclui geração de janelas semanais)
├── interface.py                 # CLI + calendário (tkinter)
│
├── experimento.py                # run_id + metadados de execução (reprodutibilidade)
├── base_dados.py                 # Persistência CSV segura contra mudança de schema + deduplicação
├── cache_traducao.py             # Cache local de traduções
├── logging_config.py             # Logging persistente (falhas não ficam mais silenciosas)
│
├── validacao_sentimento.py       # Fluxo 5: concordância entre modelos
├── calibracao.py                 # Fluxo 6: calibração do limiar de recomendação
├── analise_estatistica.py        # Fluxo 7: baselines + retorno excedente + testes estatísticos
│
├── tests/                        # Suíte pytest (61 testes)
│   └── test_*.py
├── pytest.ini                    # Garante que a raiz do projeto entre no sys.path dos testes
│
├── requirements.txt
├── GUIA_EXECUCAO.md               # Passo a passo prático para rodar o experimento completo
│
└── base_dados/                   # Gerado em tempo de execução (não versionado)
    ├── base_noticias_sentimento.csv
    ├── base_backtesting.csv
    ├── base_backtesting_enriquecido.csv
    ├── execucoes.csv
    ├── cache_traducoes.json
    └── pipeline.log
```

---

## Como Rodar

```bash
pip install -r requirements.txt --break-system-packages

# Rodar a suíte de testes primeiro
pytest tests/ -v

# Rodar o programa
python main.py
```

Para o passo a passo completo de como gerar um experimento em lote e coletar todas as métricas (incluindo tempo estimado, ordem recomendada dos relatórios, e o que fazer se algo falhar no meio do caminho), veja **[`GUIA_EXECUCAO.md`](./GUIA_EXECUCAO.md)**.

---

## Stack

Python · `transformers` (FinBERT) · `pysentimiento` · `deep-translator` · `feedparser` · `yfinance` · `pandas` · `tkcalendar` · `pytest`
# Analisador de Sentimento Financeiro

Sistema desenvolvido em Python para análise de sentimento em notícias financeiras, utilizando modelos de Processamento de Linguagem Natural (PLN) e dados históricos de ativos da bolsa. O projeto tem finalidade acadêmica e foi desenvolvido para a disciplina de Tópicos Especiais em Engenharia de Computação.

O sistema coleta notícias relacionadas a ativos financeiros, aplica modelos de análise de sentimento, gera recomendações experimentais de compra, venda ou neutralidade e permite validar essas recomendações por meio de backtesting com dados históricos de preços.

> **Aviso:** este projeto possui finalidade exclusivamente acadêmica e experimental. As recomendações geradas pelo sistema não devem ser interpretadas como recomendação financeira real.

---

## Objetivo do Projeto

O objetivo do projeto é investigar, de forma experimental, a relação entre o sentimento presente em notícias financeiras e a variação posterior dos preços de ativos da bolsa.

Para isso, o sistema realiza as seguintes etapas:

- coleta de notícias financeiras;
- limpeza e organização dos dados coletados;
- tradução dos títulos das notícias para uso com o FinBERT;
- análise de sentimento com modelos de PLN;
- geração de scores numéricos;
- criação de recomendações experimentais;
- coleta de preços históricos;
- realização de backtesting;
- geração de arquivos CSV com a base de dados.

---

## Funcionalidades

O sistema possui três funcionalidades principais:

### 1. Análise Atual

Permite buscar notícias recentes sobre um ativo financeiro e gerar uma recomendação experimental com base no sentimento identificado.

A análise pode considerar intervalos como:

- último dia;
- últimos 3 dias;
- últimos 7 dias;
- últimos 30 dias.

### 2. Backtesting

Permite selecionar um período passado de notícias e comparar a recomendação gerada com a variação real do preço do ativo em um período posterior.

Esse processo permite avaliar se a recomendação baseada em sentimento foi coerente com o movimento real do mercado.

### 3. Modo Comparativo

O sistema pode comparar dois modelos de análise de sentimento:

- **FinBERT:** modelo especializado em textos financeiros em inglês;
- **PySentimiento:** modelo geral de análise de sentimentos em português.

O FinBERT é utilizado como principal referência por ser especializado no domínio financeiro.

---

## Modelos Utilizados

### FinBERT

Modelo de análise de sentimento voltado para textos financeiros. Como o FinBERT trabalha com textos em inglês, os títulos das notícias coletadas em português são traduzidos antes da análise.

### PySentimiento

Modelo de análise de sentimentos em português. É utilizado no modo comparativo para verificar possíveis diferenças entre um modelo geral em português e um modelo especializado em finanças.

---

## Fontes de Dados

O projeto utiliza duas fontes principais de dados:

### Notícias Financeiras

As notícias são coletadas por meio do Google News RSS. Para cada notícia, são armazenadas informações como:

- título;
- fonte;
- data de publicação;
- ativo relacionado;
- termo de busca utilizado.

### Dados Históricos de Preços

Os dados históricos dos ativos são obtidos com a biblioteca `yfinance`.

Para cada backtesting, o sistema coleta:

- preço inicial;
- preço final;
- data inicial real;
- data final real;
- variação percentual do ativo.

---

## Ativos Disponíveis

O sistema possui alguns ativos previamente configurados:

| Empresa | Ticker | Termo de busca |
|---|---|---|
| Petrobras | PETR4.SA | Petrobras PETR4 |
| Vale | VALE3.SA | Vale VALE3 |
| Itaú Unibanco | ITUB4.SA | Itaú Unibanco ITUB4 |
| Ambev | ABEV3.SA | Ambev ABEV3 |
| Magazine Luiza | MGLU3.SA | Magazine Luiza MGLU3 |
| Bradesco | BBDC4.SA | Bradesco BBDC4 |
| WEG | WEGE3.SA | WEG WEGE3 |
| Embraer | EMBR3.SA | Embraer EMBR3 |

Também é possível informar manualmente outro ativo, digitando o nome da empresa, o ticker no Yahoo Finance e o termo de busca desejado.

---

## Organização do Projeto

A versão modular do projeto está organizada da seguinte forma:

```text
analisador-sentimento-financeiro/
│
├── main.py
├── config.py
├── modelos.py
├── noticias.py
├── sentimentos.py
├── mercado.py
├── base_dados.py
├── interface.py
├── pipelines.py
│
└── base_dados/
    ├── base_noticias_sentimento.csv
    └── base_backtesting.csv
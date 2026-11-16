# Organizador Financeiro

Aplicação web para gerenciamento de finanças pessoais desenvolvida com Streamlit.

## Funcionalidades

- **Painel**: Visão geral com gráficos de entradas, saídas e orçamento vs realizado
- **Transações**: Registro de entradas e saídas com categorias
- **Categorias**: Gerenciamento de categorias personalizadas
- **Orçamentos**: Definição de metas de gastos por categoria (global)
- **Cartões de Crédito**: Controle de gastos no cartão com parcelas
- **Investimentos**: Acompanhamento de ações, FIIs, cryptos com cotações automáticas
- **Importação**: Importar dados via planilha Excel

## Requisitos

- Python 3.10+
- pip

## Instalação

```bash
# Clonar/acessar o projeto
cd projeto-finança

# Criar ambiente virtual
python3 -m venv venv

# Ativar ambiente virtual
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# Instalar dependências
pip install -r requirements.txt
```

## Executando

```bash
# Ativar ambiente virtual (se não estiver ativo)
source venv/bin/activate

# Executar aplicação
streamlit run app.py
```

A aplicação abrirá automaticamente no navegador em `http://localhost:8501`

## Estrutura do Projeto

```
projeto-finança/
├── app.py              # Aplicação principal Streamlit
├── database/           # Modelos e conexão com banco de dados
│   ├── __init__.py
│   ├── models.py       # Modelos SQLAlchemy (COMPARTILHADO)
│   └── connection.py   # Configuração do banco
├── mobile/             # Aplicativo Mobile (Flet)
│   ├── main.py         # Arquivo principal do aplicativo
│   ├── state.py        # Estado global e alinhamento de regras
│   ├── styles.py       # Estilização do aplicativo
│   └── views/          # Telas do aplicativo móvel
├── views/              # Telas da aplicação Web
│   ├── dashboard.py    # Painel principal
│   ├── transactions.py # Gestão de transações
│   ├── categories.py   # Gestão de categorias
│   ├── budgets.py      # Orçamentos
│   ├── credit_cards.py # Cartões de crédito
│   ├── investments.py  # Investimentos
│   └── import_data.py  # Importação de dados
├── services/           # Serviços auxiliares
│   └── stock_service.py # Cotações de ações (yfinance)
├── exemplos/           # Planilha de exemplo
├── data/               # Banco de dados SQLite
├── requirements.txt    # Dependências Python
└── README.md
```

## 📱 Aplicativo Mobile

O projeto conta também com uma versão mobile desenvolvida com o framework **Flet**, desenhada para rodar em Android e iOS. 

**Princípio de Alinhamento**: As versões Web (PC) e Mobile mantêm funcionalidades alinhadas e compartilham da mesma estrutura de banco de dados (`financas.db`) e dos mesmos modelos via SQLAlchemy.
- A sincronização de dados ocorre por meio do compartilhamento do arquivo `financas.db` (ex. sincronizando-o via Google Drive ou iCloud). 
- O Mobile herda todas as regras complexas de negócio, como contagem de períodos contábeis e categorizações.

### Executando o App Localmente

```bash
# Com o ambiente virtual ativado:
flet run mobile/main.py
```

## Como Funciona o Módulo de Investimentos

1. **Crie uma transação** com categoria "Ações", "FIIs" ou "Criptomoedas"
   - Exemplo: Descrição "Compra PETR4", Valor R$ 3.500
   
2. **Acesse a tela de Investimentos** > Aba "Transações Pendentes"
   - O sistema sugere o ticker baseado na descrição
   
3. **Informe quantidade e preço por unidade**
   - Exemplo: 100 ações a R$ 35,00 cada
   
4. **Clique em "Vincular"**
   - O sistema cria/atualiza o ativo automaticamente

5. **Atualize cotações** clicando em "Atualizar Cotações"
   - Usa yfinance para buscar preços da B3 automaticamente

## Formato de Importação (Excel)

### Aba "Transacoes"
| Coluna | Descrição |
|--------|-----------|
| Data | Data (DD/MM/AAAA) |
| Valor | Valor da transação |
| Descricao | Descrição |
| Categoria | Nome da categoria |
| Tipo | "entrada" ou "saida" |

### Aba "Cartao"
| Coluna | Descrição |
|--------|-----------|
| Data | Data (DD/MM/AAAA) |
| Valor | Valor da compra |
| Descricao | Descrição |
| Categoria | Nome da categoria |
| Parcela | Formato "1/3" |

### Aba "Investimentos"
| Coluna | Descrição |
|--------|-----------|
| Data | Data (DD/MM/AAAA) |
| Ticker | Código do ativo (PETR4, VALE3, etc) |
| Tipo | "compra" ou "venda" |
| Quantidade | Quantidade |
| Preco | Preço por unidade |

## Tecnologias

- **Streamlit**: Framework web
- **SQLAlchemy**: ORM para banco de dados
- **SQLite**: Banco de dados local
- **Plotly**: Gráficos interativos
- **Pandas**: Manipulação de dados
- **yfinance**: Cotações de ações em tempo real

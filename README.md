# Radiologia – Laudos

Aplicação Streamlit para gerenciar procedimentos radiológicos no Delta Lake (camada Gold).

## 📋 Funcionalidades

- ✅ Gerenciar **Modalidades** (TC, RM, ANGIOTC, etc.)
- ✅ Gerenciar **Descrições** (partes anatômicas/técnicas)
- ✅ Gerenciar **Procedimentos** (vinculados a modalidades e descrições)
- ✅ Ativar/desativar procedimentos
- ✅ Importar procedimentos via CSV

## 🏗️ Estrutura de Dados

### Tabelas Gold (Delta Lake)

**`radiologia_laudos_modalidades`**
- `id_modalidade` (PK, auto-increment)
- `nome_modalidade` (TC, RM, ANGIOTC, etc.)
- `ativo`, `dt_cadastro`, `dt_atualizacao`

**`radiologia_laudos_descricoes`**
- `id_descricao` (PK, auto-increment)
- `descricao` (texto da descrição)
- `ativo`, `dt_cadastro`, `dt_atualizacao`

**`radiologia_laudos_procedimentos`**
- `cd_procedimento` (PK, código do procedimento)
- `nm_procedimento` (nome do procedimento)
- `id_modalidade` (FK → modalidades)
- `id_descricao_1` a `id_descricao_7` (FK → descrições, até 7 por procedimento)
- `ativo`, `dt_cadastro`, `dt_atualizacao`

## 🚀 Como executar

### Localmente (desenvolvimento)

```bash
cd app
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

### No Databricks (produção)

#### Opção 1: Databricks Apps (recomendado)

1. **Clone o repositório no Databricks:**
   - Repos → Add Repo
   - URL: `https://github.com/eduardocaminha/radiologia-laudos.git`

2. **Configure o SQL Warehouse:**
   - Edite `app/app.yaml`
   - Atualize `DATABRICKS_HTTP_PATH` com seu warehouse

3. **Deploy via UI:**
   - Apps → Create App
   - Selecione a pasta `app/`
   - Deploy

#### Opção 2: Cluster Databricks

```python
# No notebook do cluster
%pip install -r /Workspace/Repos/radiologia-laudos/app/requirements.txt

# Configurar SQL Warehouse
import os
os.environ['DATABRICKS_HTTP_PATH'] = '/sql/1.0/warehouses/SEU_WAREHOUSE_ID'

# Executar Streamlit
!streamlit run /Workspace/Repos/radiologia-laudos/app/app.py --server.port 8501
```

## 📦 Dependências

- `streamlit` - Interface web
- `pandas` - Manipulação de dados
- `databricks-sql-connector` - Conexão com Delta Lake

## 🔄 Integração com Oracle Lake

### Job de Extração Diária ✅

A aplicação inclui um **Job Databricks** para extração automatizada de laudos do Oracle Lake (RAWZN) para Delta Lake (Bronze).

**Características:**
- ✅ Execução diária às 02:00 AM (madrugada)
- ✅ Processamento incremental (D-1)
- ✅ Join otimizado com tabela temporária
- ✅ Salvamento em Delta Lake particionado
- ✅ Idempotente (suporta reprocessamento)

**Fluxo:**
1. Busca procedimentos ativos no Gold (gerenciados via Streamlit)
2. Cria tabela temporária filtrada no Oracle
3. Join otimizado com `tb_laudo_paciente`
4. Salva laudos no Bronze (`radiologia_laudos_extraidos`)

**Documentação completa:** [`jobs/README.md`](jobs/README.md)

**Benefícios:**
- ✅ Dados sempre atualizados (carga diária)
- ✅ Performance otimizada (tabela temp + índices)
- ✅ Histórico completo no Delta Lake
- ✅ Separação de responsabilidades (batch vs. real-time)

## 📁 Estrutura do Projeto

```
radiologia-laudos/
├── README.md
├── app/                       # Aplicação Streamlit (gerenciamento)
│   ├── app.py                 # Aplicação principal
│   ├── app.yaml               # Configuração Databricks Apps
│   ├── requirements.txt       # Dependências Python
│   ├── config.py              # Configurações (schemas, tabelas)
│   ├── database/              # Módulo de banco de dados
│   │   ├── __init__.py
│   │   ├── connections.py     # Conexão SQL Warehouse
│   │   ├── queries.py         # Execução de queries
│   │   └── schema.py          # Criação de tabelas
│   └── modules/               # Módulos de funcionalidades
│       ├── __init__.py
│       ├── modalidades.py     # Gerenciar modalidades
│       ├── descricoes.py      # Gerenciar descrições
│       ├── procedimentos.py   # Gerenciar procedimentos
│       └── importar_csv.py    # Importar dados CSV
├── jobs/                      # Jobs Databricks (extração)
│   ├── README.md              # Documentação do job
│   ├── extracao_laudos_diaria.py  # Job de extração diária
│   ├── setup_inicial.py       # Setup das tabelas Bronze
│   └── job_config.yaml        # Configuração do job
└── .gitignore
```

## 👥 Contribuindo

1. Clone o repositório
2. Crie uma branch para sua feature
3. Faça commit das mudanças
4. Abra um Pull Request

## 📝 Licença

Uso interno - Hapvida

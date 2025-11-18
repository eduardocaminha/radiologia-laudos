# Radiologia – Laudos

Aplicação Streamlit para organizar o download e a preparação de laudos provenientes do lake Oracle, consolidando os dados em uma tabela Delta (camada Gold) com as colunas `NM_PROCEDIMENTO`, `CD_PROCEDIMENTO`, `MODALIDADE` e `DESCRICAO_1` … `DESCRICAO_7`.

O app consome o arquivo `procedimentos.csv` (delimitado por `;`), filtra modalidades específicas (inicialmente **TC** e **ANGIOTC**), gera a lista única das descrições e oferece um template de `CREATE TABLE` pronto para ser executado no Lakehouse.

## Estrutura

```
radiologia-laudos/
├── README.md
└── app/
    ├── app.py
    ├── app.yaml
    └── requirements.txt
```

## Como executar localmente

```bash
cd radiologia-laudos/app
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

O app tenta carregar automaticamente `../procedimentos.csv`. Caso o arquivo esteja em outro caminho, utilize o uploader na interface.

## Publicação (Databricks)

### Pré-requisitos
- **Cluster Databricks** (NÃO Serverless) com Spark
- Driver JDBC Oracle em `/Workspace/Libraries/DatalakeConnector/ojdbc11.jar`
- Acesso ao scope `INNOVATION_RAW` no Secrets Manager
- SQL Warehouse configurado para Delta Lake

### Setup

1. Faça upload desta pasta para o workspace
2. No cluster, instale as dependências:
   ```bash
   %pip install -r /Workspace/path/to/app/requirements.txt
   ```
3. Configure a variável de ambiente:
   ```python
   import os
   os.environ['DATABRICKS_HTTP_PATH'] = '/sql/1.0/warehouses/<seu_warehouse_id>'
   ```
4. Execute o Streamlit:
   ```bash
   streamlit run /Workspace/path/to/app/app.py --server.port 8501
   ```

### Como funciona

- **Delta Lake (Gold)**: Usa SQL Warehouse via `databricks-sql-connector`
- **Oracle Lake (RAWZN)**: Usa JayDeBeAPI + JDBC (mesma abordagem da biblioteca Lake)
- Credenciais obtidas via `dbutils.secrets` automaticamente
- Conexão Oracle configurada como ReadOnly com prefetch de 10k linhas

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

### Opção 1: Databricks Apps (Serverless)

**Limitação:** Busca no Oracle Lake não funciona (sem Java, sem rede privada).

**Setup:**
1. Clone o repo no Databricks: `Repos → Add Repo → https://github.com/eduardocaminha/radiologia-laudos.git`
2. Configure `app/app.yaml` com senha Oracle
3. Deploy via UI do Databricks Apps
4. **Funcionalidades disponíveis:**
   - ✅ Gerenciar tabelas Gold (Delta Lake)
   - ✅ Cadastrar/editar procedimentos, modalidades, descrições
   - ❌ Buscar procedimentos no Oracle Lake

**Para habilitar busca no Oracle:** Use Opção 2 (Serving Endpoint).

---

### Opção 2: Serving Endpoint + Databricks Apps

**Solução completa:** API roda em cluster com Java, Streamlit chama via HTTP.

#### 2.1. Deploy do Endpoint (no cluster)

```python
# Clone o repo
# Repos → Add Repo → https://github.com/eduardocaminha/radiologia-laudos.git

# Instalar dependências
%pip install -r /Workspace/Repos/radiologia-laudos/oracle_endpoint/requirements.txt

# Iniciar endpoint
%run /Workspace/Repos/radiologia-laudos/oracle_endpoint/endpoint.py
```

**Pré-requisitos do cluster:**
- ✅ Java instalado
- ✅ Acesso à rede privada Oracle (IP 10.20.1.79)
- ✅ Driver JDBC em `/Workspace/Libraries/DatalakeConnector/ojdbc11.jar`
- ✅ Acesso ao secret `INNOVATION_RAW/USR_PROD_INFORMATICA_SAUDE`

#### 2.2. Configurar Streamlit App

Adicione ao `app/app.yaml`:
```yaml
env:
  - name: 'ORACLE_ENDPOINT_URL'
    value: 'http://seu-cluster-url:8080'
```

#### 2.3. Endpoints disponíveis

| Método | Path | Descrição |
|--------|------|-----------|
| GET | `/health` | Health check |
| POST | `/query` | Query SQL customizada |
| GET | `/procedimento/codigo/<cd>` | Buscar por código |
| POST | `/procedimento/termo` | Buscar por termo |

**Exemplo de uso:**
```bash
curl -X POST http://endpoint:8080/procedimento/termo \
  -H "Content-Type: application/json" \
  -d '{"termo": "TOMOGRAFIA"}'
```

---

### Opção 3: Cluster Normal (sem Apps)

Execute Streamlit diretamente em cluster com Java:

```python
# No notebook do cluster
%pip install -r /Workspace/Repos/radiologia-laudos/app/requirements.txt

# Configurar SQL Warehouse
import os
os.environ['DATABRICKS_HTTP_PATH'] = '/sql/1.0/warehouses/<warehouse_id>'

# Executar Streamlit
!streamlit run /Workspace/Repos/radiologia-laudos/app/app.py --server.port 8501
```

**Funcionalidades:**
- ✅ Tudo funciona (Delta Lake + Oracle Lake)
- ✅ Conexão direta via JayDeBeAPI
- ❌ Cluster precisa ficar ligado (custo)

---

## Como funciona

### Conexões
- **Delta Lake (Gold)**: SQL Warehouse via `databricks-sql-connector`
- **Oracle Lake (RAWZN)**: 
  - Em cluster: JayDeBeAPI direto
  - Em Apps: HTTP via Serving Endpoint
  - Detecção automática via `ORACLE_ENDPOINT_URL`

### Estrutura de dados
- **Modalidades**: TC, RM, ANGIOTC, etc.
- **Descrições**: Partes anatômicas/técnicas dos exames
- **Procedimentos**: Vinculam código Oracle + modalidade + descrições

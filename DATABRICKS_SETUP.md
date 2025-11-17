# 🚀 Setup no Databricks

Este guia explica como rodar o aplicativo Streamlit no Databricks com acesso ao Oracle Lake.

## 📋 Pré-requisitos

1. Acesso ao Databricks Workspace
2. Permissões para acessar o Oracle Lake (RAWZN)
3. Acesso aos secrets do scope `INNOVATION_RAW`

## 🔧 Configuração

### 1. Upload dos arquivos

Faça upload da pasta `app/` para o Databricks Workspace:

```
/Workspace/Users/<seu_usuario>/radiologia-laudos/app/
```

### 2. Criar notebook de inicialização

Crie um notebook Databricks com o seguinte conteúdo:

```python
# COMMAND ----------
# MAGIC %md
# MAGIC # Radiologia Laudos - Streamlit App
# MAGIC 
# MAGIC Aplicativo para gerenciamento de procedimentos radiológicos

# COMMAND ----------
# MAGIC %md
# MAGIC ## 1. Carregar biblioteca Lake

# COMMAND ----------
%run /Workspace/Libraries/Lake

# COMMAND ----------
# MAGIC %md
# MAGIC ## 2. Conectar ao Oracle Lake

# COMMAND ----------
# Conectar ao datalake
connect_to_datalake(
    username="USR_PROD_INFORMATICA_SAUDE",
    password=dbutils.secrets.get(scope="INNOVATION_RAW", key="USR_PROD_INFORMATICA_SAUDE"),
    layer="RAWZN",
    level="LOW",
    dbx_secret_scope="INNOVATION_RAW"
)

print("✅ Conexão com Oracle Lake estabelecida!")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 3. Configurar variáveis de ambiente

# COMMAND ----------
import os

# Configurar HTTP Path do SQL Warehouse
os.environ['DATABRICKS_HTTP_PATH'] = '/sql/1.0/warehouses/<seu_warehouse_id>'

print("✅ Variáveis de ambiente configuradas!")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 4. Iniciar Streamlit

# COMMAND ----------
# Instalar Streamlit se necessário
%pip install streamlit

# COMMAND ----------
# Iniciar o app
import sys
sys.path.append('/Workspace/Users/<seu_usuario>/radiologia-laudos/app')

# Executar Streamlit
!streamlit run /Workspace/Users/<seu_usuario>/radiologia-laudos/app/app.py --server.port 8501
```

## 🔍 Como funciona

### Ambiente Local vs Databricks

O código detecta automaticamente o ambiente:

```python
# Em connections.py
IS_DATABRICKS = os.path.exists('/Workspace')
```

**No Databricks:**
- Usa `spark.sql()` para consultar o Oracle Lake
- Acessa `RAWZN.RAW_HSP_TB_PROCEDIMENTO` diretamente
- Converte Spark DataFrame para Pandas

**No ambiente local:**
- Retorna dados mockados
- Permite desenvolvimento sem conexão ao Oracle
- Mostra warning informativo

### Busca no Oracle Lake

```python
# Busca por código
df = buscar_procedimento_oracle(cd_procedimento=12345)

# Busca por termo
df = buscar_procedimento_oracle(termo_busca="TOMOGRAFIA")
```

**Query executada no Databricks:**
```sql
SELECT DISTINCT CD_PROCEDIMENTO, NM_PROCEDIMENTO
FROM RAWZN.RAW_HSP_TB_PROCEDIMENTO
WHERE UPPER(NM_PROCEDIMENTO) LIKE UPPER('%TOMOGRAFIA%')
ORDER BY NM_PROCEDIMENTO
LIMIT 100
```

## 📊 Tabelas Acessadas

### Oracle Lake (RAWZN)
- `RAW_HSP_TB_PROCEDIMENTO` - Procedimentos do HSP

### Delta Lake (Gold)
- `radiologia_laudos_modalidades` - Modalidades radiológicas
- `radiologia_laudos_descricoes` - Descrições anatômicas/técnicas
- `radiologia_laudos_procedimentos` - Procedimentos cadastrados

## 🔐 Segurança

- Credenciais armazenadas no Databricks Secrets
- Scope: `INNOVATION_RAW`
- Key: `USR_PROD_INFORMATICA_SAUDE`
- Acesso apenas via biblioteca Lake

## 🐛 Troubleshooting

### Erro: "Biblioteca Lake não carregada"
**Solução:** Execute `%run /Workspace/Libraries/Lake` antes de iniciar o app

### Erro: "spark not defined"
**Solução:** Certifique-se de estar em um notebook Databricks com cluster ativo

### Erro: "Tabela não encontrada"
**Solução:** Verifique permissões de acesso ao schema RAWZN

### App mostra dados mockados no Databricks
**Solução:** Verifique se `IS_DATABRICKS = True` e se o Spark está disponível

## 📝 Notas

- O app funciona tanto localmente (com mocks) quanto no Databricks (com dados reais)
- A detecção de ambiente é automática
- Não é necessário modificar código entre ambientes
- Use o ambiente local para desenvolvimento de UI
- Use o Databricks para testes com dados reais

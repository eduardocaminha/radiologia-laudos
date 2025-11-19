# Oracle Lake Serving Endpoint

API HTTP para executar queries no Oracle Lake a partir do Databricks Apps.

## 🎯 Por que precisamos disso?

Databricks Apps (serverless) não consegue conectar diretamente ao Oracle porque:
- Não tem Java (JVM) instalado
- Não tem acesso à rede privada Oracle (IP 10.20.1.79)
- Filesystem read-only

**Solução:** Criar um Serving Endpoint que roda em cluster normal (com Java e rede privada) e expõe API HTTP.

## 📋 Setup

### 1. Fazer upload dos arquivos

Faça upload desta pasta `oracle_endpoint/` para o Databricks Workspace:
```
/Workspace/Users/seu_usuario/oracle_endpoint/
```

### 2. Criar cluster com Java

Crie ou use um cluster existente que tenha:
- ✅ Java instalado
- ✅ Acesso à rede privada Oracle
- ✅ Acesso ao driver JDBC em `/Workspace/Libraries/DatalakeConnector/ojdbc11.jar`

### 3. Configurar senha Oracle

No cluster, configure a senha como Spark config:
```python
spark.conf.set("spark.oracle.password", "SENHA_AQUI")
```

Ou via cluster settings:
```
Spark Config:
spark.oracle.password {{secrets/INNOVATION_RAW/USR_PROD_INFORMATICA_SAUDE}}
```

### 4. Instalar dependências

No notebook do cluster:
```python
%pip install -r /Workspace/Users/seu_usuario/oracle_endpoint/requirements.txt
```

### 5. Iniciar o endpoint

```python
%run /Workspace/Users/seu_usuario/oracle_endpoint/endpoint.py
```

Ou criar um Job que mantém o endpoint rodando.

### 6. Obter URL do endpoint

Após deploy, você terá uma URL tipo:
```
https://adb-xxxxx.azuredatabricks.net/serving-endpoints/oracle-lake-api/invocations
```

### 7. Configurar no Streamlit App

Adicione ao `app.yaml`:
```yaml
env:
  - name: 'ORACLE_ENDPOINT_URL'
    value: 'https://adb-xxxxx.azuredatabricks.net/serving-endpoints/oracle-lake-api'
```

## 🧪 Testar o endpoint

### Health check
```bash
curl https://seu-endpoint/health
```

### Query customizada
```bash
curl -X POST https://seu-endpoint/query \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT * FROM RAWZN.RAW_HSP_TB_PROCEDIMENTO WHERE CD_PROCEDIMENTO = 123"}'
```

### Buscar por código
```bash
curl https://seu-endpoint/procedimento/codigo/123
```

### Buscar por termo
```bash
curl -X POST https://seu-endpoint/procedimento/termo \
  -H "Content-Type: application/json" \
  -d '{"termo": "TOMOGRAFIA"}'
```

## 📊 Endpoints disponíveis

| Método | Path | Descrição |
|--------|------|-----------|
| GET | `/health` | Health check |
| POST | `/query` | Executar query SQL customizada |
| GET | `/procedimento/codigo/<cd>` | Buscar procedimento por código |
| POST | `/procedimento/termo` | Buscar procedimento por termo |

## 🔧 Troubleshooting

### Erro: "No JVM found"
- Certifique-se que o cluster tem Java instalado
- Verifique se o driver JDBC está em `/Workspace/Libraries/DatalakeConnector/ojdbc11.jar`

### Erro: "ORA-12170: Cannot connect"
- Verifique se o cluster tem acesso à rede privada Oracle
- Teste conectividade: `ping 10.20.1.79`

### Erro: "Password not configured"
- Configure `spark.oracle.password` no cluster
- Ou use secrets: `{{secrets/INNOVATION_RAW/USR_PROD_INFORMATICA_SAUDE}}`

## 💰 Custos

- O cluster precisa ficar rodando para o endpoint funcionar
- Considere usar cluster com autoscaling
- Ou configurar para desligar em horários de baixo uso

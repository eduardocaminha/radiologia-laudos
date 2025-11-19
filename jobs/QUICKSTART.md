# 🚀 Quick Start - Job de Extração de Laudos

Guia rápido para configurar e executar o job de extração diária de laudos radiológicos.

## ⚡ Setup em 5 Passos

### 1️⃣ Upload dos Arquivos

```bash
# Via Databricks CLI
databricks workspace import-dir \
  jobs/ \
  /Workspace/Repos/radiologia-laudos/jobs/
```

Ou via UI:
- Workspace → Repos → Add Repo
- URL: `https://github.com/eduardocaminha/radiologia-laudos.git`

### 2️⃣ Executar Setup Inicial

No Databricks, abra e execute o notebook:
```
/Workspace/Repos/radiologia-laudos/jobs/setup_inicial
```

Isso cria:
- ✅ Schema Bronze
- ✅ Tabela `radiologia_laudos_extraidos`
- ✅ Tabela `radiologia_laudos_metricas_job`
- ✅ Views de monitoramento

### 3️⃣ Cadastrar Procedimentos

Use a aplicação Streamlit para cadastrar os procedimentos que deseja monitorar:

1. Acesse o Streamlit App
2. Vá em **🔬 Procedimentos**
3. Cadastre os códigos de procedimentos radiológicos
4. Marque como **Ativo**

### 4️⃣ Criar o Job

**Opção A: Via UI (mais fácil)**

1. Jobs → Create Job
2. Nome: `radiologia_extracao_laudos_diaria`
3. Task:
   - Type: **Notebook**
   - Path: `/Workspace/Repos/radiologia-laudos/jobs/extracao_laudos_diaria`
4. Cluster:
   - Spark Version: `13.3.x-scala2.12`
   - Workers: `2`
   - Node Type: `Standard_DS3_v2`
5. Schedule:
   - Cron: `0 0 2 * * ?`
   - Timezone: `America/Sao_Paulo`
6. Save

**Opção B: Via CLI (automatizado)**

```bash
databricks jobs create --json-file jobs/job_config.yaml
```

### 5️⃣ Testar Execução

Execute manualmente para testar:

```bash
# Via CLI
databricks jobs run-now --job-id <JOB_ID>

# Ou via UI
Jobs → radiologia_extracao_laudos_diaria → Run Now
```

## ✅ Verificação

Após a primeira execução, verifique:

```sql
-- Ver laudos extraídos
SELECT * FROM innovation_dev.bronze.radiologia_laudos_extraidos
LIMIT 10;

-- Ver métricas do job
SELECT * FROM innovation_dev.bronze.vw_radiologia_job_monitoramento
LIMIT 5;

-- Estatísticas diárias
SELECT * FROM innovation_dev.bronze.vw_radiologia_laudos_diario
ORDER BY dt_processamento DESC
LIMIT 7;
```

## 📊 Monitoramento Diário

### Dashboard Simples

```sql
-- Últimas 7 execuções
SELECT 
    data_processamento,
    laudos_extraidos,
    procedimentos_ativos,
    status
FROM innovation_dev.bronze.vw_radiologia_job_monitoramento
LIMIT 7;

-- Volume por dia (últimos 30 dias)
SELECT 
    dt_processamento,
    total_laudos,
    pacientes_unicos
FROM innovation_dev.bronze.vw_radiologia_laudos_diario
WHERE dt_processamento >= CURRENT_DATE - INTERVAL 30 DAYS
ORDER BY dt_processamento DESC;
```

### Alertas

Configure alertas no Databricks SQL para:
- ⚠️ Job falhou
- ⚠️ Nenhum laudo extraído
- ⚠️ Volume muito baixo (< 100 laudos)

## 🔧 Parâmetros Úteis

### Reprocessar Período Específico

```python
# Reprocessar última semana
data_processamento = "2024-01-31"
modo_execucao = "reprocessamento"
dias_retroativos = "7"
```

### Execução Manual com Parâmetros

```bash
databricks jobs run-now --job-id <JOB_ID> \
  --notebook-params '{
    "data_processamento": "2024-01-15",
    "modo_execucao": "reprocessamento",
    "dias_retroativos": "30"
  }'
```

## 🎯 Próximos Passos

Após o job estar rodando:

1. **Monitorar** execuções diárias
2. **Criar camada Silver** (limpeza/normalização)
3. **Criar camada Gold** (agregações/métricas)
4. **Dashboards** de análise
5. **ML Pipeline** (extração de entidades)

## 📞 Troubleshooting Rápido

| Problema | Solução |
|----------|---------|
| Nenhum procedimento ativo | Cadastrar procedimentos no Streamlit |
| Erro de conexão Oracle | Verificar acesso de rede do cluster |
| Driver JDBC não encontrado | Upload do `ojdbc11.jar` |
| Job muito lento | Aumentar workers (2 → 4) |
| Duplicatas na tabela | Usar modo `reprocessamento` |

## 📚 Documentação Completa

- [README do Job](README.md) - Documentação detalhada
- [Notebook de Extração](extracao_laudos_diaria.py) - Código do job
- [Configuração](job_config.yaml) - YAML do job

---

**Dúvidas?** eduardo.caminha@hapvida.com.br

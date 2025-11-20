# Job: Extração Diária de Laudos Radiológicos

Job Databricks para extração automatizada de laudos de procedimentos radiológicos do Oracle Lake (RAWZN) para Delta Lake (Bronze).

## 🎯 Objetivo

Alimentar diariamente uma tabela Bronze no Delta Lake com laudos de exames radiológicos, permitindo análises e processamentos posteriores (Silver/Gold).

## 📋 Características

### Processamento
- ✅ **Batch diário**: Execução automática às 02:00 AM
- ✅ **Incremental**: Processa apenas D-1 (dia anterior)
- ✅ **Idempotente**: Suporta reprocessamento sem duplicatas
- ✅ **Otimizado**: Tabela temporária + índices para joins eficientes

### Dados
- **Origem**: Oracle Lake (RAWZN) - **HSP + PSC**
  - `RAW_HSP_TB_PROCEDIMENTO_REALIZADO` + `RAW_PSC_TB_PROCEDIMENTO_REALIZADO`
  - `RAW_HSP_TM_ATENDIMENTO` + `RAW_PSC_TM_ATENDIMENTO`
  - `RAW_HSP_TB_LAUDO_PACIENTE` + `RAW_PSC_TB_LAUDO_PACIENTE`
- **Destino**: Delta Lake Bronze
  - `innovation_dev.bronze.radiologia_laudos_extraidos`
  - Particionado por `ano_mes` (YYYY-MM)
  
> **📌 Nota:** Busca laudos tanto de **HSP (Hospital)** quanto de **PSC (Pronto Socorro)** usando UNION ALL

### Procedimentos
- Lista dinâmica obtida do Gold: `radiologia_laudos_procedimentos`
- Apenas procedimentos **ativos** são processados
- Gerenciamento via aplicação Streamlit

## 🏗️ Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│  GOLD (Delta Lake)                                          │
│  ├─ radiologia_laudos_procedimentos (lista de códigos)     │
│  └─ radiologia_laudos_modalidades                          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  JOB DATABRICKS (02:00 AM)                                  │
│  ├─ 1. Buscar procedimentos ativos (Gold)                  │
│  ├─ 2. Criar tabela temp no Oracle (filtrada)              │
│  ├─ 3. Join no Oracle:                                     │
│  │     • temp ↔ TM_ATENDIMENTO (cd_paciente)               │
│  │     • temp ↔ TB_LAUDO_PACIENTE (laudos)                 │
│  └─ 4. Salvar em Bronze (Delta Lake)                       │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  BRONZE (Delta Lake)                                        │
│  └─ radiologia_laudos_extraidos                            │
│     ├─ Particionado por ANO_MES                            │
│     ├─ Otimizado (OPTIMIZE + Z-ORDER)                      │
│     └─ Histórico completo                                  │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Setup

### 1. Upload do Notebook

```bash
# Via Databricks CLI
databricks workspace import \
  --language PYTHON \
  --file jobs/extracao_laudos_diaria.py \
  /Workspace/Repos/radiologia-laudos/jobs/extracao_laudos_diaria
```

Ou via UI:
- Workspace → Repos → radiologia-laudos → jobs
- Upload `extracao_laudos_diaria.py`

### 2. Criar Job via UI

1. **Jobs → Create Job**
2. **Nome**: `radiologia_extracao_laudos_diaria`
3. **Task**:
   - Type: Notebook
   - Path: `/Workspace/Repos/radiologia-laudos/jobs/extracao_laudos_diaria`
4. **Cluster**:
   - Spark Version: `13.3.x-scala2.12`
   - Workers: `2` (ajustar conforme volume)
   - Node Type: `Standard_DS3_v2` ou similar
5. **Schedule**:
   - Cron: `0 0 2 * * ?`
   - Timezone: `America/Sao_Paulo`
6. **Notifications**:
   - On Failure: `seu-email@hapvida.com.br`

### 3. Criar Job via CLI (Recomendado)

```bash
# Usando o arquivo de configuração
databricks jobs create --json-file jobs/job_config.yaml
```

### 4. Pré-requisitos do Cluster

✅ **Java instalado** (para JDBC Oracle)  
✅ **Driver JDBC**: `/Workspace/Libraries/DatalakeConnector/ojdbc11.jar`  
✅ **Acesso ao Oracle Lake** (rede privada: 10.20.1.79)  
✅ **Secrets configurados**: `INNOVATION_RAW/USR_PROD_INFORMATICA_SAUDE`  
✅ **Biblioteca Lake**: `/Workspace/Libraries/Lake`

## 📊 Schema da Tabela Bronze

```sql
CREATE TABLE innovation_dev.bronze.radiologia_laudos_extraidos (
    cd_atendimento BIGINT,
    cd_ocorrencia BIGINT,
    cd_ordem BIGINT,
    accession_number STRING NOT NULL,  -- Chave única
    cd_procedimento BIGINT,
    cd_paciente BIGINT,
    ds_laudo_medico STRING,
    dt_procedimento_realizado TIMESTAMP,  -- Data + hora completa
    ano_mes STRING,  -- Particionamento (YYYY-MM)
    dt_carga TIMESTAMP,  -- Quando foi carregado
    modo_execucao STRING  -- Como foi carregado (diario/reprocessamento_historico)
)
PARTITIONED BY (ano_mes)
USING DELTA
```

**Mudanças no Schema (Nov/2025):**
- ✅ `dt_procedimento_realizado`: DATE → **TIMESTAMP** (inclui hora)
- ✅ Schema otimizado: 11 colunas (foco em dados essenciais)
- ✅ Busca laudos de **HSP + PSC** (UNION ALL)

### Colunas Principais

- **`accession_number`**: Chave única = `cd_atendimento + cd_ocorrencia + cd_ordem` (sem separadores)
  - Garante unicidade dos laudos
  - Usado no MERGE para evitar duplicatas
  - Indexado via Z-ORDER para performance

> **📌 Padrão de nomenclatura:** Todas as colunas em **minúsculo** (padrão Delta Lake)

### Colunas de Controle

- `dt_carga`: Timestamp da carga no Delta Lake (quando foi carregado)
- `modo_execucao`: `diario` ou `reprocessamento_historico` (como foi carregado)

### Controle de Duplicidades

✅ **Deduplicação em múltiplas camadas:**
1. Query Oracle: `DISTINCT` na extração
2. Spark DataFrame: `dropDuplicates(['accession_number'])`
3. Delta Lake: `MERGE` usando `accession_number` como chave
4. View de monitoramento: `vw_radiologia_laudos_duplicatas`

## 🎮 Execução

### Execução Automática (Diária)

O job roda automaticamente às **02:00 AM** (horário de Brasília) processando o dia anterior (D-1).

### Execução Manual

#### Via UI
1. Jobs → `radiologia_extracao_laudos_diaria`
2. Run Now
3. (Opcional) Sobrescrever parâmetros:
   - `data_processamento`: `2024-01-15`
   - `modo_execucao`: `reprocessamento`
   - `dias_retroativos`: `7`

#### Via CLI
```bash
# Execução padrão (D-1)
databricks jobs run-now --job-id <JOB_ID>

# Reprocessamento de período específico
databricks jobs run-now --job-id <JOB_ID> \
  --notebook-params '{
    "data_processamento": "2024-01-15",
    "modo_execucao": "reprocessamento",
    "dias_retroativos": "7"
  }'
```

## 🔧 Modos de Execução

### 1. Job Diário (Padrão)
```python
modo_execucao = "job_diario"
```
- Processa apenas **1 dia** (D-1)
- Usa `MERGE` no Delta Lake
- Ideal para execução diária automática
- Mais rápido e eficiente

### 2. Reprocessamento
```python
modo_execucao = "reprocessamento"
dias_retroativos = 7  # últimos 7 dias
```
- Processa **múltiplos dias** retroativos
- Usa `MERGE` no Delta Lake (evita duplicatas)
- Ideal para correções ou backfill
- Mais lento (devido ao merge)

## 📈 Monitoramento

### Métricas do Job

O job salva métricas em:
```sql
SELECT * FROM innovation_dev.bronze.radiologia_laudos_metricas_job
ORDER BY dt_execucao DESC
```

**Campos:**
- `data_processamento`: Data de referência
- `periodo_inicio` / `periodo_fim`: Período extraído
- `procedimentos_ativos`: Quantidade de procedimentos na lista
- `procedimentos_realizados`: Procedimentos encontrados no Oracle
- `laudos_extraidos`: Laudos salvos no Bronze
- `total_bronze`: Total acumulado na tabela Bronze
- `dt_execucao`: Timestamp da execução

### Queries de Monitoramento

```sql
-- Verificar última execução
SELECT * 
FROM innovation_dev.bronze.radiologia_laudos_metricas_job
ORDER BY dt_execucao DESC
LIMIT 1;

-- Volume por dia de carga
SELECT 
    DATE(dt_carga) as dia_carga,
    modo_execucao,
    COUNT(*) as total_laudos,
    COUNT(DISTINCT accession_number) as laudos_unicos,
    COUNT(DISTINCT cd_paciente) as pacientes_unicos,
    COUNT(DISTINCT cd_procedimento) as procedimentos_distintos
FROM innovation_dev.bronze.radiologia_laudos_extraidos
GROUP BY dia_carga, modo_execucao
ORDER BY dia_carga DESC;

-- Volume por ano/mês (usando função YEAR/MONTH)
SELECT 
    YEAR(dt_procedimento_realizado) as ano,
    MONTH(dt_procedimento_realizado) as mes,
    COUNT(*) as total_laudos
FROM innovation_dev.bronze.radiologia_laudos_extraidos
GROUP BY ano, mes
ORDER BY ano DESC, mes DESC;

-- ⚠️ VERIFICAR DUPLICATAS (deve retornar vazio!)
SELECT * 
FROM innovation_dev.bronze.vw_radiologia_laudos_duplicatas;

-- Exemplo de accession_number
SELECT 
    accession_number,
    cd_atendimento,
    cd_ocorrencia,
    cd_ordem,
    cd_procedimento,
    dt_procedimento_realizado
FROM innovation_dev.bronze.radiologia_laudos_extraidos
LIMIT 10;

-- Volume por modalidade (últimos 30 dias)
SELECT 
    p.nome_modalidade,
    COUNT(*) as total_laudos,
    COUNT(DISTINCT l.accession_number) as laudos_unicos
FROM innovation_dev.bronze.radiologia_laudos_extraidos l
INNER JOIN innovation_dev.gold.radiologia_laudos_procedimentos p
    ON l.cd_procedimento = p.cd_procedimento
WHERE l.dt_carga >= CURRENT_DATE - INTERVAL 30 DAYS
GROUP BY p.nome_modalidade
ORDER BY total_laudos DESC;

-- Verificar partições
SHOW PARTITIONS innovation_dev.bronze.radiologia_laudos_extraidos;
```

## 🔍 Troubleshooting

### Erro: "Nenhum procedimento ativo"
**Causa:** Tabela Gold vazia ou todos procedimentos inativos  
**Solução:** Cadastrar procedimentos via aplicação Streamlit

### Erro: "Nenhum procedimento realizado no período"
**Causa:** Não há dados no Oracle para o período/códigos  
**Solução:** Verificar se os códigos estão corretos e se há dados no período

### Erro: "Connection timeout Oracle"
**Causa:** Cluster sem acesso à rede privada Oracle  
**Solução:** Verificar configuração de rede do cluster

### Erro: "Driver JDBC não encontrado"
**Causa:** Driver `ojdbc11.jar` não está no path esperado  
**Solução:** Upload do driver para `/Workspace/Libraries/DatalakeConnector/`

### Job lento
**Otimizações:**
1. Aumentar número de workers (2 → 4)
2. Verificar volume de dados (considerar filtros adicionais)
3. Analisar plano de execução: `EXPLAIN` nas queries
4. Considerar Z-ORDER na tabela Bronze:
   ```sql
   OPTIMIZE innovation_dev.bronze.radiologia_laudos_extraidos
   ZORDER BY (CD_PROCEDIMENTO, DT_PROCEDIMENTO_REALIZADO)
   ```

## 🔄 Migração de Schema (Nov/2025)

### Script de Migração

Para atualizar dados existentes com timestamp completo, execute **UMA VEZ**:

```python
# Notebook: migracao_adicionar_timestamp.py
%run /Workspace/Repos/radiologia-laudos/jobs/migracao_adicionar_timestamp
```

**O que faz:**
1. ✅ Cria backup automático
2. ✅ Busca `HR_PROCEDIMENTO_REALIZADO` do Oracle
3. ✅ Combina data + hora em TIMESTAMP
4. ✅ Remove colunas `ano` e `mes`
5. ✅ Otimiza tabela Delta

**Tempo estimado:** 30-60 minutos (dependendo do volume)

### Após a Migração

1. ✅ Fazer pull dos notebooks atualizados no Databricks
2. ✅ Testar job diário com novo schema
3. ✅ (Opcional) Deletar backup após validação

---

## 🔄 Manutenção

### Otimização Regular

```sql
-- Compactar arquivos pequenos
OPTIMIZE innovation_dev.bronze.radiologia_laudos_extraidos;

-- Z-ORDER para queries por procedimento/data
OPTIMIZE innovation_dev.bronze.radiologia_laudos_extraidos
ZORDER BY (accession_number, cd_procedimento, dt_procedimento_realizado);

-- Vacuum (remover arquivos antigos > 7 dias)
VACUUM innovation_dev.bronze.radiologia_laudos_extraidos RETAIN 168 HOURS;
```

### Reprocessamento Completo

```bash
# Reprocessar últimos 30 dias
databricks jobs run-now --job-id <JOB_ID> \
  --notebook-params '{
    "data_processamento": "2024-01-31",
    "modo_execucao": "reprocessamento",
    "dias_retroativos": "30"
  }'
```

## 📝 Logs

### Visualizar Logs do Job

1. Jobs → `radiologia_extracao_laudos_diaria`
2. Runs → Selecionar execução
3. View Logs

### Logs Importantes

- ✅ Conexão Oracle estabelecida
- 📋 Quantidade de procedimentos ativos
- 🔧 Tabela temporária criada
- 🔍 Laudos extraídos
- 💾 Dados salvos no Bronze
- 📊 Métricas finais

## 🎯 Próximos Passos

Após a camada Bronze estar populada:

1. **Silver Layer**: Limpeza e normalização dos laudos
2. **Gold Layer**: Agregações e métricas de negócio
3. **ML Pipeline**: Extração de entidades (NER) dos laudos
4. **Dashboards**: Visualizações e análises

---

# 🔄 Reprocessamento Histórico

Para processar laudos de períodos anteriores, use o notebook **`reprocessamento_historico.py`**.

## 📋 Quando Usar

- ✅ **Carga inicial histórica** (ex: processar últimos 6 meses)
- ✅ **Reprocessamento após correções** (ex: bug corrigido, reprocessar dados)
- ✅ **Períodos específicos** (ex: processar apenas Janeiro/2025)
- ✅ **Recuperação de falhas** (ex: job diário falhou por 1 semana)

## 🚀 Como Usar

### 1. Configurar Parâmetros

```python
data_inicio: 2024-06-01      # Data inicial (YYYY-MM-DD)
data_fim: 2024-12-31         # Data final (YYYY-MM-DD)
tamanho_lote: 7              # Dias por lote (7, 14 ou 30)
modo_teste: false            # true = apenas conta, false = processa
```

### 2. Executar

**Via UI Databricks:**
1. Abra o notebook `reprocessamento_historico`
2. Configure os widgets no topo
3. Run All

**Via CLI:**
```bash
databricks jobs run-now --job-id <JOB_ID> \
  --notebook-params '{
    "data_inicio":"2024-06-01",
    "data_fim":"2024-12-31",
    "tamanho_lote":"7",
    "modo_teste":"false"
  }'
```

## 📊 Exemplos

### Exemplo 1: Carga Inicial (6 meses)
```python
data_inicio: 2024-06-01
data_fim: 2024-12-01
tamanho_lote: 7        # ~26 lotes de 1 semana
modo_teste: false
```

**Resultado:** ~26 lotes, 30-60 minutos

### Exemplo 2: Teste Antes de Processar
```python
data_inicio: 2024-06-01
data_fim: 2024-12-01
tamanho_lote: 7
modo_teste: true       # ← Apenas mostra estatísticas
```

## ⚙️ Tamanho de Lote Recomendado

| Período Total | Tamanho Lote | Nº Lotes | Tempo Estimado |
|---------------|--------------|----------|----------------|
| 1 mês | 7 dias | ~4 | 5-10 min |
| 3 meses | 7 dias | ~13 | 15-30 min |
| 6 meses | 7 dias | ~26 | 30-60 min |
| 1 ano | 14 dias | ~26 | 30-60 min |

## 🎯 Por Que Lotes?

**✅ Com Lotes:**
- Processamento controlado
- Recuperação de erros (continua do lote que falhou)
- Progresso visível
- Não sobrecarrega Oracle

**❌ Sem Lotes:**
- Timeout do Oracle
- Memória insuficiente
- Difícil recuperar de erros

## 🛡️ Segurança

- ✅ **Merge inteligente**: Não cria duplicatas
- ✅ **Idempotente**: Pode reprocessar o mesmo período
- ✅ **Modo teste**: Valida antes de processar

---

# 🚀 Quick Start

## Setup Inicial (Uma Vez)

1. **Executar setup:**
   ```python
   %run /Workspace/Repos/radiologia-laudos/jobs/setup_inicial
   ```

2. **Criar job no Databricks:**
   - Via UI: Jobs → Create Job
   - Via CLI: `databricks jobs create --json-file jobs/job_config.yaml`

3. **Configurar widgets (deixar vazios para automático):**
   - `data_processamento`: *vazio* (calcula D-1)
   - `modo_execucao`: `job_diario`
   - `dias_retroativos`: `1`

## Teste Manual

```python
# Configure os widgets:
data_processamento: 2025-11-18  # Dia específico
modo_execucao: job_diario
dias_retroativos: 1

# Execute o notebook
```

## Verificação

```sql
-- Ver dados extraídos (por dia de carga)
SELECT * 
FROM innovation_dev.bronze.radiologia_laudos_extraidos
WHERE DATE(dt_carga) = '2025-11-18'
LIMIT 10;

-- Ver métricas
SELECT * 
FROM innovation_dev.bronze.radiologia_laudos_metricas_job
ORDER BY dt_execucao DESC
LIMIT 5;

-- Verificar duplicatas (deve estar vazio!)
SELECT * 
FROM innovation_dev.bronze.vw_radiologia_laudos_duplicatas;
```

## ✅ Checklist

- [ ] Setup inicial executado
- [ ] Job criado no Databricks
- [ ] Teste manual funcionou
- [ ] Dados aparecem no Bronze
- [ ] Métricas salvas
- [ ] Sem duplicatas
- [ ] Schedule ativado (se quiser automático)

---

## 📞 Suporte

**Dúvidas ou problemas:**
- Email: eduardo.caminha@hapvida.com.br
- Slack: #innovation-radiologia
- Documentação: Confluence → Radiologia Analytics

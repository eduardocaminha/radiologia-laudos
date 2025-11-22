# 📊 Dashboard de Laudos Radiológicos

## Visão Geral

Dashboard completo com análises e estatísticas dos laudos extraídos da base Bronze (`innovation_dev.bronze.radiologia_laudos_extraidos`).

## Funcionalidades

### 🔍 Filtros Interativos

- **Período de análise**: Últimos 7, 30, 90 dias, último ano ou tudo
- **Fonte dos laudos**: HSP (Hospital) e/ou PSC (Pronto Socorro)

### 📈 Indicadores Principais (KPIs)

1. **Total de Laudos**: Quantidade total de registros
2. **Pacientes Únicos**: Quantidade de pacientes distintos
3. **Procedimentos**: Tipos de procedimentos realizados
4. **Média/Dia**: Média de laudos por dia no período

### 📊 Gráficos e Visualizações

#### Linha 1: Volume e Tendências
- **Volume de Laudos por Dia**: Gráfico de linha mostrando evolução temporal
- **Distribuição por Fonte**: Pizza mostrando proporção HSP vs PSC

#### Linha 2: Modalidades e Procedimentos
- **Top 10 Modalidades**: Ranking das modalidades mais realizadas (TC, RM, etc.)
- **Top 10 Procedimentos**: Ranking dos procedimentos específicos mais comuns

#### Linha 3: Análise Temporal
- **Volume por Dia da Semana**: Distribuição semanal com linha de média
- **Volume por Hora do Dia**: Distribuição horária dos procedimentos

### 📋 Tabelas Detalhadas

#### Detalhamento por Modalidade
- Total de laudos por modalidade
- Pacientes únicos
- Procedimentos distintos
- Percentual do total

#### Métricas de Execução dos Jobs
- **Últimas Execuções**: Histórico das 10 últimas cargas
- **Estatísticas de Carga**: Resumo por modo de execução (job_diario vs reprocessamento_historico)

## Requisitos

### Tabelas Necessárias

1. **Bronze**:
   - `innovation_dev.bronze.radiologia_laudos_extraidos`
   - `innovation_dev.bronze.radiologia_laudos_metricas_job`

2. **Gold**:
   - `innovation_dev.gold.radiologia_laudos_procedimentos` (com mapeamento de modalidades)

### Colunas Utilizadas

**radiologia_laudos_extraidos**:
- `accession_number`: Chave única
- `cd_paciente`: Código do paciente
- `cd_procedimento`: Código do procedimento
- `tms_procedimento_realizado`: Timestamp do procedimento
- `fonte`: HSP ou PSC
- `tms_carga`: Timestamp da carga

**radiologia_laudos_procedimentos**:
- `cd_procedimento`: Código do procedimento
- `nome_procedimento`: Nome do procedimento
- `nome_modalidade`: Modalidade (TC, RM, etc.)
- `ativo`: Flag de ativo

**radiologia_laudos_metricas_job**:
- `dt_processamento`: Data do processamento
- `modo_execucao`: job_diario ou reprocessamento_historico
- `laudos_extraidos`: Quantidade de laudos
- `procedimentos_ativos`: Procedimentos processados
- `tms_execucao`: Timestamp da execução

## Tecnologias

- **Streamlit**: Framework web
- **Plotly**: Gráficos interativos
- **Pandas**: Manipulação de dados
- **Databricks SQL Connector**: Conexão com Delta Lake

## Performance

### Otimizações Implementadas

1. **Filtros no SQL**: WHERE clauses aplicadas no Databricks
2. **Agregações no SQL**: GROUP BY executado no Delta Lake
3. **Limite de resultados**: TOP 10 para rankings
4. **Cache do Streamlit**: Reutilização de queries quando possível

### Queries Principais

Todas as queries utilizam:
- `WHERE` com filtros de período e fonte
- `JOIN` com tabela de procedimentos para enriquecimento
- `GROUP BY` para agregações
- `ORDER BY` para rankings

## Exemplos de Insights

### Volume e Tendências
- Identificar picos de demanda
- Comparar volume HSP vs PSC
- Detectar anomalias no volume diário

### Modalidades
- Quais modalidades são mais demandadas
- Distribuição de recursos por tipo de exame
- Planejamento de capacidade

### Análise Temporal
- Dias da semana com maior demanda
- Horários de pico
- Padrões sazonais

### Qualidade de Dados
- Monitorar execuções dos jobs
- Verificar consistência das cargas
- Acompanhar volume de laudos extraídos

## Manutenção

### Adicionar Novos Gráficos

1. Criar query SQL no dashboard.py
2. Executar com `execute_query(conn, query)`
3. Criar visualização com Plotly
4. Adicionar ao layout com `st.plotly_chart()`

### Adicionar Novos Filtros

1. Adicionar widget no sidebar
2. Atualizar `where_clauses` com nova condição
3. Reconstruir `where_sql`

### Atualizar KPIs

1. Modificar `query_kpis`
2. Adicionar nova coluna ao SELECT
3. Criar novo `st.metric()` no layout

## Troubleshooting

### Erro: "Sem dados para o período selecionado"
- Verificar se há dados na tabela Bronze
- Ajustar filtro de período
- Verificar se fonte está selecionada

### Gráficos não aparecem
- Verificar se Plotly está instalado: `pip install plotly`
- Verificar se query retorna dados: `len(df) > 0`

### Performance lenta
- Reduzir período de análise
- Verificar índices no Delta Lake (Z-ORDER)
- Otimizar queries SQL

## Roadmap

### Próximas Funcionalidades

- [ ] Exportar dados para Excel
- [ ] Comparação entre períodos
- [ ] Alertas automáticos
- [ ] Drill-down por procedimento
- [ ] Análise de pacientes recorrentes
- [ ] Mapa de calor temporal
- [ ] Previsão de demanda (ML)

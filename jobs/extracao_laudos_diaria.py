# Databricks notebook source
# MAGIC %md
# MAGIC # Job: Extração Diária de Laudos Radiológicos
# MAGIC 
# MAGIC **Objetivo:** Extrair laudos de procedimentos radiológicos do Oracle Lake (RAWZN) e salvar no Delta Lake (Bronze)
# MAGIC 
# MAGIC **Estratégia:**
# MAGIC - Processamento incremental diário (D-1)
# MAGIC - Tabela temporária otimizada com índices
# MAGIC - Join eficiente entre tb_procedimento_realizado e tb_laudo_paciente
# MAGIC - Salvamento em Delta Lake com particionamento por ano_mes
# MAGIC 
# MAGIC **Execução:** Diária às 02:00 AM (madrugada)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Setup e Conexão

# COMMAND ----------

# MAGIC %run /Workspace/Libraries/Lake

# COMMAND ----------

from pyspark.sql.functions import *
from pyspark.sql.types import *
from datetime import datetime, timedelta
import pandas as pd

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Parâmetros e Configuração

# COMMAND ----------

# Widgets para parametrização
dbutils.widgets.text("data_processamento", "", "Data Processamento (YYYY-MM-DD)")
dbutils.widgets.dropdown("modo_execucao", "incremental", ["incremental", "reprocessamento"], "Modo Execução")
dbutils.widgets.text("dias_retroativos", "1", "Dias Retroativos (reprocessamento)")

# Obter parâmetros
data_param = dbutils.widgets.get("data_processamento")
modo_execucao = dbutils.widgets.get("modo_execucao")
dias_retroativos = int(dbutils.widgets.get("dias_retroativos"))

# Determinar data de processamento
if data_param:
    data_processamento = datetime.strptime(data_param, '%Y-%m-%d').date()
else:
    # Default: D-1 (ontem)
    data_processamento = (datetime.now() - timedelta(days=1)).date()

# Período de extração
if modo_execucao == "incremental":
    # Processar apenas 1 dia (D-1)
    data_inicio = data_processamento
    data_fim = data_processamento + timedelta(days=1)
else:
    # Reprocessamento: últimos N dias
    data_inicio = data_processamento - timedelta(days=dias_retroativos)
    data_fim = data_processamento + timedelta(days=1)

# Configuração Delta Lake
SCHEMA_GOLD = "innovation_dev.gold"
SCHEMA_BRONZE = "innovation_dev.bronze"
TABLE_PROCEDIMENTOS_GOLD = f"{SCHEMA_GOLD}.radiologia_laudos_procedimentos"
TABLE_LAUDOS_BRONZE = f"{SCHEMA_BRONZE}.radiologia_laudos_extraidos"

print(f"""
╔══════════════════════════════════════════════════════════════╗
║  JOB: EXTRAÇÃO DIÁRIA DE LAUDOS RADIOLÓGICOS                ║
╠══════════════════════════════════════════════════════════════╣
║  Data Processamento: {data_processamento}                    
║  Período Extração:   {data_inicio} até {data_fim}            
║  Modo Execução:      {modo_execucao}                         
║  Tabela Destino:     {TABLE_LAUDOS_BRONZE}                   
╚══════════════════════════════════════════════════════════════╝
""")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Conectar ao Oracle Lake

# COMMAND ----------

print("🔌 Conectando ao Oracle Lake (RAWZN)...")

connect_to_datalake(
    username="USR_PROD_INFORMATICA_SAUDE",
    password=dbutils.secrets.get(scope="INNOVATION_RAW", key="USR_PROD_INFORMATICA_SAUDE"),
    layer="RAWZN",
    level="LOW",
    dbx_secret_scope="INNOVATION_RAW"
)

print("✅ Conexão estabelecida com sucesso!")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Buscar Procedimentos Ativos no Gold

# COMMAND ----------

print("📋 Buscando lista de procedimentos ativos no Delta Lake (Gold)...")

# Buscar procedimentos ativos
query_procedimentos = f"""
SELECT 
    p.cd_procedimento,
    p.nm_procedimento,
    m.nome_modalidade
FROM {TABLE_PROCEDIMENTOS_GOLD} p
INNER JOIN {SCHEMA_GOLD}.radiologia_laudos_modalidades m 
    ON p.id_modalidade = m.id_modalidade
WHERE p.ativo = TRUE
ORDER BY p.cd_procedimento
"""

df_procedimentos = spark.sql(query_procedimentos)
procedimentos_ativos = df_procedimentos.collect()

if len(procedimentos_ativos) == 0:
    print("⚠️ ATENÇÃO: Nenhum procedimento ativo encontrado no Gold!")
    dbutils.notebook.exit("Nenhum procedimento ativo para processar")

# Criar lista de códigos
lista_codigos = [row.cd_procedimento for row in procedimentos_ativos]
codigos_csv = ", ".join(str(cd) for cd in lista_codigos)

print(f"✅ {len(lista_codigos)} procedimentos ativos encontrados")
print(f"📊 Modalidades: {df_procedimentos.select('nome_modalidade').distinct().count()}")

# Mostrar amostra
print("\n📌 Amostra de procedimentos:")
df_procedimentos.show(10, truncate=False)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Criar Tabela Temporária Otimizada

# COMMAND ----------

print("🔧 Criando tabela temporária com procedimentos filtrados...")

# Query para criar tabela temporária
# Estratégia: filtrar por período e códigos ANTES do join
query_temp_table = f"""
SELECT /*+ PARALLEL(8) */
    PREA.CD_ATENDIMENTO,
    PREA.CD_OCORRENCIA,
    PREA.CD_ORDEM,
    PREA.CD_PROCEDIMENTO,
    PREA.DT_PROCEDIMENTO_REALIZADO,
    PREA.CD_PACIENTE
FROM RAWZN.RAW_HSP_TB_PROCEDIMENTO_REALIZADO PREA
WHERE PREA.CD_PROCEDIMENTO IN ({codigos_csv})
  AND PREA.DT_PROCEDIMENTO_REALIZADO >= DATE '{data_inicio}'
  AND PREA.DT_PROCEDIMENTO_REALIZADO < DATE '{data_fim}'
"""

print(f"📅 Período: {data_inicio} até {data_fim}")
print(f"🔢 Códigos: {len(lista_codigos)} procedimentos")

# Executar query e criar DataFrame temporário
df_procedimentos_realizados = run_sql(query_temp_table)

if len(df_procedimentos_realizados) == 0:
    print(f"⚠️ Nenhum procedimento realizado encontrado no período {data_inicio} - {data_fim}")
    dbutils.notebook.exit("Nenhum procedimento realizado no período")

print(f"✅ {len(df_procedimentos_realizados):,} procedimentos realizados encontrados")

# Estatísticas do pandas DataFrame
print("\n📊 Estatísticas da extração:")
print(f"   - Registros: {len(df_procedimentos_realizados):,}")
print(f"   - Atendimentos únicos: {df_procedimentos_realizados['CD_ATENDIMENTO'].nunique():,}")
print(f"   - Pacientes únicos: {df_procedimentos_realizados['CD_PACIENTE'].nunique():,}")

# Converter para Spark DataFrame para otimizações
df_proc_spark = spark.createDataFrame(df_procedimentos_realizados)

# Criar view temporária
df_proc_spark.createOrReplaceTempView("temp_procedimentos_realizados")

# Cache para otimizar joins
df_proc_spark.cache()
print("✅ Tabela temporária criada e cacheada!")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Extrair Laudos com Join Otimizado

# COMMAND ----------

print("🔍 Extraindo laudos com join otimizado...")

# Query otimizada com join
# Estratégia: usar a tabela temporária (já filtrada) para join com tb_laudo_paciente
query_laudos = f"""
SELECT /*+ BROADCAST(temp) */
    temp.CD_ATENDIMENTO as cd_atendimento,
    temp.CD_OCORRENCIA as cd_ocorrencia,
    temp.CD_ORDEM as cd_ordem,
    CONCAT(
        CAST(temp.CD_ATENDIMENTO AS STRING),
        CAST(temp.CD_OCORRENCIA AS STRING),
        CAST(temp.CD_ORDEM AS STRING)
    ) as accession_number,
    temp.CD_PROCEDIMENTO as cd_procedimento,
    temp.CD_PACIENTE as cd_paciente,
    P.NM_PROCEDIMENTO as nm_procedimento,
    LAUP.DS_LAUDO_MEDICO as ds_laudo_medico,
    temp.DT_PROCEDIMENTO_REALIZADO as dt_procedimento_realizado,
    YEAR(temp.DT_PROCEDIMENTO_REALIZADO) as ano,
    MONTH(temp.DT_PROCEDIMENTO_REALIZADO) as mes,
    CONCAT(
        YEAR(temp.DT_PROCEDIMENTO_REALIZADO), 
        '-', 
        LPAD(MONTH(temp.DT_PROCEDIMENTO_REALIZADO), 2, '0')
    ) as ano_mes
FROM temp_procedimentos_realizados temp
INNER JOIN RAWZN.RAW_HSP_TB_PROCEDIMENTO P
    ON temp.CD_PROCEDIMENTO = P.CD_PROCEDIMENTO
INNER JOIN RAWZN.RAW_HSP_TB_LAUDO_PACIENTE LAUP
    ON temp.CD_ATENDIMENTO = LAUP.CD_ATENDIMENTO
    AND temp.CD_OCORRENCIA = LAUP.CD_OCORRENCIA
    AND temp.CD_ORDEM = LAUP.CD_ORDEM
WHERE LAUP.DS_LAUDO_MEDICO IS NOT NULL
  AND LENGTH(TRIM(LAUP.DS_LAUDO_MEDICO)) > 0
"""

# Executar extração
df_laudos_pd = run_sql(query_laudos)

if len(df_laudos_pd) == 0:
    print(f"⚠️ Nenhum laudo encontrado para o período {data_inicio} - {data_fim}")
    # Limpar cache
    df_proc_spark.unpersist()
    dbutils.notebook.exit("Nenhum laudo encontrado")

print(f"✅ {len(df_laudos_pd):,} laudos extraídos com sucesso!")

# Converter para Spark DataFrame
df_laudos = spark.createDataFrame(df_laudos_pd)

# Verificar e remover duplicatas (se houver)
count_antes = df_laudos.count()
df_laudos = df_laudos.dropDuplicates(['accession_number'])
count_depois = df_laudos.count()

if count_antes > count_depois:
    print(f"⚠️ Removidas {count_antes - count_depois} duplicatas baseadas em accession_number")

# Estatísticas
print("\n📊 Estatísticas dos laudos extraídos:")
print(f"   - Total de laudos: {count_depois:,}")
print(f"   - Accession Numbers únicos: {df_laudos.select('accession_number').distinct().count():,}")
print(f"   - Procedimentos distintos: {df_laudos.select('cd_procedimento').distinct().count()}")
print(f"   - Pacientes distintos: {df_laudos.select('cd_paciente').distinct().count():,}")
print(f"   - Período: {df_laudos.agg(min('dt_procedimento_realizado'), max('dt_procedimento_realizado')).collect()[0]}")

# Distribuição por modalidade
print("\n📋 Distribuição por procedimento (Top 10):")
df_laudos.groupBy('cd_procedimento', 'nm_procedimento') \
    .count() \
    .orderBy(desc('count')) \
    .show(10, truncate=False)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7. Salvar no Delta Lake (Bronze)

# COMMAND ----------

print(f"💾 Salvando laudos no Delta Lake: {TABLE_LAUDOS_BRONZE}")

# Adicionar metadados de controle
df_laudos_final = df_laudos.withColumn("dt_carga", current_timestamp()) \
                            .withColumn("dt_processamento", lit(str(data_processamento))) \
                            .withColumn("modo_execucao", lit(modo_execucao))

# Verificar se tabela existe
table_exists = spark.catalog.tableExists(TABLE_LAUDOS_BRONZE)

if not table_exists:
    print("📝 Criando tabela Bronze pela primeira vez...")
    
    # Criar tabela com particionamento
    df_laudos_final.write \
        .format("delta") \
        .mode("overwrite") \
        .partitionBy("ano_mes") \
        .option("overwriteSchema", "true") \
        .saveAsTable(TABLE_LAUDOS_BRONZE)
    
    print(f"✅ Tabela {TABLE_LAUDOS_BRONZE} criada com sucesso!")
else:
    print("📝 Tabela Bronze já existe. Aplicando merge...")
    
    # Estratégia de merge para evitar duplicatas
    # Chave única: ACCESSION_NUMBER (CD_ATENDIMENTO + CD_OCORRENCIA + CD_ORDEM)
    
    from delta.tables import DeltaTable
    delta_table = DeltaTable.forName(spark, TABLE_LAUDOS_BRONZE)
    
    if modo_execucao == "incremental":
        # Incremental: usar merge para evitar duplicatas mesmo em modo incremental
        print("📝 Aplicando merge incremental (evita duplicatas)...")
        
        delta_table.alias("target").merge(
            df_laudos_final.alias("source"),
            "target.accession_number = source.accession_number"
        ).whenMatchedUpdate(
            set = {
                "ds_laudo_medico": "source.ds_laudo_medico",
                "dt_carga": "source.dt_carga",
                "dt_processamento": "source.dt_processamento"
            }
        ).whenNotMatchedInsertAll() \
         .execute()
        
        print("✅ Merge incremental concluído (sem duplicatas)!")
    else:
        # Reprocessamento: merge completo
        print("📝 Aplicando merge de reprocessamento...")
        
        delta_table.alias("target").merge(
            df_laudos_final.alias("source"),
            "target.accession_number = source.accession_number"
        ).whenMatchedUpdateAll() \
         .whenNotMatchedInsertAll() \
         .execute()
        
        print("✅ Merge de reprocessamento concluído!")

# Otimizar tabela (compactação)
print("🔧 Otimizando tabela Delta...")
spark.sql(f"OPTIMIZE {TABLE_LAUDOS_BRONZE}")
print("✅ Otimização concluída!")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 8. Métricas e Limpeza

# COMMAND ----------

print("📊 Gerando métricas finais...")

# Contar registros na tabela Bronze
total_bronze = spark.sql(f"SELECT COUNT(*) as total FROM {TABLE_LAUDOS_BRONZE}").collect()[0]['total']

# Métricas do processamento atual
metricas = {
    'data_processamento': str(data_processamento),
    'periodo_inicio': str(data_inicio),
    'periodo_fim': str(data_fim),
    'modo_execucao': modo_execucao,
    'procedimentos_ativos': len(lista_codigos),
    'procedimentos_realizados': len(df_procedimentos_realizados),
    'laudos_extraidos': len(df_laudos_pd),
    'total_bronze': total_bronze,
    'dt_execucao': datetime.now().isoformat()
}

# Exibir métricas
print("\n" + "="*70)
print("📈 MÉTRICAS DO PROCESSAMENTO")
print("="*70)
for key, value in metricas.items():
    print(f"   {key:.<40} {value:>25}")
print("="*70)

# Limpar cache
df_proc_spark.unpersist()
print("\n🧹 Cache limpo!")

# Salvar métricas em tabela de controle (opcional)
df_metricas = spark.createDataFrame([metricas])
df_metricas.write \
    .format("delta") \
    .mode("append") \
    .saveAsTable(f"{SCHEMA_BRONZE}.radiologia_laudos_metricas_job")

print(f"✅ Métricas salvas em {SCHEMA_BRONZE}.radiologia_laudos_metricas_job")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 9. Finalização

# COMMAND ----------

print("""
╔══════════════════════════════════════════════════════════════╗
║  ✅ JOB CONCLUÍDO COM SUCESSO!                              ║
╠══════════════════════════════════════════════════════════════╣
║  Laudos extraídos e salvos no Delta Lake (Bronze)          ║
║  Próxima execução: D+1 às 02:00 AM                          ║
╚══════════════════════════════════════════════════════════════╝
""")

# Retornar métricas para o Job
dbutils.notebook.exit(metricas)

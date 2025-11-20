# Databricks notebook source
# MAGIC %md
# MAGIC # Setup Inicial - Tabelas Bronze e Métricas
# MAGIC 
# MAGIC **Execute este notebook UMA VEZ antes de rodar o job pela primeira vez**
# MAGIC 
# MAGIC Cria:
# MAGIC - Tabela Bronze para laudos extraídos
# MAGIC - Tabela de métricas do job
# MAGIC - Configurações de otimização

# COMMAND ----------

from pyspark.sql.types import *
from pyspark.sql.functions import *

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuração

# COMMAND ----------

SCHEMA_BRONZE = "innovation_dev.bronze"
TABLE_LAUDOS = f"{SCHEMA_BRONZE}.radiologia_laudos_extraidos"
TABLE_METRICAS = f"{SCHEMA_BRONZE}.radiologia_laudos_metricas_job"

print(f"""
╔══════════════════════════════════════════════════════════════╗
║  SETUP INICIAL - RADIOLOGIA LAUDOS                          ║
╠══════════════════════════════════════════════════════════════╣
║  Schema Bronze:  {SCHEMA_BRONZE}                             
║  Tabela Laudos:  {TABLE_LAUDOS}                              
║  Tabela Métricas: {TABLE_METRICAS}                           
╚══════════════════════════════════════════════════════════════╝
""")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Criar Schema Bronze (se não existir)

# COMMAND ----------

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA_BRONZE}")
print(f"✅ Schema {SCHEMA_BRONZE} criado/verificado")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Criar Tabela de Laudos

# COMMAND ----------

# Schema da tabela de laudos (nomes em minúsculo - padrão Delta Lake)
schema_laudos = StructType([
    StructField("cd_atendimento", LongType(), False),
    StructField("cd_ocorrencia", LongType(), False),
    StructField("cd_ordem", LongType(), False),
    StructField("accession_number", StringType(), False),  # Chave única
    StructField("cd_procedimento", LongType(), False),
    StructField("cd_paciente", LongType(), True),
    StructField("ds_laudo_medico", StringType(), True),
    StructField("dt_procedimento_realizado", TimestampType(), True),  # TIMESTAMP completo (data + hora)
    StructField("ano_mes", StringType(), False),  # Particionamento (YYYY-MM)
    StructField("dt_carga", TimestampType(), True),  # Quando foi carregado
    StructField("modo_execucao", StringType(), True)  # Como foi carregado (diario/reprocessamento_historico)
])

# Criar DataFrame vazio com o schema
df_empty = spark.createDataFrame([], schema_laudos)

# Verificar se tabela já existe
if spark.catalog.tableExists(TABLE_LAUDOS):
    print(f"⚠️  Tabela {TABLE_LAUDOS} já existe!")
    
    # Mostrar informações
    df_info = spark.sql(f"DESCRIBE EXTENDED {TABLE_LAUDOS}")
    print("\n📊 Informações da tabela existente:")
    df_info.show(50, truncate=False)
    
    # Contar registros
    count = spark.sql(f"SELECT COUNT(*) as total FROM {TABLE_LAUDOS}").collect()[0]['total']
    print(f"\n📈 Total de registros: {count:,}")
    
else:
    print(f"📝 Criando tabela {TABLE_LAUDOS}...")
    
    # Criar tabela com particionamento
    df_empty.write \
        .format("delta") \
        .mode("overwrite") \
        .partitionBy("ano_mes") \
        .option("delta.autoOptimize.optimizeWrite", "true") \
        .option("delta.autoOptimize.autoCompact", "true") \
        .saveAsTable(TABLE_LAUDOS)
    
    print(f"✅ Tabela {TABLE_LAUDOS} criada com sucesso!")
    
    # Adicionar propriedades da tabela
    spark.sql(f"""
        ALTER TABLE {TABLE_LAUDOS} 
        SET TBLPROPERTIES (
            'delta.autoOptimize.optimizeWrite' = 'true',
            'delta.autoOptimize.autoCompact' = 'true',
            'delta.enableChangeDataFeed' = 'true',
            'delta.logRetentionDuration' = 'interval 30 days',
            'delta.deletedFileRetentionDuration' = 'interval 7 days'
        )
    """)
    
    print("✅ Propriedades de otimização configuradas!")
    
    # Adicionar comentário sobre accession_number
    spark.sql(f"""
        ALTER TABLE {TABLE_LAUDOS}
        ALTER COLUMN accession_number COMMENT 'Chave única: cd_atendimento + cd_ocorrencia + cd_ordem (sem separadores)'
    """)
    
    print("✅ Comentários adicionados às colunas!")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Criar Tabela de Métricas

# COMMAND ----------

# Schema da tabela de métricas
schema_metricas = StructType([
    StructField("data_processamento", StringType(), True),
    StructField("periodo_inicio", StringType(), True),
    StructField("periodo_fim", StringType(), True),
    StructField("modo_execucao", StringType(), True),
    StructField("procedimentos_ativos", IntegerType(), True),
    StructField("procedimentos_realizados", IntegerType(), True),
    StructField("laudos_extraidos", IntegerType(), True),
    StructField("total_bronze", LongType(), True),
    StructField("dt_execucao", StringType(), True)
])

# Criar DataFrame vazio com o schema
df_empty_metricas = spark.createDataFrame([], schema_metricas)

# Verificar se tabela já existe
if spark.catalog.tableExists(TABLE_METRICAS):
    print(f"⚠️  Tabela {TABLE_METRICAS} já existe!")
    
    # Mostrar últimas execuções
    print("\n📊 Últimas 10 execuções:")
    spark.sql(f"""
        SELECT 
            data_processamento,
            modo_execucao,
            procedimentos_ativos,
            laudos_extraidos,
            dt_execucao
        FROM {TABLE_METRICAS}
        ORDER BY dt_execucao DESC
        LIMIT 10
    """).show(truncate=False)
    
else:
    print(f"📝 Criando tabela {TABLE_METRICAS}...")
    
    # Criar tabela
    df_empty_metricas.write \
        .format("delta") \
        .mode("overwrite") \
        .saveAsTable(TABLE_METRICAS)
    
    print(f"✅ Tabela {TABLE_METRICAS} criada com sucesso!")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Configurar Otimizações

# COMMAND ----------

print("🔧 Configurando otimizações na tabela de laudos...")

# Z-ORDER nas colunas mais consultadas
try:
    spark.sql(f"""
        OPTIMIZE {TABLE_LAUDOS}
        ZORDER BY (accession_number, cd_procedimento, dt_procedimento_realizado)
    """)
    print("✅ Z-ORDER configurado para accession_number, cd_procedimento e dt_procedimento_realizado")
except Exception as e:
    print(f"⚠️  Z-ORDER não aplicado (tabela vazia): {str(e)}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Criar Views Úteis

# COMMAND ----------

print("📊 Criando views úteis...")

# View: Estatísticas diárias
spark.sql(f"""
CREATE OR REPLACE VIEW {SCHEMA_BRONZE}.vw_radiologia_laudos_diario AS
SELECT 
    dt_processamento,
    COUNT(*) as total_laudos,
    COUNT(DISTINCT cd_paciente) as pacientes_unicos,
    COUNT(DISTINCT cd_procedimento) as procedimentos_distintos,
    COUNT(DISTINCT cd_atendimento) as atendimentos_unicos,
    MIN(dt_carga) as primeira_carga,
    MAX(dt_carga) as ultima_carga
FROM {TABLE_LAUDOS}
GROUP BY dt_processamento
ORDER BY dt_processamento DESC
""")
print(f"✅ View criada: {SCHEMA_BRONZE}.vw_radiologia_laudos_diario")

# View: Estatísticas por procedimento
spark.sql(f"""
CREATE OR REPLACE VIEW {SCHEMA_BRONZE}.vw_radiologia_laudos_por_procedimento AS
SELECT 
    cd_procedimento,
    nm_procedimento,
    COUNT(*) as total_laudos,
    COUNT(DISTINCT accession_number) as accession_numbers_unicos,
    COUNT(DISTINCT cd_paciente) as pacientes_unicos,
    MIN(dt_procedimento_realizado) as primeira_data,
    MAX(dt_procedimento_realizado) as ultima_data,
    AVG(LENGTH(ds_laudo_medico)) as tamanho_medio_laudo
FROM {TABLE_LAUDOS}
GROUP BY cd_procedimento, nm_procedimento
ORDER BY total_laudos DESC
""")
print(f"✅ View criada: {SCHEMA_BRONZE}.vw_radiologia_laudos_por_procedimento")

# View: Verificar duplicatas (não deveria ter nenhuma)
spark.sql(f"""
CREATE OR REPLACE VIEW {SCHEMA_BRONZE}.vw_radiologia_laudos_duplicatas AS
SELECT 
    accession_number,
    COUNT(*) as qtd_duplicatas,
    COLLECT_LIST(dt_carga) as datas_carga
FROM {TABLE_LAUDOS}
GROUP BY accession_number
HAVING COUNT(*) > 1
ORDER BY qtd_duplicatas DESC
""")
print(f"✅ View criada: {SCHEMA_BRONZE}.vw_radiologia_laudos_duplicatas (monitoramento)")

# View: Monitoramento do job
spark.sql(f"""
CREATE OR REPLACE VIEW {SCHEMA_BRONZE}.vw_radiologia_job_monitoramento AS
SELECT 
    data_processamento,
    modo_execucao,
    procedimentos_ativos,
    procedimentos_realizados,
    laudos_extraidos,
    ROUND(laudos_extraidos / procedimentos_realizados * 100, 2) as taxa_laudos_pct,
    total_bronze,
    dt_execucao,
    CASE 
        WHEN laudos_extraidos = 0 THEN '⚠️ Sem laudos'
        WHEN laudos_extraidos < 100 THEN '⚠️ Baixo volume'
        ELSE '✅ OK'
    END as status
FROM {TABLE_METRICAS}
ORDER BY dt_execucao DESC
""")
print(f"✅ View criada: {SCHEMA_BRONZE}.vw_radiologia_job_monitoramento")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Verificação Final

# COMMAND ----------

print("\n" + "="*70)
print("📋 VERIFICAÇÃO FINAL")
print("="*70)

# Verificar tabelas criadas
tables = spark.sql(f"SHOW TABLES IN {SCHEMA_BRONZE}").filter(
    col("tableName").like("radiologia%")
).collect()

print(f"\n✅ Tabelas criadas em {SCHEMA_BRONZE}:")
for table in tables:
    table_name = table['tableName']
    is_view = table['isTemporary']
    tipo = "VIEW" if is_view else "TABLE"
    print(f"   - {table_name} ({tipo})")

print("\n" + "="*70)
print("✅ SETUP CONCLUÍDO COM SUCESSO!")
print("="*70)
print("""
Próximos passos:
1. Configure o Job Databricks usando job_config.yaml
2. Execute o job manualmente para testar
3. Ative o schedule para execução diária às 02:00 AM

Queries úteis:
- SELECT * FROM {0}.vw_radiologia_laudos_diario;
- SELECT * FROM {0}.vw_radiologia_laudos_por_procedimento;
- SELECT * FROM {0}.vw_radiologia_job_monitoramento;
- SELECT * FROM {0}.vw_radiologia_laudos_duplicatas; -- Deve estar vazio!

Verificar accession_number:
- SELECT accession_number, cd_atendimento, cd_ocorrencia, cd_ordem 
  FROM {0}.radiologia_laudos_extraidos LIMIT 10;
""".format(SCHEMA_BRONZE))

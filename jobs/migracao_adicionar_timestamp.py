# Databricks notebook source
# MAGIC %md
# MAGIC # Migração: Adicionar Timestamp Completo aos Laudos
# MAGIC 
# MAGIC **Objetivo:** Atualizar dados existentes na Bronze para incluir hora do procedimento
# MAGIC 
# MAGIC **Mudanças:**
# MAGIC - `dt_procedimento_realizado`: DATE → TIMESTAMP (adiciona hora)
# MAGIC - Remove colunas: `ano`, `mes` (redundantes)
# MAGIC - Mantém: `ano_mes` (particionamento)
# MAGIC 
# MAGIC **⚠️ IMPORTANTE:**
# MAGIC - Execute este script **UMA VEZ** após o reprocessamento histórico atual
# MAGIC - Faz backup automático antes de alterar
# MAGIC - Pode levar alguns minutos dependendo do volume

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Setup

# COMMAND ----------

# MAGIC %run /Workspace/Libraries/Lake

# COMMAND ----------

from pyspark.sql.functions import *
from pyspark.sql.types import *
from delta.tables import DeltaTable
from datetime import datetime
import time

# COMMAND ----------

# Configuração
SCHEMA_BRONZE = "innovation_dev.bronze"
TABLE_LAUDOS = f"{SCHEMA_BRONZE}.radiologia_laudos_extraidos"
TABLE_BACKUP = f"{SCHEMA_BRONZE}.radiologia_laudos_extraidos_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

print(f"""
╔══════════════════════════════════════════════════════════════╗
║  MIGRAÇÃO: ADICIONAR TIMESTAMP COMPLETO                     ║
╠══════════════════════════════════════════════════════════════╣
║  Tabela:         {TABLE_LAUDOS}
║  Backup:         {TABLE_BACKUP}
║  Data:           {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
╚══════════════════════════════════════════════════════════════╝
""")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Verificações Iniciais

# COMMAND ----------

print("🔍 Verificando tabela Bronze...")

# Verificar se tabela existe
if not spark.catalog.tableExists(TABLE_LAUDOS):
    raise Exception(f"❌ Tabela {TABLE_LAUDOS} não existe!")

# Contar registros
df_atual = spark.table(TABLE_LAUDOS)
total_registros = df_atual.count()

print(f"✅ Tabela encontrada: {total_registros:,} registros")
print(f"\n📊 Schema atual:")
df_atual.printSchema()

# Verificar se já tem timestamp
if df_atual.schema['dt_procedimento_realizado'].dataType == TimestampType():
    print("\n⚠️  A coluna dt_procedimento_realizado já é TIMESTAMP!")
    print("   Esta migração pode já ter sido executada.")
    resposta = input("\n   Deseja continuar mesmo assim? (sim/não): ")
    if resposta.lower() != 'sim':
        dbutils.notebook.exit("Migração cancelada pelo usuário")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Criar Backup

# COMMAND ----------

print(f"💾 Criando backup: {TABLE_BACKUP}")
inicio_backup = time.time()

df_atual.write \
    .format("delta") \
    .mode("overwrite") \
    .saveAsTable(TABLE_BACKUP)

tempo_backup = time.time() - inicio_backup
print(f"✅ Backup criado em {tempo_backup:.1f} segundos")
print(f"   Registros no backup: {spark.table(TABLE_BACKUP).count():,}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Conectar ao Oracle

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
# MAGIC ## 5. Buscar Horas do Oracle em Lotes

# COMMAND ----------

print("🔍 Buscando horas dos procedimentos do Oracle...")
print("⏳ Processando em lotes de 10.000 registros...\n")

# Buscar accession_numbers únicos da Bronze
df_bronze = spark.table(TABLE_LAUDOS).select(
    "accession_number",
    "cd_atendimento", 
    "cd_ocorrencia", 
    "cd_ordem"
).distinct()

total_laudos = df_bronze.count()
print(f"📊 Total de laudos a processar: {total_laudos:,}")

# Converter para pandas para processar em lotes
df_bronze_pd = df_bronze.toPandas()

# Processar em lotes
tamanho_lote = 10000
num_lotes = (len(df_bronze_pd) // tamanho_lote) + 1
resultados = []

inicio_total = time.time()

for i in range(num_lotes):
    inicio_lote = i * tamanho_lote
    fim_lote = inicio_lote + tamanho_lote if (inicio_lote + tamanho_lote) < len(df_bronze_pd) else len(df_bronze_pd)
    
    lote = df_bronze_pd.iloc[inicio_lote:fim_lote]
    
    if len(lote) == 0:
        continue
    
    print(f"📦 Lote {i+1}/{num_lotes} - Processando {len(lote):,} registros...")
    
    # Criar lista de condições para WHERE
    condicoes = []
    for _, row in lote.iterrows():
        condicoes.append(
            f"(CD_ATENDIMENTO = {row['cd_atendimento']} AND "
            f"CD_OCORRENCIA = {row['cd_ocorrencia']} AND "
            f"CD_ORDEM = {row['cd_ordem']})"
        )
    
    where_clause = " OR ".join(condicoes)
    
    # Query Oracle (HSP + PSC)
    query = f"""
    SELECT * FROM (
        -- HSP (Hospital)
        SELECT 
            CD_ATENDIMENTO,
            CD_OCORRENCIA,
            CD_ORDEM,
            DT_PROCEDIMENTO_REALIZADO,
            HR_PROCEDIMENTO_REALIZADO
        FROM RAWZN.RAW_HSP_TB_PROCEDIMENTO_REALIZADO
        WHERE {where_clause}
        
        UNION ALL
        
        -- PSC (Pronto Socorro)
        SELECT 
            CD_ATENDIMENTO,
            CD_OCORRENCIA,
            CD_ORDEM,
            DT_PROCEDIMENTO_REALIZADO,
            HR_PROCEDIMENTO_REALIZADO
        FROM RAWZN.RAW_PSC_TB_PROCEDIMENTO_REALIZADO
        WHERE {where_clause}
    )
    """
    
    try:
        df_oracle = run_sql(query)
        
        if len(df_oracle) > 0:
            # Criar accession_number
            df_oracle['ACCESSION_NUMBER'] = (
                df_oracle['CD_ATENDIMENTO'].astype(str) + 
                df_oracle['CD_OCORRENCIA'].astype(str) + 
                df_oracle['CD_ORDEM'].astype(str)
            )
            resultados.append(df_oracle)
            print(f"   ✅ {len(df_oracle):,} registros encontrados")
        else:
            print(f"   ⚠️  Nenhum registro encontrado no Oracle")
    
    except Exception as e:
        print(f"   ❌ Erro no lote {i+1}: {str(e)[:200]}")
        continue

tempo_total = time.time() - inicio_total
print(f"\n⏱️  Tempo total de busca: {tempo_total/60:.1f} minutos")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Combinar Resultados

# COMMAND ----------

if len(resultados) == 0:
    raise Exception("❌ Nenhum dado foi encontrado no Oracle!")

print("🔄 Combinando resultados...")

import pandas as pd
df_horas_pd = pd.concat(resultados, ignore_index=True)

print(f"✅ Total de registros com hora: {len(df_horas_pd):,}")

# Converter colunas para minúsculo
df_horas_pd.columns = [col.lower() for col in df_horas_pd.columns]

# Criar timestamp combinando data + hora
# HR_PROCEDIMENTO_REALIZADO está em segundos desde meia-noite
df_horas_pd['dt_procedimento_realizado'] = pd.to_datetime(df_horas_pd['dt_procedimento_realizado'])
df_horas_pd['hr_segundos'] = pd.to_numeric(df_horas_pd['hr_procedimento_realizado'], errors='coerce').fillna(0)
df_horas_pd['dt_procedimento_realizado'] = df_horas_pd['dt_procedimento_realizado'] + pd.to_timedelta(df_horas_pd['hr_segundos'], unit='s')

# Converter para Spark
df_horas = spark.createDataFrame(df_horas_pd[['accession_number', 'dt_procedimento_realizado']])

print("\n📊 Amostra dos dados com timestamp:")
df_horas.show(5, truncate=False)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7. Atualizar Tabela Bronze

# COMMAND ----------

print("🔄 Atualizando tabela Bronze com timestamps...")
inicio_update = time.time()

# Ler tabela atual
df_bronze_atual = spark.table(TABLE_LAUDOS)

# Join com as horas
df_bronze_atualizado = df_bronze_atual.alias("bronze").join(
    df_horas.alias("horas"),
    "accession_number",
    "left"
).select(
    col("bronze.cd_atendimento"),
    col("bronze.cd_ocorrencia"),
    col("bronze.cd_ordem"),
    col("bronze.accession_number"),
    col("bronze.cd_procedimento"),
    col("bronze.cd_paciente"),
    col("bronze.ds_laudo_medico"),
    # Usar timestamp do Oracle, ou manter data original se não encontrou
    coalesce(col("horas.dt_procedimento_realizado"), col("bronze.dt_procedimento_realizado").cast(TimestampType())).alias("dt_procedimento_realizado"),
    col("bronze.ano_mes"),
    col("bronze.dt_carga"),
    col("bronze.dt_processamento"),
    col("bronze.modo_execucao")
    # Removido: ano, mes
)

# Verificar quantos foram atualizados
total_com_hora = df_bronze_atualizado.filter(col("dt_procedimento_realizado").isNotNull()).count()
print(f"✅ {total_com_hora:,} registros com timestamp completo")

# Sobrescrever tabela
print("\n💾 Salvando nova versão da tabela...")
df_bronze_atualizado.write \
    .format("delta") \
    .mode("overwrite") \
    .partitionBy("ano_mes") \
    .option("overwriteSchema", "true") \
    .saveAsTable(TABLE_LAUDOS)

tempo_update = time.time() - inicio_update
print(f"✅ Tabela atualizada em {tempo_update:.1f} segundos")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 8. Verificação Final

# COMMAND ----------

print("🔍 Verificando migração...\n")

df_novo = spark.table(TABLE_LAUDOS)

print("📊 Novo schema:")
df_novo.printSchema()

print("\n📈 Estatísticas:")
print(f"   - Total de registros: {df_novo.count():,}")
print(f"   - Com timestamp: {df_novo.filter(col('dt_procedimento_realizado').isNotNull()).count():,}")
print(f"   - Partições: {df_novo.select('ano_mes').distinct().count()}")

print("\n📋 Amostra dos dados:")
df_novo.select(
    "accession_number",
    "dt_procedimento_realizado",
    "ano_mes"
).show(10, truncate=False)

# Verificar se colunas ano e mes foram removidas
colunas = df_novo.columns
if 'ano' in colunas or 'mes' in colunas:
    print("\n⚠️  ATENÇÃO: Colunas 'ano' e/ou 'mes' ainda existem!")
else:
    print("\n✅ Colunas 'ano' e 'mes' removidas com sucesso!")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 9. Otimizar Tabela

# COMMAND ----------

print("🔧 Otimizando tabela Delta...")

spark.sql(f"OPTIMIZE {TABLE_LAUDOS}")
spark.sql(f"OPTIMIZE {TABLE_LAUDOS} ZORDER BY (accession_number, cd_procedimento)")

print("✅ Otimização concluída!")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 10. Resumo Final

# COMMAND ----------

print("\n" + "="*70)
print("✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
print("="*70)
print(f"Tabela:              {TABLE_LAUDOS}")
print(f"Backup:              {TABLE_BACKUP}")
print(f"Registros migrados:  {total_registros:,}")
print(f"Com timestamp:       {total_com_hora:,}")
print(f"Tempo total:         {(time.time() - inicio_total)/60:.1f} minutos")
print("="*70)

print("\n📋 Próximos passos:")
print("   1. ✅ Migração concluída")
print("   2. ⏭️  Fazer pull dos notebooks atualizados no Databricks")
print("   3. ⏭️  Testar job diário com novo schema")
print("   4. ⏭️  (Opcional) Deletar backup após validação:")
print(f"      DROP TABLE {TABLE_BACKUP}")

# COMMAND ----------

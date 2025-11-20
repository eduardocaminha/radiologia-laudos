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
# MAGIC ## 5. Criar Tabela Temporária no Oracle e Extrair Laudos

# COMMAND ----------

print("🔧 Criando tabela temporária no Oracle Lake...")
print(f"📅 Período: {data_inicio} até {data_fim}")
print(f"🔢 Códigos: {len(lista_codigos)} procedimentos")

# Estratégia otimizada:
# 1. Criar tabela temporária NO ORACLE com procedimentos filtrados
# 2. Fazer join NO ORACLE usando a temp table
# 3. Trazer apenas o resultado final para o Databricks

# Passo 1: Criar ou limpar tabela temporária no Oracle
query_create_temp = f"""
CREATE GLOBAL TEMPORARY TABLE temp_proc_radiologia (
    CD_ATENDIMENTO NUMBER,
    CD_OCORRENCIA NUMBER,
    CD_ORDEM NUMBER,
    CD_PROCEDIMENTO NUMBER,
    DT_PROCEDIMENTO_REALIZADO DATE,
    HR_PROCEDIMENTO_REALIZADO NUMBER
) ON COMMIT PRESERVE ROWS
"""

try:
    run_sql(query_create_temp)
    print("✅ Tabela temporária criada no Oracle")
except Exception as e:
    # Tabela já existe - apenas limpar os dados
    if "ORA-00955" in str(e):  # name is already used by an existing object
        try:
            run_sql("TRUNCATE TABLE temp_proc_radiologia")
            print("ℹ️  Tabela temporária já existe, dados limpos")
        except:
            # Se TRUNCATE falhar, tentar DELETE
            run_sql("DELETE FROM temp_proc_radiologia")
            print("ℹ️  Tabela temporária já existe, dados deletados")
    else:
        raise e

# Passo 2: Popular tabela temporária (HSP + PSC)
query_insert_temp = f"""
INSERT INTO temp_proc_radiologia
SELECT /*+ PARALLEL(8) */
    CD_ATENDIMENTO,
    CD_OCORRENCIA,
    CD_ORDEM,
    CD_PROCEDIMENTO,
    DT_PROCEDIMENTO_REALIZADO,
    HR_PROCEDIMENTO_REALIZADO
FROM (
    -- HSP (Hospital)
    SELECT 
        PREA.CD_ATENDIMENTO,
        PREA.CD_OCORRENCIA,
        PREA.CD_ORDEM,
        PREA.CD_PROCEDIMENTO,
        PREA.DT_PROCEDIMENTO_REALIZADO,
        PREA.HR_PROCEDIMENTO_REALIZADO
    FROM RAWZN.RAW_HSP_TB_PROCEDIMENTO_REALIZADO PREA
    WHERE PREA.CD_PROCEDIMENTO IN ({codigos_csv})
      AND PREA.DT_PROCEDIMENTO_REALIZADO >= DATE '{data_inicio}'
      AND PREA.DT_PROCEDIMENTO_REALIZADO < DATE '{data_fim}'
    
    UNION ALL
    
    -- PSC (Pronto Socorro)
    SELECT 
        PREA.CD_ATENDIMENTO,
        PREA.CD_OCORRENCIA,
        PREA.CD_ORDEM,
        PREA.CD_PROCEDIMENTO,
        PREA.DT_PROCEDIMENTO_REALIZADO,
        PREA.HR_PROCEDIMENTO_REALIZADO
    FROM RAWZN.RAW_PSC_TB_PROCEDIMENTO_REALIZADO PREA
    WHERE PREA.CD_PROCEDIMENTO IN ({codigos_csv})
      AND PREA.DT_PROCEDIMENTO_REALIZADO >= DATE '{data_inicio}'
      AND PREA.DT_PROCEDIMENTO_REALIZADO < DATE '{data_fim}'
)
"""

run_sql(query_insert_temp)
print("✅ Tabela temporária populada no Oracle")

# Verificar quantos registros foram inseridos
query_count = "SELECT COUNT(*) as TOTAL FROM temp_proc_radiologia"
df_count = run_sql(query_count)
total_procedimentos = df_count['TOTAL'].iloc[0]

if total_procedimentos == 0:
    print(f"⚠️ Nenhum procedimento realizado encontrado no período {data_inicio} - {data_fim}")
    dbutils.notebook.exit("Nenhum procedimento realizado no período")

print(f"✅ {total_procedimentos:,} procedimentos realizados encontrados")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Extrair Laudos com Join no Oracle

# COMMAND ----------

print("🔍 Extraindo laudos com join otimizado NO ORACLE...")
print("⏳ Aguarde... O join pode levar alguns minutos dependendo do volume de dados.")
print(f"📊 Processando {total_procedimentos:,} procedimentos realizados...")

# Query otimizada: JOIN acontece NO ORACLE usando a tabela temporária
# Busca CD_PACIENTE via TM_ATENDIMENTO
# Nota: DS_LAUDO_MEDICO é tipo LONG, não pode usar funções no WHERE
query_laudos = f"""
SELECT /*+ PARALLEL(8) */ * FROM (
    -- HSP (Hospital)
    SELECT 
        temp.CD_ATENDIMENTO,
        temp.CD_OCORRENCIA,
        temp.CD_ORDEM,
        TO_CHAR(temp.CD_ATENDIMENTO) || TO_CHAR(temp.CD_OCORRENCIA) || TO_CHAR(temp.CD_ORDEM) as ACCESSION_NUMBER,
        temp.CD_PROCEDIMENTO,
        ATD.CD_PACIENTE,
        LAUP.DS_LAUDO_MEDICO,
        temp.DT_PROCEDIMENTO_REALIZADO,
        temp.HR_PROCEDIMENTO_REALIZADO,
        TO_CHAR(temp.DT_PROCEDIMENTO_REALIZADO, 'YYYY-MM') as ANO_MES
    FROM temp_proc_radiologia temp
    INNER JOIN RAWZN.RAW_HSP_TM_ATENDIMENTO ATD
        ON temp.CD_ATENDIMENTO = ATD.CD_ATENDIMENTO
    INNER JOIN RAWZN.RAW_HSP_TB_LAUDO_PACIENTE LAUP
        ON temp.CD_ATENDIMENTO = LAUP.CD_ATENDIMENTO
        AND temp.CD_OCORRENCIA = LAUP.CD_OCORRENCIA
        AND temp.CD_ORDEM = LAUP.CD_ORDEM
    WHERE LAUP.DS_LAUDO_MEDICO IS NOT NULL
    
    UNION ALL
    
    -- PSC (Pronto Socorro)
    SELECT 
        temp.CD_ATENDIMENTO,
        temp.CD_OCORRENCIA,
        temp.CD_ORDEM,
        TO_CHAR(temp.CD_ATENDIMENTO) || TO_CHAR(temp.CD_OCORRENCIA) || TO_CHAR(temp.CD_ORDEM) as ACCESSION_NUMBER,
        temp.CD_PROCEDIMENTO,
        ATD.CD_PACIENTE,
        LAUP.DS_LAUDO_MEDICO,
        temp.DT_PROCEDIMENTO_REALIZADO,
        temp.HR_PROCEDIMENTO_REALIZADO,
        TO_CHAR(temp.DT_PROCEDIMENTO_REALIZADO, 'YYYY-MM') as ANO_MES
    FROM temp_proc_radiologia temp
    INNER JOIN RAWZN.RAW_PSC_TM_ATENDIMENTO ATD
        ON temp.CD_ATENDIMENTO = ATD.CD_ATENDIMENTO
    INNER JOIN RAWZN.RAW_PSC_TB_LAUDO_PACIENTE LAUP
        ON temp.CD_ATENDIMENTO = LAUP.CD_ATENDIMENTO
        AND temp.CD_OCORRENCIA = LAUP.CD_OCORRENCIA
        AND temp.CD_ORDEM = LAUP.CD_ORDEM
    WHERE LAUP.DS_LAUDO_MEDICO IS NOT NULL
)
"""

# Executar extração (join acontece no Oracle)
import time
inicio_extracao = time.time()

print("\n" + "="*60)
print("🔄 EXECUTANDO JOIN NO ORACLE...")
print("="*60)
print("📍 Etapas:")
print("   1. Join temp_proc_radiologia ↔ TM_ATENDIMENTO (CD_PACIENTE)")
print("   2. Join com TB_LAUDO_PACIENTE (laudos)")
print("   3. Transferência Oracle → Databricks")
print("="*60 + "\n")

df_laudos_pd = run_sql(query_laudos)

tempo_extracao = time.time() - inicio_extracao
print(f"\n⏱️  Tempo de extração: {tempo_extracao:.2f} segundos ({tempo_extracao/60:.1f} minutos)")

# Filtrar laudos vazios no pandas (DS_LAUDO_MEDICO é tipo LONG, não pode filtrar no Oracle)
if len(df_laudos_pd) > 0:
    count_antes_filtro = len(df_laudos_pd)
    df_laudos_pd = df_laudos_pd[df_laudos_pd['DS_LAUDO_MEDICO'].astype(str).str.strip().str.len() > 0]
    count_depois_filtro = len(df_laudos_pd)
    if count_antes_filtro > count_depois_filtro:
        print(f"🧹 Removidos {count_antes_filtro - count_depois_filtro} laudos vazios")

if len(df_laudos_pd) == 0:
    print(f"⚠️ Nenhum laudo encontrado para o período {data_inicio} - {data_fim}")
    dbutils.notebook.exit("Nenhum laudo encontrado")

print(f"✅ {len(df_laudos_pd):,} laudos extraídos com sucesso!")

# Limpar tabela temporária do Oracle
try:
    run_sql("TRUNCATE TABLE temp_proc_radiologia")
    print("🧹 Tabela temporária do Oracle limpa")
except:
    pass

# Renomear colunas para minúsculo (padrão Delta Lake)
df_laudos_pd.columns = [col.lower() for col in df_laudos_pd.columns]

# Combinar data + hora em timestamp
# HR_PROCEDIMENTO_REALIZADO está em segundos desde meia-noite
import pandas as pd
df_laudos_pd['dt_procedimento_realizado'] = pd.to_datetime(df_laudos_pd['dt_procedimento_realizado'])
df_laudos_pd['hr_segundos'] = pd.to_numeric(df_laudos_pd['hr_procedimento_realizado'], errors='coerce').fillna(0)
df_laudos_pd['dt_procedimento_realizado'] = df_laudos_pd['dt_procedimento_realizado'] + pd.to_timedelta(df_laudos_pd['hr_segundos'], unit='s')

# Remover coluna auxiliar
df_laudos_pd = df_laudos_pd.drop(columns=['hr_procedimento_realizado', 'hr_segundos'])

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

# Distribuição por procedimento
print("\n📋 Distribuição por procedimento (Top 10):")
df_laudos.groupBy('cd_procedimento') \
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
    'procedimentos_ativos': int(len(lista_codigos)),
    'procedimentos_realizados': int(total_procedimentos),
    'laudos_extraidos': int(count_depois),  # Após remoção de duplicatas
    'total_bronze': int(total_bronze),
    'dt_execucao': datetime.now().isoformat()
}

# Exibir métricas
print("\n" + "="*70)
print("📈 MÉTRICAS DO PROCESSAMENTO")
print("="*70)
for key, value in metricas.items():
    print(f"   {key:.<40} {value:>25}")
print("="*70)

# Finalização
print("\n✅ Processamento concluído com sucesso!")

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

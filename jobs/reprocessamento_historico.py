# Databricks notebook source
# MAGIC %md
# MAGIC # Reprocessamento Histórico de Laudos
# MAGIC 
# MAGIC **Objetivo:** Processar laudos de períodos anteriores em lotes semanais
# MAGIC 
# MAGIC **Uso:**
# MAGIC - Carga inicial histórica
# MAGIC - Reprocessamento de períodos específicos
# MAGIC - Correção de dados após mudanças
# MAGIC 
# MAGIC **Estratégia:**
# MAGIC - Processamento em **lotes semanais** (evita sobrecarga)
# MAGIC - Mesma lógica do job diário (tabela temp Oracle)
# MAGIC - Merge inteligente (não duplica dados)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Setup

# COMMAND ----------

# MAGIC %run /Workspace/Libraries/Lake

# COMMAND ----------

from pyspark.sql.functions import *
from pyspark.sql.types import *
from datetime import datetime, timedelta
import pandas as pd

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Parâmetros

# COMMAND ----------

# Widgets para configuração
dbutils.widgets.text("data_inicio", "", "Data Início (YYYY-MM-DD)")
dbutils.widgets.text("data_fim", "", "Data Fim (YYYY-MM-DD)")
dbutils.widgets.dropdown("tamanho_lote", "7", ["7", "14", "30"], "Dias por Lote")
dbutils.widgets.dropdown("modo_teste", "false", ["true", "false"], "Modo Teste (apenas conta)")

# Obter parâmetros
data_inicio_param = dbutils.widgets.get("data_inicio")
data_fim_param = dbutils.widgets.get("data_fim")
dias_por_lote = int(dbutils.widgets.get("tamanho_lote"))
modo_teste = dbutils.widgets.get("modo_teste") == "true"

# Validar parâmetros
if not data_inicio_param or not data_fim_param:
    raise ValueError("❌ Você deve especificar data_inicio e data_fim!")

data_inicio = datetime.strptime(data_inicio_param, '%Y-%m-%d').date()
data_fim = datetime.strptime(data_fim_param, '%Y-%m-%d').date()

if data_inicio >= data_fim:
    raise ValueError("❌ data_inicio deve ser anterior a data_fim!")

# Validar modo_execucao contra tabela de domínio
modo_execucao = "reprocessamento_historico"
df_modos_validos = spark.sql("""
    SELECT codigo 
    FROM innovation_dev.gold.radiologia_laudos_modo_execucao 
    WHERE ativo = TRUE
""")
modos_validos = [row.codigo for row in df_modos_validos.collect()]

if modo_execucao not in modos_validos:
    raise ValueError(f"❌ Modo de execução inválido: '{modo_execucao}'. Valores válidos: {modos_validos}")

# Calcular lotes
total_dias = (data_fim - data_inicio).days
num_lotes = (total_dias // dias_por_lote) + (1 if total_dias % dias_por_lote > 0 else 0)

# Configuração
SCHEMA_GOLD = "innovation_dev.gold"
SCHEMA_BRONZE = "innovation_dev.bronze"
TABLE_PROCEDIMENTOS_GOLD = f"{SCHEMA_GOLD}.radiologia_laudos_procedimentos"
TABLE_LAUDOS_BRONZE = f"{SCHEMA_BRONZE}.radiologia_laudos_extraidos"

print(f"""
╔══════════════════════════════════════════════════════════════╗
║  REPROCESSAMENTO HISTÓRICO DE LAUDOS                        ║
╠══════════════════════════════════════════════════════════════╣
║  Período Total:      {data_inicio} até {data_fim}            
║  Total de Dias:      {total_dias} dias                       
║  Tamanho do Lote:    {dias_por_lote} dias                    
║  Número de Lotes:    {num_lotes} lotes                       
║  Modo Teste:         {'SIM (apenas contagem)' if modo_teste else 'NÃO (processamento real)'}
║  Tabela Destino:     {TABLE_LAUDOS_BRONZE}                   
╚══════════════════════════════════════════════════════════════╝
""")

if modo_teste:
    print("⚠️  MODO TESTE ATIVADO - Nenhum dado será salvo!")
    print("   Apenas contagens serão exibidas para validação.\n")

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
# MAGIC ## 4. Buscar Procedimentos Ativos

# COMMAND ----------

print("📋 Buscando procedimentos ativos do Gold...")

df_procedimentos = spark.sql(f"""
    SELECT cd_procedimento
    FROM {TABLE_PROCEDIMENTOS_GOLD}
    WHERE ativo = true
""")

lista_codigos = [row.cd_procedimento for row in df_procedimentos.collect()]
codigos_csv = ','.join(map(str, lista_codigos))

print(f"✅ {len(lista_codigos)} procedimentos ativos encontrados")

if len(lista_codigos) == 0:
    dbutils.notebook.exit("⚠️ Nenhum procedimento ativo encontrado!")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Processar em Lotes

# COMMAND ----------

import time

# Estatísticas globais
total_procedimentos_realizados = 0
total_laudos_extraidos = 0
total_tempo_processamento = 0
lotes_processados = 0
lotes_com_erro = []

print("🚀 Iniciando processamento em lotes...\n")
print("="*70)

for i in range(num_lotes):
    lote_inicio = data_inicio + timedelta(days=i * dias_por_lote)
    lote_fim_calculado = lote_inicio + timedelta(days=dias_por_lote)
    lote_fim = lote_fim_calculado if lote_fim_calculado < data_fim else data_fim
    
    print(f"\n📦 LOTE {i+1}/{num_lotes}")
    print(f"   Período: {lote_inicio} até {lote_fim}")
    print(f"   Dias: {(lote_fim - lote_inicio).days}")
    print("-"*70)
    
    inicio_lote = time.time()
    
    try:
        # Criar/limpar tabela temporária no Oracle
        # Primeiro tentar dropar (se existir com estrutura antiga)
        try:
            run_sql("DROP TABLE temp_proc_radiologia")
            print("   🗑️  Tabela temporária antiga removida")
        except:
            pass  # Não existe, tudo bem
        
        # Criar nova tabela
        query_create_temp = """
        CREATE GLOBAL TEMPORARY TABLE temp_proc_radiologia (
            CD_ATENDIMENTO NUMBER,
            CD_OCORRENCIA NUMBER,
            CD_ORDEM NUMBER,
            CD_PROCEDIMENTO NUMBER,
            DT_PROCEDIMENTO_REALIZADO DATE,
            HR_PROCEDIMENTO_REALIZADO NUMBER
        ) ON COMMIT PRESERVE ROWS
        """
        
        run_sql(query_create_temp)
        print("   ✅ Tabela temporária criada")
        
        # Popular tabela temporária (HSP + PSC)
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
              AND PREA.DT_PROCEDIMENTO_REALIZADO >= DATE '{lote_inicio}'
              AND PREA.DT_PROCEDIMENTO_REALIZADO < DATE '{lote_fim}'
            
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
              AND PREA.DT_PROCEDIMENTO_REALIZADO >= DATE '{lote_inicio}'
              AND PREA.DT_PROCEDIMENTO_REALIZADO < DATE '{lote_fim}'
        )
        """
        
        run_sql(query_insert_temp)
        
        # Contar procedimentos
        query_count = "SELECT COUNT(*) as TOTAL FROM temp_proc_radiologia"
        df_count = run_sql(query_count)
        count_procedimentos = df_count['TOTAL'].iloc[0]
        
        print(f"   📊 {count_procedimentos:,} procedimentos realizados")
        total_procedimentos_realizados += count_procedimentos
        
        if count_procedimentos == 0:
            print(f"   ⚠️  Nenhum procedimento neste período, pulando...")
            continue
        
        # Extrair laudos (HSP + PSC)
        query_laudos = """
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
                'HSP' as FONTE,
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
                'PSC' as FONTE,
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
        
        df_laudos_pd = run_sql(query_laudos)
        
        # Filtrar laudos vazios
        if len(df_laudos_pd) > 0:
            df_laudos_pd = df_laudos_pd[df_laudos_pd['DS_LAUDO_MEDICO'].astype(str).str.strip().str.len() > 0]
        
        count_laudos = len(df_laudos_pd)
        print(f"   📄 {count_laudos:,} laudos extraídos")
        total_laudos_extraidos += count_laudos
        
        if count_laudos == 0:
            print(f"   ⚠️  Nenhum laudo encontrado, pulando...")
            continue
        
        # Modo teste: apenas mostra estatísticas
        if modo_teste:
            print(f"   🧪 MODO TESTE - Estatísticas:")
            print(f"      - Accession numbers únicos: {df_laudos_pd['ACCESSION_NUMBER'].nunique()}")
            print(f"      - Procedimentos distintos: {df_laudos_pd['CD_PROCEDIMENTO'].nunique()}")
            print(f"      - Pacientes distintos: {df_laudos_pd['CD_PACIENTE'].nunique()}")
            lotes_processados += 1
            continue
        
        # Processar e salvar
        df_laudos_pd.columns = [col.lower() for col in df_laudos_pd.columns]
        
        # Combinar data + hora em timestamp
        # HR_PROCEDIMENTO_REALIZADO está em segundos desde meia-noite
        import pandas as pd
        df_laudos_pd['tms_procedimento_realizado'] = pd.to_datetime(df_laudos_pd['dt_procedimento_realizado'])
        df_laudos_pd['hr_segundos'] = pd.to_numeric(df_laudos_pd['hr_procedimento_realizado'], errors='coerce').fillna(0)
        df_laudos_pd['tms_procedimento_realizado'] = df_laudos_pd['tms_procedimento_realizado'] + pd.to_timedelta(df_laudos_pd['hr_segundos'], unit='s')
        
        # Remover colunas auxiliares
        df_laudos_pd = df_laudos_pd.drop(columns=['dt_procedimento_realizado', 'hr_procedimento_realizado', 'hr_segundos'])
        
        df_laudos = spark.createDataFrame(df_laudos_pd)
        
        # Remover duplicatas
        df_laudos = df_laudos.dropDuplicates(['accession_number'])
        
        # Adicionar metadados
        df_laudos_final = df_laudos.withColumn("tms_carga", current_timestamp()) \
            .withColumn("modo_execucao", lit("reprocessamento_historico"))
        
        # Salvar no Delta Lake
        from delta.tables import DeltaTable
        
        if not spark.catalog.tableExists(TABLE_LAUDOS_BRONZE):
            # Primeira vez: criar tabela
            df_laudos_final.write \
                .format("delta") \
                .mode("overwrite") \
                .partitionBy("ano_mes") \
                .option("overwriteSchema", "true") \
                .saveAsTable(TABLE_LAUDOS_BRONZE)
            print(f"   ✅ Tabela criada e {count_laudos:,} laudos salvos")
        else:
            # Merge para evitar duplicatas
            delta_table = DeltaTable.forName(spark, TABLE_LAUDOS_BRONZE)
            
            delta_table.alias("target").merge(
                df_laudos_final.alias("source"),
                "target.accession_number = source.accession_number"
            ).whenMatchedUpdateAll() \
             .whenNotMatchedInsertAll() \
             .execute()
            
            print(f"   ✅ Merge concluído - {count_laudos:,} laudos processados")
        
        lotes_processados += 1
        
    except Exception as e:
        print(f"   ❌ ERRO no lote {i+1}: {str(e)[:200]}")
        lotes_com_erro.append({
            'lote': i+1,
            'periodo': f"{lote_inicio} - {lote_fim}",
            'erro': str(e)[:500]
        })
        continue
    
    finally:
        # Limpar tabela temporária
        try:
            run_sql("TRUNCATE TABLE temp_proc_radiologia")
        except:
            pass
    
    tempo_lote = time.time() - inicio_lote
    total_tempo_processamento += tempo_lote
    print(f"   ⏱️  Tempo: {tempo_lote:.1f}s")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Resumo Final

# COMMAND ----------

print("\n" + "="*70)
print("📊 RESUMO DO REPROCESSAMENTO HISTÓRICO")
print("="*70)
print(f"Período processado:          {data_inicio} até {data_fim}")
print(f"Total de lotes:              {num_lotes}")
print(f"Lotes processados com sucesso: {lotes_processados}")
print(f"Lotes com erro:              {len(lotes_com_erro)}")
print(f"Procedimentos realizados:    {total_procedimentos_realizados:,}")
print(f"Laudos extraídos:            {total_laudos_extraidos:,}")
print(f"Tempo total:                 {total_tempo_processamento/60:.1f} minutos")
tempo_medio = total_tempo_processamento / lotes_processados if lotes_processados > 0 else 0
print(f"Tempo médio por lote:        {tempo_medio:.1f} segundos")
print("="*70)

if modo_teste:
    print("\n⚠️  MODO TESTE - Nenhum dado foi salvo no Delta Lake!")
    print("   Para processar de verdade, configure modo_teste = false\n")

if lotes_com_erro:
    print("\n⚠️  LOTES COM ERRO:")
    for erro in lotes_com_erro:
        print(f"\n   Lote {erro['lote']} ({erro['periodo']}):")
        print(f"   {erro['erro']}")

if not modo_teste and lotes_processados > 0:
    print("\n✅ Reprocessamento concluído!")
    print(f"   Dados salvos em: {TABLE_LAUDOS_BRONZE}")
    
    # Otimizar tabela
    print("\n🔧 Otimizando tabela Delta...")
    spark.sql(f"OPTIMIZE {TABLE_LAUDOS_BRONZE}")
    print("✅ Otimização concluída!")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7. Verificação (Opcional)

# COMMAND ----------

if not modo_teste and lotes_processados > 0:
    print("🔍 Verificando dados salvos...\n")
    
    # Contar por período
    df_verificacao = spark.sql(f"""
        SELECT 
            ano_mes,
            COUNT(*) as total_laudos,
            COUNT(DISTINCT accession_number) as laudos_unicos,
            MIN(tms_procedimento_realizado) as data_min,
            MAX(tms_procedimento_realizado) as data_max
        FROM {TABLE_LAUDOS_BRONZE}
        WHERE modo_execucao = 'reprocessamento_historico'
          AND DATE(tms_carga) >= '{data_inicio}'
          AND DATE(tms_carga) < '{data_fim}'
        GROUP BY ano_mes
        ORDER BY ano_mes
    """)
    
    df_verificacao.show(100, truncate=False)
    
    # Verificar duplicatas
    print("\n🔍 Verificando duplicatas...")
    df_duplicatas = spark.sql(f"""
        SELECT accession_number, COUNT(*) as count
        FROM {TABLE_LAUDOS_BRONZE}
        WHERE modo_execucao = 'reprocessamento_historico'
          AND DATE(tms_carga) >= '{data_inicio}'
          AND DATE(tms_carga) < '{data_fim}'
        GROUP BY accession_number
        HAVING COUNT(*) > 1
    """)
    
    count_duplicatas = df_duplicatas.count()
    if count_duplicatas == 0:
        print("✅ Nenhuma duplicata encontrada!")
    else:
        print(f"⚠️  {count_duplicatas} duplicatas encontradas:")
        df_duplicatas.show(20)

# COMMAND ----------

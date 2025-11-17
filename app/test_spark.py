"""
Script de teste para verificar se Spark está disponível no Streamlit
Execute este script no Databricks para testar a configuração
"""

import streamlit as st
import sys
import os

st.title("🧪 Teste de Configuração Spark + Lake")

st.markdown("---")
st.header("1. Verificações de Ambiente")

# Verificar Databricks
col1, col2 = st.columns(2)
with col1:
    if os.path.exists('/Workspace'):
        st.success("✅ Rodando no Databricks")
    else:
        st.error("❌ Não está no Databricks")

with col2:
    if os.path.exists('/Workspace/Libraries/Lake'):
        st.success("✅ Biblioteca Lake encontrada")
    else:
        st.error("❌ Biblioteca Lake não encontrada")

st.markdown("---")
st.header("2. Teste de Imports")

# Testar PySpark
try:
    from pyspark.sql import SparkSession
    st.success("✅ PySpark importado com sucesso")
    
    try:
        spark = SparkSession.builder.getOrCreate()
        st.success(f"✅ SparkSession criada: {spark.version}")
    except Exception as e:
        st.error(f"❌ Erro ao criar SparkSession: {str(e)}")
except Exception as e:
    st.error(f"❌ Erro ao importar PySpark: {str(e)}")

# Testar dbutils
try:
    from pyspark.dbutils import DBUtils
    from pyspark.sql import SparkSession
    spark = SparkSession.builder.getOrCreate()
    dbutils = DBUtils(spark)
    st.success("✅ dbutils disponível")
except Exception as e:
    st.error(f"❌ dbutils não disponível: {str(e)}")

st.markdown("---")
st.header("3. Teste da Biblioteca Lake")

# Testar importação Lake
try:
    sys.path.insert(0, '/Workspace/Libraries')
    import Lake
    st.success("✅ Biblioteca Lake importada")
    
    # Verificar funções disponíveis
    if hasattr(Lake, 'connect_to_datalake'):
        st.success("✅ Função connect_to_datalake encontrada")
    else:
        st.warning("⚠️ Função connect_to_datalake não encontrada")
    
    if hasattr(Lake, 'run_sql'):
        st.success("✅ Função run_sql encontrada")
    else:
        st.warning("⚠️ Função run_sql não encontrada")
        
except Exception as e:
    st.error(f"❌ Erro ao importar Lake: {str(e)}")

st.markdown("---")
st.header("4. Teste de Conexão Lake")

if st.button("🔌 Testar Conexão"):
    try:
        from database.lake_connection import init_lake_connection
        
        with st.spinner("Conectando ao Oracle Lake..."):
            success = init_lake_connection()
        
        if success:
            st.success("✅ Conexão Lake estabelecida com sucesso!")
            
            # Testar query simples
            st.markdown("### Testando query no Oracle Lake...")
            try:
                from database.lake_connection import execute_lake_query
                
                query = """
                SELECT COUNT(*) as total
                FROM RAWZN.RAW_HSP_TB_PROCEDIMENTO
                LIMIT 1
                """
                
                df = execute_lake_query(query)
                if len(df) > 0:
                    st.success(f"✅ Query executada! Total de procedimentos: {df['total'].iloc[0]}")
                else:
                    st.warning("⚠️ Query retornou vazio")
                    
            except Exception as e:
                st.error(f"❌ Erro ao executar query: {str(e)}")
        else:
            st.error("❌ Falha ao conectar ao Lake")
            
    except Exception as e:
        st.error(f"❌ Erro: {str(e)}")
        st.exception(e)

st.markdown("---")
st.header("5. Informações do Sistema")

with st.expander("Ver detalhes"):
    st.code(f"""
Python version: {sys.version}
Python path: {sys.path[:3]}
Working directory: {os.getcwd()}
    """)

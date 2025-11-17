"""
Conexão com Oracle Lake usando biblioteca Lake do Databricks
Similar ao que é usado nos notebooks
"""

import streamlit as st
import pandas as pd
import os
import sys

# Flag para indicar se a conexão Lake está disponível
LAKE_CONNECTED = False

def init_lake_connection():
    """
    Inicializa conexão com Oracle Lake usando biblioteca Lake
    Similar ao %run /Workspace/Libraries/Lake nos notebooks
    """
    global LAKE_CONNECTED
    
    try:
        # Verificar se estamos no Databricks
        if not os.path.exists('/Workspace'):
            st.warning("⚠️ Não está rodando no Databricks. Biblioteca Lake não disponível.")
            return False
        
        # Adicionar path da biblioteca Lake
        lake_path = '/Workspace/Libraries'
        if lake_path not in sys.path:
            sys.path.insert(0, lake_path)
        
        # Importar a biblioteca Lake
        try:
            # A biblioteca Lake injeta funções globalmente quando importada
            import Lake
        except ImportError:
            st.error("❌ Biblioteca Lake não encontrada em /Workspace/Libraries/Lake")
            return False
        
        # Verificar se run_sql está disponível
        if 'run_sql' not in globals():
            # Tentar importar do módulo Lake
            try:
                from Lake import run_sql, connect_to_datalake
                # Injetar no namespace global
                globals()['run_sql'] = run_sql
                globals()['connect_to_datalake'] = connect_to_datalake
            except:
                st.error("❌ Função run_sql não disponível")
                return False
        
        # Conectar ao datalake se ainda não conectado
        if not LAKE_CONNECTED:
            try:
                # Importar dbutils
                from pyspark.dbutils import DBUtils
                from pyspark.sql import SparkSession
                
                spark = SparkSession.builder.getOrCreate()
                dbutils = DBUtils(spark)
                
                # Conectar usando credenciais do secrets
                connect_to_datalake(
                    username="USR_PROD_INFORMATICA_SAUDE",
                    password=dbutils.secrets.get(scope="INNOVATION_RAW", key="USR_PROD_INFORMATICA_SAUDE"),
                    layer="RAWZN",
                    level="LOW",
                    dbx_secret_scope="INNOVATION_RAW"
                )
                
                LAKE_CONNECTED = True
                st.success("✅ Conexão com Oracle Lake estabelecida!")
                return True
                
            except Exception as e:
                st.error(f"❌ Erro ao conectar ao Lake: {str(e)}")
                return False
        
        return True
        
    except Exception as e:
        st.error(f"❌ Erro ao inicializar Lake: {str(e)}")
        return False


def execute_lake_query(query):
    """
    Executa query no Oracle Lake usando run_sql
    
    Args:
        query: Query SQL para executar
        
    Returns:
        DataFrame pandas com os resultados
    """
    try:
        if not LAKE_CONNECTED:
            if not init_lake_connection():
                st.error("❌ Conexão Lake não disponível")
                return pd.DataFrame()
        
        # Executar query usando run_sql (injetado pela biblioteca Lake)
        if 'run_sql' in globals():
            df = run_sql(query)
            return df
        else:
            st.error("❌ Função run_sql não disponível")
            return pd.DataFrame()
            
    except Exception as e:
        st.error(f"❌ Erro ao executar query: {str(e)}")
        return pd.DataFrame()

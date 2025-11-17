"""
Gerenciamento de conexões com Databricks SQL Warehouse e Oracle Lake
"""

import streamlit as st
import pandas as pd
from databricks import sql
from databricks.sdk.core import Config
from config import ORACLE_TABLE_PROCEDIMENTO_HSP, MAX_RESULTADOS_BUSCA
import os

# Configuração Databricks
cfg = Config()

@st.cache_resource
def get_databricks_connection(http_path):
    """
    Conecta ao SQL Warehouse do Databricks para acessar Delta Lake
    
    Args:
        http_path: Caminho HTTP do SQL Warehouse
        
    Returns:
        Connection object do Databricks SQL
    """
    try:
        if not http_path:
            raise ValueError("DATABRICKS_HTTP_PATH não encontrado")
        
        if not http_path.startswith('/'):
            http_path = '/' + http_path
        
        connection = sql.connect(
            server_hostname=cfg.host,
            http_path=http_path,
            credentials_provider=lambda: cfg.authenticate,
        )
        
        return connection
        
    except Exception as e:
        error_details = {
            "error": str(e),
            "error_type": type(e).__name__,
            "host": cfg.host if hasattr(cfg, 'host') else "não disponível",
            "http_path": http_path if 'http_path' in locals() else "não disponível",
        }
        st.session_state.connection_error = error_details
        raise


def buscar_procedimento_oracle(conn, cd_procedimento=None, termo_busca=None):
    """
    Busca procedimentos no Oracle Lake (RAWZN.RAW_HSP_TB_PROCEDIMENTO)
    usando a mesma conexão SQL Warehouse do Databricks.
    
    Args:
        conn: Conexão Databricks SQL Warehouse
        cd_procedimento: Código do procedimento para busca exata
        termo_busca: Termo para busca LIKE no nome do procedimento
        
    Returns:
        DataFrame com CD_PROCEDIMENTO e NM_PROCEDIMENTO
    """
    try:
        # Construir query
        if cd_procedimento:
            query = f"""
            SELECT DISTINCT CD_PROCEDIMENTO, NM_PROCEDIMENTO
            FROM {ORACLE_TABLE_PROCEDIMENTO_HSP}
            WHERE CD_PROCEDIMENTO = {cd_procedimento}
            """
        elif termo_busca:
            query = f"""
            SELECT DISTINCT CD_PROCEDIMENTO, NM_PROCEDIMENTO
            FROM {ORACLE_TABLE_PROCEDIMENTO_HSP}
            WHERE UPPER(NM_PROCEDIMENTO) LIKE UPPER('%{termo_busca}%')
            ORDER BY NM_PROCEDIMENTO
            LIMIT {MAX_RESULTADOS_BUSCA}
            """
        else:
            return pd.DataFrame()
        
        # Executar query via SQL Warehouse
        with conn.cursor() as cursor:
            cursor.execute(query)
            result = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            df = pd.DataFrame(result, columns=columns)
            return df
            
    except Exception as e:
        st.error(f"❌ Erro ao buscar no Oracle Lake: {str(e)}")
        st.info("💡 Verifique se o SQL Warehouse tem acesso ao schema RAWZN")
        return pd.DataFrame()

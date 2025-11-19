"""
Gerenciamento de conexão com Databricks SQL Warehouse (Delta Lake)
"""

import streamlit as st
from databricks import sql
from databricks.sdk.core import Config

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

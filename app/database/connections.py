"""
Gerenciamento de conexões com Databricks SQL Warehouse e Oracle Lake
"""

import streamlit as st
import pandas as pd
from databricks import sql
from databricks.sdk.core import Config
from config import ORACLE_TABLE_PROCEDIMENTO_HSP, MAX_RESULTADOS_BUSCA

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


def buscar_procedimento_oracle(cd_procedimento=None, termo_busca=None):
    """
    Busca procedimentos no Oracle Lake (RAWZN.RAW_HSP_TB_PROCEDIMENTO)
    
    NOTA: Esta função só funciona dentro do Databricks workspace com acesso ao run_sql.
    No ambiente local, retorna dados mockados para desenvolvimento.
    
    Args:
        cd_procedimento: Código do procedimento para busca exata
        termo_busca: Termo para busca LIKE no nome do procedimento
        
    Returns:
        DataFrame com CD_PROCEDIMENTO e NM_PROCEDIMENTO
    """
    try:
        # Verificar se estamos no ambiente Databricks
        if 'run_sql' in globals():
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
                FETCH FIRST {MAX_RESULTADOS_BUSCA} ROWS ONLY
                """
            else:
                return pd.DataFrame()
            
            # Executar via run_sql (função do Lake)
            df = run_sql(query)
            return df
        else:
            # Ambiente local - retornar mock para desenvolvimento
            st.warning("⚠️ Função run_sql não disponível (ambiente local). Usando dados mockados.")
            if cd_procedimento:
                return pd.DataFrame({
                    'CD_PROCEDIMENTO': [cd_procedimento],
                    'NM_PROCEDIMENTO': [f'PROCEDIMENTO MOCK {cd_procedimento}']
                })
            else:
                return pd.DataFrame({
                    'CD_PROCEDIMENTO': [12345, 67890, 11111],
                    'NM_PROCEDIMENTO': [
                        'TOMOGRAFIA COMPUTADORIZADA DE ABDOME MOCK',
                        'ANGIOTOMOGRAFIA DE AORTA MOCK',
                        'RESSONANCIA MAGNETICA MOCK'
                    ]
                })
    except Exception as e:
        st.error(f"❌ Erro ao buscar no Oracle: {str(e)}")
        return pd.DataFrame()

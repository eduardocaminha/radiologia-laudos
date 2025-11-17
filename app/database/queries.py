"""
Funções para execução de queries e comandos SQL no Databricks
"""

import streamlit as st
import pandas as pd


def execute_query(conn, query: str) -> pd.DataFrame:
    """
    Executa query SQL no Databricks e retorna pandas DataFrame
    
    Args:
        conn: Conexão com Databricks SQL Warehouse
        query: Query SQL a ser executada
        
    Returns:
        DataFrame com os resultados
    """
    try:
        with conn.cursor() as cursor:
            cursor.execute(query)
            result = cursor.fetchall_arrow()
            if result is not None:
                return result.to_pandas()
            return pd.DataFrame()
    except Exception as e:
        st.error(f"❌ Erro ao executar query: {str(e)}")
        return pd.DataFrame()


def execute_command(conn, command: str) -> bool:
    """
    Executa comando SQL (INSERT, UPDATE, DELETE, CREATE TABLE)
    
    Args:
        conn: Conexão com Databricks SQL Warehouse
        command: Comando SQL a ser executado
        
    Returns:
        True se sucesso, False se erro
    """
    try:
        with conn.cursor() as cursor:
            cursor.execute(command)
        return True
    except Exception as e:
        st.error(f"❌ Erro ao executar comando: {str(e)}")
        return False

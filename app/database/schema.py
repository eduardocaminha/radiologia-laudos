"""
Definição e criação do schema das tabelas Gold no Delta Lake
"""

import streamlit as st
from config import SCHEMA_GOLD, TABLE_MODALIDADES, TABLE_DESCRICOES, TABLE_PROCEDIMENTOS
from .queries import execute_command, execute_query


def criar_tabelas_gold(conn):
    """
    Cria as tabelas Gold no Delta Lake se não existirem
    
    Args:
        conn: Conexão com Databricks SQL Warehouse
        
    Returns:
        True se sucesso, False se erro
    """
    
    # 1. Tabela de Modalidades
    sql_modalidades = f"""
    CREATE TABLE IF NOT EXISTS {TABLE_MODALIDADES} (
        id_modalidade INT GENERATED ALWAYS AS IDENTITY,
        nome_modalidade STRING NOT NULL,
        ativo BOOLEAN DEFAULT TRUE,
        dt_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
        dt_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
    )
    USING DELTA
    COMMENT 'Catálogo de modalidades radiológicas (TC, ANGIOTC, RM, etc.)'
    """
    
    # 2. Tabela de Descrições
    sql_descricoes = f"""
    CREATE TABLE IF NOT EXISTS {TABLE_DESCRICOES} (
        id_descricao INT GENERATED ALWAYS AS IDENTITY,
        descricao STRING NOT NULL,
        ativo BOOLEAN DEFAULT TRUE,
        dt_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
        dt_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
    )
    USING DELTA
    COMMENT 'Catálogo de descrições anatômicas/técnicas dos procedimentos'
    """
    
    # 3. Tabela de Procedimentos
    sql_procedimentos = f"""
    CREATE TABLE IF NOT EXISTS {TABLE_PROCEDIMENTOS} (
        cd_procedimento BIGINT NOT NULL,
        nm_procedimento STRING NOT NULL,
        id_modalidade INT NOT NULL,
        descricao_1 STRING,
        descricao_2 STRING,
        descricao_3 STRING,
        descricao_4 STRING,
        descricao_5 STRING,
        descricao_6 STRING,
        descricao_7 STRING,
        ativo BOOLEAN DEFAULT TRUE,
        dt_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
        dt_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
        PRIMARY KEY (cd_procedimento)
    )
    USING DELTA
    COMMENT 'Procedimentos radiológicos vinculados a modalidades e descrições'
    """
    
    try:
        execute_command(conn, sql_modalidades)
        execute_command(conn, sql_descricoes)
        execute_command(conn, sql_procedimentos)
        return True
    except Exception as e:
        st.error(f"❌ Erro ao criar tabelas: {str(e)}")
        return False


def verificar_tabelas_existem(conn):
    """
    Verifica se as tabelas Gold já existem
    
    Args:
        conn: Conexão com Databricks SQL Warehouse
        
    Returns:
        True se todas as 3 tabelas existem, False caso contrário
    """
    try:
        query = f"""
        SELECT table_name 
        FROM {SCHEMA_GOLD.split('.')[0]}.information_schema.tables 
        WHERE table_schema = '{SCHEMA_GOLD.split('.')[1]}'
        AND table_name IN ('radiologia_laudos_modalidades', 'radiologia_laudos_descricoes', 'radiologia_laudos_procedimentos')
        """
        df = execute_query(conn, query)
        return len(df) == 3
    except:
        return False

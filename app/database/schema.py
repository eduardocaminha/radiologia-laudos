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
        id_modalidade BIGINT GENERATED ALWAYS AS IDENTITY,
        nome_modalidade STRING NOT NULL,
        ativo BOOLEAN,
        dt_cadastro TIMESTAMP,
        dt_atualizacao TIMESTAMP
    )
    USING DELTA
    TBLPROPERTIES (
        'delta.feature.allowColumnDefaults' = 'supported',
        'delta.columnMapping.mode' = 'name'
    )
    COMMENT 'Catálogo de modalidades radiológicas (TC, ANGIOTC, RM, etc.)'
    """
    
    # 2. Tabela de Descrições
    sql_descricoes = f"""
    CREATE TABLE IF NOT EXISTS {TABLE_DESCRICOES} (
        id_descricao BIGINT GENERATED ALWAYS AS IDENTITY,
        descricao STRING NOT NULL,
        ativo BOOLEAN,
        dt_cadastro TIMESTAMP,
        dt_atualizacao TIMESTAMP
    )
    USING DELTA
    TBLPROPERTIES (
        'delta.feature.allowColumnDefaults' = 'supported',
        'delta.columnMapping.mode' = 'name'
    )
    COMMENT 'Catálogo de descrições anatômicas/técnicas dos procedimentos'
    """
    
    # 3. Tabela de Procedimentos
    sql_procedimentos = f"""
    CREATE TABLE IF NOT EXISTS {TABLE_PROCEDIMENTOS} (
        cd_procedimento BIGINT NOT NULL,
        nm_procedimento STRING NOT NULL,
        id_modalidade BIGINT NOT NULL,
        id_descricao_1 BIGINT,
        id_descricao_2 BIGINT,
        id_descricao_3 BIGINT,
        id_descricao_4 BIGINT,
        id_descricao_5 BIGINT,
        id_descricao_6 BIGINT,
        id_descricao_7 BIGINT,
        ativo BOOLEAN,
        dt_cadastro TIMESTAMP,
        dt_atualizacao TIMESTAMP,
        CONSTRAINT pk_procedimento PRIMARY KEY (cd_procedimento)
    )
    USING DELTA
    TBLPROPERTIES (
        'delta.feature.allowColumnDefaults' = 'supported',
        'delta.columnMapping.mode' = 'name'
    )
    COMMENT 'Procedimentos radiológicos vinculados a modalidades e descrições (relacionamento lógico via IDs)'
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


def deletar_tabelas_gold(conn):
    """
    Deleta todas as tabelas Gold (usar com cuidado!)
    
    Args:
        conn: Conexão com Databricks SQL Warehouse
        
    Returns:
        True se sucesso, False se erro
    """
    try:
        # Deletar na ordem inversa (boa prática)
        execute_command(conn, f"DROP TABLE IF EXISTS {TABLE_PROCEDIMENTOS}")
        st.info("🗑️ Tabela de procedimentos deletada")
        
        execute_command(conn, f"DROP TABLE IF EXISTS {TABLE_DESCRICOES}")
        st.info("🗑️ Tabela de descrições deletada")
        
        execute_command(conn, f"DROP TABLE IF EXISTS {TABLE_MODALIDADES}")
        st.info("🗑️ Tabela de modalidades deletada")
        
        st.success("✅ Todas as tabelas deletadas com sucesso!")
        return True
    except Exception as e:
        st.error(f"❌ Erro ao deletar tabelas: {str(e)}")
        return False

"""
Módulo de gerenciamento de Procedimentos
"""

import streamlit as st
import pandas as pd
from config import TABLE_PROCEDIMENTOS, TABLE_MODALIDADES, TABLE_DESCRICOES
from database import execute_query, execute_command


def listar_procedimentos(conn, apenas_ativos=True, id_modalidade=None):
    """
    Lista todos os procedimentos com suas descrições
    
    Args:
        conn: Conexão com Databricks
        apenas_ativos: Se True, retorna apenas procedimentos ativos
        id_modalidade: Filtrar por modalidade específica
        
    Returns:
        DataFrame com os procedimentos
    """
    filtros = []
    if apenas_ativos:
        filtros.append("p.ativo = TRUE")
    if id_modalidade:
        filtros.append(f"p.id_modalidade = {id_modalidade}")
    
    where_clause = f"WHERE {' AND '.join(filtros)}" if filtros else ""
    
    query = f"""
    SELECT 
        p.cd_procedimento,
        p.nm_procedimento,
        p.id_modalidade,
        m.nome_modalidade,
        p.id_descricao_1,
        p.id_descricao_2,
        p.id_descricao_3,
        p.id_descricao_4,
        p.id_descricao_5,
        p.id_descricao_6,
        p.id_descricao_7,
        d1.descricao as descricao_1,
        d2.descricao as descricao_2,
        d3.descricao as descricao_3,
        d4.descricao as descricao_4,
        d5.descricao as descricao_5,
        d6.descricao as descricao_6,
        d7.descricao as descricao_7,
        p.ativo,
        p.dt_cadastro
    FROM {TABLE_PROCEDIMENTOS} p
    INNER JOIN {TABLE_MODALIDADES} m ON p.id_modalidade = m.id_modalidade
    LEFT JOIN {TABLE_DESCRICOES} d1 ON p.id_descricao_1 = d1.id_descricao
    LEFT JOIN {TABLE_DESCRICOES} d2 ON p.id_descricao_2 = d2.id_descricao
    LEFT JOIN {TABLE_DESCRICOES} d3 ON p.id_descricao_3 = d3.id_descricao
    LEFT JOIN {TABLE_DESCRICOES} d4 ON p.id_descricao_4 = d4.id_descricao
    LEFT JOIN {TABLE_DESCRICOES} d5 ON p.id_descricao_5 = d5.id_descricao
    LEFT JOIN {TABLE_DESCRICOES} d6 ON p.id_descricao_6 = d6.id_descricao
    LEFT JOIN {TABLE_DESCRICOES} d7 ON p.id_descricao_7 = d7.id_descricao
    {where_clause}
    ORDER BY p.nm_procedimento
    """
    return execute_query(conn, query)


def obter_modalidades_ativas(conn):
    """Retorna lista de modalidades ativas"""
    query = f"""
    SELECT id_modalidade, nome_modalidade
    FROM {TABLE_MODALIDADES}
    WHERE ativo = TRUE
    ORDER BY nome_modalidade
    """
    return execute_query(conn, query)


def obter_descricoes_ativas(conn):
    """Retorna lista de descrições ativas"""
    query = f"""
    SELECT id_descricao, descricao
    FROM {TABLE_DESCRICOES}
    WHERE ativo = TRUE
    ORDER BY descricao
    """
    return execute_query(conn, query)


def adicionar_procedimento(conn, cd_procedimento, nm_procedimento, id_modalidade, ids_descricoes):
    """
    Adiciona um novo procedimento
    
    Args:
        conn: Conexão com Databricks
        cd_procedimento: Código do procedimento
        nm_procedimento: Nome do procedimento
        id_modalidade: ID da modalidade
        ids_descricoes: Lista com até 7 IDs de descrições
        
    Returns:
        True se sucesso, False se erro
    """
    # Verificar se já existe
    query_check = f"""
    SELECT COUNT(*) as total 
    FROM {TABLE_PROCEDIMENTOS} 
    WHERE cd_procedimento = {cd_procedimento}
    """
    df_check = execute_query(conn, query_check)
    
    if len(df_check) > 0 and df_check['total'].iloc[0] > 0:
        st.error(f"❌ Procedimento com código {cd_procedimento} já existe!")
        return False
    
    # Preparar IDs de descrições (até 7)
    desc_values = ["NULL"] * 7
    for i, id_desc in enumerate(ids_descricoes[:7]):
        if id_desc:
            desc_values[i] = str(id_desc)
    
    # Inserir
    command = f"""
    INSERT INTO {TABLE_PROCEDIMENTOS} (
        cd_procedimento, nm_procedimento, id_modalidade,
        id_descricao_1, id_descricao_2, id_descricao_3, id_descricao_4,
        id_descricao_5, id_descricao_6, id_descricao_7, ativo,
        dt_cadastro, dt_atualizacao
    )
    VALUES (
        {cd_procedimento}, '{nm_procedimento}', {id_modalidade},
        {desc_values[0]}, {desc_values[1]}, {desc_values[2]}, {desc_values[3]},
        {desc_values[4]}, {desc_values[5]}, {desc_values[6]}, TRUE,
        CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP()
    )
    """
    
    if execute_command(conn, command):
        st.success(f"✅ Procedimento {cd_procedimento} - {nm_procedimento} adicionado com sucesso!")
        return True
    return False


def alternar_status_procedimento(conn, cd_procedimento, ativo):
    """
    Ativa ou desativa um procedimento
    
    Args:
        conn: Conexão com Databricks
        cd_procedimento: Código do procedimento
        ativo: True para ativar, False para desativar
        
    Returns:
        True se sucesso, False se erro
    """
    command = f"""
    UPDATE {TABLE_PROCEDIMENTOS}
    SET ativo = {str(ativo).upper()},
        dt_atualizacao = CURRENT_TIMESTAMP()
    WHERE cd_procedimento = {cd_procedimento}
    """
    
    if execute_command(conn, command):
        status = "ativado" if ativo else "desativado"
        st.success(f"✅ Procedimento {status} com sucesso!")
        return True
    return False


def renderizar_pagina_procedimentos(conn):
    """
    Renderiza a página de gerenciamento de procedimentos
    
    Args:
        conn: Conexão com Databricks
    """
    st.subheader("🔬 Gerenciamento de Procedimentos")
    
    st.info("""
    ℹ️ **Gerenciamento de procedimentos:** Visualize, ative/desative procedimentos cadastrados no Delta Lake.
    Os procedimentos são vinculados a modalidades e descrições.
    """)
    
    # ===== LISTAR PROCEDIMENTOS =====
    st.markdown("### Procedimentos Cadastrados")
    
    # Filtros
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        mostrar_inativos = st.checkbox("Mostrar procedimentos inativos", value=False)
    
    with col2:
        df_modalidades = obter_modalidades_ativas(conn)
        opcoes_modalidades = ["Todas"] + df_modalidades['nome_modalidade'].tolist()
        filtro_modalidade = st.selectbox("Filtrar por modalidade:", opcoes_modalidades)
    
    with col3:
        if st.button("🔄 Atualizar", key="refresh_procedimentos"):
            st.rerun()
    
    # Determinar filtro de modalidade
    id_modalidade_filtro = None
    if filtro_modalidade != "Todas":
        id_modalidade_filtro = df_modalidades[
            df_modalidades['nome_modalidade'] == filtro_modalidade
        ]['id_modalidade'].iloc[0]
    
    # Carregar procedimentos
    df_procedimentos = listar_procedimentos(
        conn,
        apenas_ativos=not mostrar_inativos,
        id_modalidade=id_modalidade_filtro
    )
    
    if len(df_procedimentos) == 0:
        st.info("ℹ️ Nenhum procedimento encontrado.")
    else:
        st.markdown(f"**Total:** {len(df_procedimentos)} procedimento(s)")
        
        # Exibir procedimentos
        for idx, row in df_procedimentos.iterrows():
            with st.expander(f"{'✅' if row['ativo'] else '❌'} {row['cd_procedimento']} - {row['nm_procedimento']}"):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.markdown(f"**Modalidade:** {row['nome_modalidade']}")
                    st.markdown(f"**Código:** {row['cd_procedimento']}")
                    st.markdown(f"**Cadastro:** {row['dt_cadastro']}")
                    
                    # Descrições
                    descricoes = []
                    for i in range(1, 8):
                        desc = row[f'descricao_{i}']
                        if pd.notna(desc) and desc:
                            descricoes.append(desc)
                    
                    if descricoes:
                        st.markdown("**Descrições:**")
                        for desc in descricoes:
                            st.markdown(f"- {desc}")
                    else:
                        st.caption("_Sem descrições_")
                
                with col2:
                    # Botão Ativar/Desativar
                    if row['ativo']:
                        if st.button("🚫 Desativar", key=f"deactivate_proc_{row['cd_procedimento']}"):
                            alternar_status_procedimento(conn, row['cd_procedimento'], False)
                            st.rerun()
                    else:
                        if st.button("✅ Ativar", key=f"activate_proc_{row['cd_procedimento']}"):
                            alternar_status_procedimento(conn, row['cd_procedimento'], True)
                            st.rerun()

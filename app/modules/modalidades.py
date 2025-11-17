"""
Módulo de gerenciamento de Modalidades
"""

import streamlit as st
import pandas as pd
from config import TABLE_MODALIDADES
from database import execute_query, execute_command


def listar_modalidades(conn, apenas_ativas=True):
    """
    Lista todas as modalidades
    
    Args:
        conn: Conexão com Databricks
        apenas_ativas: Se True, retorna apenas modalidades ativas
        
    Returns:
        DataFrame com as modalidades
    """
    filtro = "WHERE ativo = TRUE" if apenas_ativas else ""
    query = f"""
    SELECT 
        id_modalidade,
        nome_modalidade,
        ativo,
        dt_cadastro,
        dt_atualizacao
    FROM {TABLE_MODALIDADES}
    {filtro}
    ORDER BY nome_modalidade
    """
    return execute_query(conn, query)


def adicionar_modalidade(conn, nome_modalidade):
    """
    Adiciona uma nova modalidade
    
    Args:
        conn: Conexão com Databricks
        nome_modalidade: Nome da modalidade
        
    Returns:
        True se sucesso, False se erro
    """
    # Verificar se já existe
    query_check = f"""
    SELECT COUNT(*) as total 
    FROM {TABLE_MODALIDADES} 
    WHERE UPPER(nome_modalidade) = UPPER('{nome_modalidade}')
    """
    df_check = execute_query(conn, query_check)
    
    if len(df_check) > 0 and df_check['total'].iloc[0] > 0:
        st.error(f"❌ Modalidade '{nome_modalidade}' já existe!")
        return False
    
    # Inserir
    command = f"""
    INSERT INTO {TABLE_MODALIDADES} (nome_modalidade, ativo, dt_cadastro, dt_atualizacao)
    VALUES ('{nome_modalidade}', TRUE, CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP())
    """
    
    if execute_command(conn, command):
        st.success(f"✅ Modalidade '{nome_modalidade}' adicionada com sucesso!")
        return True
    return False


def editar_modalidade(conn, id_modalidade, novo_nome):
    """
    Edita o nome de uma modalidade
    
    Args:
        conn: Conexão com Databricks
        id_modalidade: ID da modalidade
        novo_nome: Novo nome da modalidade
        
    Returns:
        True se sucesso, False se erro
    """
    command = f"""
    UPDATE {TABLE_MODALIDADES}
    SET nome_modalidade = '{novo_nome}',
        dt_atualizacao = CURRENT_TIMESTAMP()
    WHERE id_modalidade = {id_modalidade}
    """
    
    if execute_command(conn, command):
        st.success(f"✅ Modalidade atualizada com sucesso!")
        return True
    return False


def alternar_status_modalidade(conn, id_modalidade, ativo):
    """
    Ativa ou desativa uma modalidade
    
    Args:
        conn: Conexão com Databricks
        id_modalidade: ID da modalidade
        ativo: True para ativar, False para desativar
        
    Returns:
        True se sucesso, False se erro
    """
    command = f"""
    UPDATE {TABLE_MODALIDADES}
    SET ativo = {str(ativo).upper()},
        dt_atualizacao = CURRENT_TIMESTAMP()
    WHERE id_modalidade = {id_modalidade}
    """
    
    if execute_command(conn, command):
        status = "ativada" if ativo else "desativada"
        st.success(f"✅ Modalidade {status} com sucesso!")
        return True
    return False


def renderizar_pagina_modalidades(conn):
    """
    Renderiza a página de gerenciamento de modalidades
    
    Args:
        conn: Conexão com Databricks
    """
    st.subheader("🏷️ Gerenciamento de Modalidades")
    
    # Tabs para organizar funcionalidades
    tab_listar, tab_adicionar = st.tabs(["📋 Listar", "➕ Adicionar"])
    
    # ===== TAB: LISTAR =====
    with tab_listar:
        st.markdown("### Modalidades Cadastradas")
        
        # Filtro ativo/inativo
        col1, col2 = st.columns([3, 1])
        with col1:
            mostrar_inativos = st.checkbox("Mostrar modalidades inativas", value=False)
        with col2:
            if st.button("🔄 Atualizar", key="refresh_modalidades"):
                st.rerun()
        
        # Carregar modalidades
        df_modalidades = listar_modalidades(conn, apenas_ativas=not mostrar_inativos)
        
        if len(df_modalidades) == 0:
            st.info("ℹ️ Nenhuma modalidade cadastrada ainda.")
        else:
            st.markdown(f"**Total:** {len(df_modalidades)} modalidade(s)")
            
            # Exibir tabela com ações
            for idx, row in df_modalidades.iterrows():
                col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                
                with col1:
                    status_icon = "✅" if row['ativo'] else "❌"
                    st.markdown(f"{status_icon} **{row['nome_modalidade']}**")
                    st.caption(f"ID: {row['id_modalidade']} | Cadastro: {row['dt_cadastro']}")
                
                with col2:
                    # Botão Editar
                    if st.button("✏️", key=f"edit_{row['id_modalidade']}", help="Editar"):
                        st.session_state[f"editing_{row['id_modalidade']}"] = True
                        st.rerun()
                
                with col3:
                    # Botão Ativar/Desativar
                    if row['ativo']:
                        if st.button("🚫", key=f"deactivate_{row['id_modalidade']}", help="Desativar"):
                            alternar_status_modalidade(conn, row['id_modalidade'], False)
                            st.rerun()
                    else:
                        if st.button("✅", key=f"activate_{row['id_modalidade']}", help="Ativar"):
                            alternar_status_modalidade(conn, row['id_modalidade'], True)
                            st.rerun()
                
                with col4:
                    # Verificar se está em modo de edição
                    if st.session_state.get(f"editing_{row['id_modalidade']}", False):
                        st.markdown("✏️")
                
                # Formulário de edição (se ativado)
                if st.session_state.get(f"editing_{row['id_modalidade']}", False):
                    with st.form(key=f"form_edit_{row['id_modalidade']}"):
                        novo_nome = st.text_input(
                            "Novo nome:",
                            value=row['nome_modalidade'],
                            key=f"input_edit_{row['id_modalidade']}"
                        )
                        
                        col_save, col_cancel = st.columns(2)
                        with col_save:
                            if st.form_submit_button("💾 Salvar"):
                                if novo_nome.strip():
                                    if editar_modalidade(conn, row['id_modalidade'], novo_nome.strip()):
                                        st.session_state[f"editing_{row['id_modalidade']}"] = False
                                        st.rerun()
                                else:
                                    st.error("Nome não pode ser vazio")
                        
                        with col_cancel:
                            if st.form_submit_button("❌ Cancelar"):
                                st.session_state[f"editing_{row['id_modalidade']}"] = False
                                st.rerun()
                
                st.markdown("---")
    
    # ===== TAB: ADICIONAR =====
    with tab_adicionar:
        st.markdown("### Adicionar Nova Modalidade")
        
        with st.form("form_adicionar_modalidade"):
            nome_modalidade = st.text_input(
                "Nome da Modalidade:",
                placeholder="Ex: TC, ANGIOTC, RM, RX",
                help="Nome da modalidade radiológica"
            )
            
            st.markdown("**Exemplos:** TC, ANGIOTC, RM, RX, US, MAMOGRAFIA")
            
            submitted = st.form_submit_button("➕ Adicionar Modalidade")
            
            if submitted:
                if nome_modalidade.strip():
                    if adicionar_modalidade(conn, nome_modalidade.strip().upper()):
                        st.rerun()
                else:
                    st.error("❌ Nome da modalidade não pode ser vazio")

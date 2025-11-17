"""
Módulo de gerenciamento de Descrições
"""

import streamlit as st
import pandas as pd
from config import TABLE_DESCRICOES
from database import execute_query, execute_command


def listar_descricoes(conn, apenas_ativas=True):
    """
    Lista todas as descrições
    
    Args:
        conn: Conexão com Databricks
        apenas_ativas: Se True, retorna apenas descrições ativas
        
    Returns:
        DataFrame com as descrições
    """
    filtro = "WHERE ativo = TRUE" if apenas_ativas else ""
    query = f"""
    SELECT 
        id_descricao,
        descricao,
        ativo,
        dt_cadastro,
        dt_atualizacao
    FROM {TABLE_DESCRICOES}
    {filtro}
    ORDER BY descricao
    """
    return execute_query(conn, query)


def adicionar_descricao(conn, descricao):
    """
    Adiciona uma nova descrição
    
    Args:
        conn: Conexão com Databricks
        descricao: Texto da descrição
        
    Returns:
        True se sucesso, False se erro
    """
    # Verificar se já existe
    query_check = f"""
    SELECT COUNT(*) as total 
    FROM {TABLE_DESCRICOES} 
    WHERE UPPER(descricao) = UPPER('{descricao}')
    """
    df_check = execute_query(conn, query_check)
    
    if len(df_check) > 0 and df_check['total'].iloc[0] > 0:
        st.error(f"❌ Descrição '{descricao}' já existe!")
        return False
    
    # Inserir
    command = f"""
    INSERT INTO {TABLE_DESCRICOES} (descricao, ativo, dt_cadastro, dt_atualizacao)
    VALUES ('{descricao}', TRUE, CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP())
    """
    
    if execute_command(conn, command):
        st.success(f"✅ Descrição '{descricao}' adicionada com sucesso!")
        return True
    return False


def editar_descricao(conn, id_descricao, nova_descricao):
    """
    Edita o texto de uma descrição
    
    Args:
        conn: Conexão com Databricks
        id_descricao: ID da descrição
        nova_descricao: Novo texto da descrição
        
    Returns:
        True se sucesso, False se erro
    """
    command = f"""
    UPDATE {TABLE_DESCRICOES}
    SET descricao = '{nova_descricao}',
        dt_atualizacao = CURRENT_TIMESTAMP()
    WHERE id_descricao = {id_descricao}
    """
    
    if execute_command(conn, command):
        st.success(f"✅ Descrição atualizada com sucesso!")
        return True
    return False


def alternar_status_descricao(conn, id_descricao, ativo):
    """
    Ativa ou desativa uma descrição
    
    Args:
        conn: Conexão com Databricks
        id_descricao: ID da descrição
        ativo: True para ativar, False para desativar
        
    Returns:
        True se sucesso, False se erro
    """
    command = f"""
    UPDATE {TABLE_DESCRICOES}
    SET ativo = {str(ativo).upper()},
        dt_atualizacao = CURRENT_TIMESTAMP()
    WHERE id_descricao = {id_descricao}
    """
    
    if execute_command(conn, command):
        status = "ativada" if ativo else "desativada"
        st.success(f"✅ Descrição {status} com sucesso!")
        return True
    return False


def renderizar_pagina_descricoes(conn):
    """
    Renderiza a página de gerenciamento de descrições
    
    Args:
        conn: Conexão com Databricks
    """
    st.subheader("📝 Gerenciamento de Descrições")
    
    # Tabs para organizar funcionalidades
    tab_listar, tab_adicionar = st.tabs(["📋 Listar", "➕ Adicionar"])
    
    # ===== TAB: LISTAR =====
    with tab_listar:
        st.markdown("### Descrições Cadastradas")
        
        # Filtros e controles
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            mostrar_inativos = st.checkbox("Mostrar descrições inativas", value=False)
        with col2:
            busca = st.text_input("🔍 Buscar descrição:", placeholder="Digite para filtrar...", key="busca_descricao")
        with col3:
            if st.button("🔄 Atualizar", key="refresh_descricoes"):
                st.rerun()
        
        # Carregar descrições
        df_descricoes = listar_descricoes(conn, apenas_ativas=not mostrar_inativos)
        
        # Aplicar filtro de busca
        if busca:
            df_descricoes = df_descricoes[
                df_descricoes['descricao'].str.contains(busca, case=False, na=False)
            ]
        
        if len(df_descricoes) == 0:
            st.info("ℹ️ Nenhuma descrição encontrada.")
        else:
            st.markdown(f"**Total:** {len(df_descricoes)} descrição(ões)")
            
            # Exibir tabela com ações
            for idx, row in df_descricoes.iterrows():
                col1, col2, col3, col4 = st.columns([4, 1, 1, 1])
                
                with col1:
                    status_icon = "✅" if row['ativo'] else "❌"
                    st.markdown(f"{status_icon} **{row['descricao']}**")
                    st.caption(f"ID: {row['id_descricao']} | Cadastro: {row['dt_cadastro']}")
                
                with col2:
                    # Botão Editar
                    if st.button("✏️", key=f"edit_desc_{row['id_descricao']}", help="Editar"):
                        st.session_state[f"editing_desc_{row['id_descricao']}"] = True
                        st.rerun()
                
                with col3:
                    # Botão Ativar/Desativar
                    if row['ativo']:
                        if st.button("🚫", key=f"deactivate_desc_{row['id_descricao']}", help="Desativar"):
                            alternar_status_descricao(conn, row['id_descricao'], False)
                            st.rerun()
                    else:
                        if st.button("✅", key=f"activate_desc_{row['id_descricao']}", help="Ativar"):
                            alternar_status_descricao(conn, row['id_descricao'], True)
                            st.rerun()
                
                with col4:
                    # Verificar se está em modo de edição
                    if st.session_state.get(f"editing_desc_{row['id_descricao']}", False):
                        st.markdown("✏️")
                
                # Formulário de edição (se ativado)
                if st.session_state.get(f"editing_desc_{row['id_descricao']}", False):
                    with st.form(key=f"form_edit_desc_{row['id_descricao']}"):
                        nova_descricao = st.text_area(
                            "Nova descrição:",
                            value=row['descricao'],
                            key=f"input_edit_desc_{row['id_descricao']}",
                            height=100
                        )
                        
                        col_save, col_cancel = st.columns(2)
                        with col_save:
                            if st.form_submit_button("💾 Salvar"):
                                if nova_descricao.strip():
                                    if editar_descricao(conn, row['id_descricao'], nova_descricao.strip()):
                                        st.session_state[f"editing_desc_{row['id_descricao']}"] = False
                                        st.rerun()
                                else:
                                    st.error("Descrição não pode ser vazia")
                        
                        with col_cancel:
                            if st.form_submit_button("❌ Cancelar"):
                                st.session_state[f"editing_desc_{row['id_descricao']}"] = False
                                st.rerun()
                
                st.markdown("---")
    
    # ===== TAB: ADICIONAR =====
    with tab_adicionar:
        st.markdown("### Adicionar Nova Descrição")
        
        with st.form("form_adicionar_descricao"):
            descricao = st.text_area(
                "Descrição:",
                placeholder="Ex: ABDOME, TÓRAX, CRÂNIO, COM CONTRASTE, SEM CONTRASTE",
                help="Descrição anatômica ou técnica do procedimento",
                height=100
            )
            
            st.markdown("""
            **Exemplos de descrições:**
            - Anatômicas: ABDOME, TÓRAX, CRÂNIO, COLUNA, PELVE
            - Técnicas: COM CONTRASTE, SEM CONTRASTE, ALTA RESOLUÇÃO
            - Especificações: SUPERIOR, INFERIOR, TOTAL, PARCIAL
            """)
            
            submitted = st.form_submit_button("➕ Adicionar Descrição")
            
            if submitted:
                if descricao.strip():
                    if adicionar_descricao(conn, descricao.strip().upper()):
                        st.rerun()
                else:
                    st.error("❌ Descrição não pode ser vazia")

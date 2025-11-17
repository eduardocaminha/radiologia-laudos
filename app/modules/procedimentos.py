"""
Módulo de gerenciamento de Procedimentos
"""

import streamlit as st
import pandas as pd
from config import TABLE_PROCEDIMENTOS, TABLE_MODALIDADES, TABLE_DESCRICOES
from database import execute_query, execute_command, buscar_procedimento_oracle


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
    
    # Tabs para organizar funcionalidades
    tab_listar, tab_manual, tab_busca_codigo, tab_busca_termo = st.tabs([
        "📋 Listar",
        "✍️ Manual",
        "🔍 Buscar por Código",
        "🔎 Buscar por Termo"
    ])
    
    # ===== TAB: LISTAR =====
    with tab_listar:
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
    
    # ===== TAB: MANUAL =====
    with tab_manual:
        st.markdown("### Adicionar Procedimento Manualmente")
        
        with st.form("form_procedimento_manual"):
            col1, col2 = st.columns(2)
            
            with col1:
                cd_procedimento = st.number_input(
                    "Código do Procedimento:",
                    min_value=1,
                    step=1,
                    help="CD_PROCEDIMENTO"
                )
            
            with col2:
                df_modalidades = obter_modalidades_ativas(conn)
                if len(df_modalidades) == 0:
                    st.error("❌ Nenhuma modalidade cadastrada. Cadastre modalidades primeiro.")
                    st.stop()
                
                modalidade_selecionada = st.selectbox(
                    "Modalidade:",
                    options=df_modalidades['nome_modalidade'].tolist()
                )
            
            nm_procedimento = st.text_input(
                "Nome do Procedimento:",
                placeholder="Ex: TOMOGRAFIA COMPUTADORIZADA DE ABDOME"
            )
            
            # Multiselect para descrições
            df_descricoes = obter_descricoes_ativas(conn)
            if len(df_descricoes) == 0:
                st.warning("⚠️ Nenhuma descrição cadastrada. Cadastre descrições primeiro.")
            else:
                descricoes_selecionadas = st.multiselect(
                    "Descrições (selecione até 7):",
                    options=df_descricoes['descricao'].tolist(),
                    max_selections=7,
                    help="Selecione as descrições que se aplicam a este procedimento"
                )
            
            submitted = st.form_submit_button("➕ Adicionar Procedimento")
            
            if submitted:
                if cd_procedimento and nm_procedimento.strip():
                    id_modalidade = df_modalidades[
                        df_modalidades['nome_modalidade'] == modalidade_selecionada
                    ]['id_modalidade'].iloc[0]
                    
                    # Converter descrições selecionadas para IDs
                    ids_descricoes = []
                    if len(df_descricoes) > 0 and 'descricoes_selecionadas' in locals():
                        for desc in descricoes_selecionadas:
                            id_desc = df_descricoes[df_descricoes['descricao'] == desc]['id_descricao'].iloc[0]
                            ids_descricoes.append(id_desc)
                    
                    if adicionar_procedimento(conn, cd_procedimento, nm_procedimento.strip(), id_modalidade, ids_descricoes):
                        st.rerun()
                else:
                    st.error("❌ Código e Nome do procedimento são obrigatórios")
    
    # ===== TAB: BUSCA POR CÓDIGO =====
    with tab_busca_codigo:
        st.markdown("### Buscar Procedimento por Código no Oracle Lake")
        
        cd_busca = st.number_input(
            "Digite o código do procedimento:",
            min_value=1,
            step=1,
            key="cd_busca_oracle"
        )
        
        if st.button("🔍 Buscar no Oracle", key="btn_buscar_codigo"):
            with st.spinner("Buscando no Oracle Lake..."):
                df_resultado = buscar_procedimento_oracle(cd_procedimento=cd_busca)
            
            if len(df_resultado) == 0:
                st.warning(f"⚠️ Procedimento {cd_busca} não encontrado no Oracle Lake")
            else:
                st.success(f"✅ Procedimento encontrado!")
                
                proc = df_resultado.iloc[0]
                st.markdown(f"**Código:** {proc['CD_PROCEDIMENTO']}")
                st.markdown(f"**Nome:** {proc['NM_PROCEDIMENTO']}")
                
                # Formulário para adicionar
                with st.form("form_adicionar_oracle_codigo"):
                    df_modalidades = obter_modalidades_ativas(conn)
                    modalidade_selecionada = st.selectbox(
                        "Selecione a Modalidade:",
                        options=df_modalidades['nome_modalidade'].tolist()
                    )
                    
                    # Multiselect para descrições
                    df_descricoes = obter_descricoes_ativas(conn)
                    descricoes_selecionadas = []
                    if len(df_descricoes) > 0:
                        descricoes_selecionadas = st.multiselect(
                            "Descrições (selecione até 7):",
                            options=df_descricoes['descricao'].tolist(),
                            max_selections=7,
                            key="desc_oracle_codigo"
                        )
                    
                    if st.form_submit_button("➕ Adicionar ao Delta Lake"):
                        id_modalidade = df_modalidades[
                            df_modalidades['nome_modalidade'] == modalidade_selecionada
                        ]['id_modalidade'].iloc[0]
                        
                        # Converter descrições para IDs
                        ids_descricoes = []
                        if len(df_descricoes) > 0:
                            for desc in descricoes_selecionadas:
                                id_desc = df_descricoes[df_descricoes['descricao'] == desc]['id_descricao'].iloc[0]
                                ids_descricoes.append(id_desc)
                        
                        if adicionar_procedimento(
                            conn,
                            int(proc['CD_PROCEDIMENTO']),
                            proc['NM_PROCEDIMENTO'],
                            id_modalidade,
                            ids_descricoes
                        ):
                            st.rerun()
    
    # ===== TAB: BUSCA POR TERMO =====
    with tab_busca_termo:
        st.markdown("### Buscar Procedimentos por Termo no Oracle Lake")
        
        termo_busca = st.text_input(
            "Digite o termo de busca:",
            placeholder="Ex: TOMOGRAFIA, ANGIOTC, ABDOME",
            key="termo_busca_oracle"
        )
        
        if st.button("🔎 Buscar no Oracle", key="btn_buscar_termo"):
            if termo_busca.strip():
                with st.spinner("Buscando no Oracle Lake..."):
                    df_resultados = buscar_procedimento_oracle(termo_busca=termo_busca.strip())
                
                if len(df_resultados) == 0:
                    st.warning(f"⚠️ Nenhum procedimento encontrado com o termo '{termo_busca}'")
                else:
                    st.success(f"✅ {len(df_resultados)} procedimento(s) encontrado(s)")
                    st.session_state['resultados_busca_termo'] = df_resultados
            else:
                st.error("❌ Digite um termo para buscar")
        
        # Exibir resultados e permitir seleção
        if 'resultados_busca_termo' in st.session_state:
            df_resultados = st.session_state['resultados_busca_termo']
            
            st.markdown("---")
            st.markdown("### Selecione os procedimentos para adicionar:")
            
            # Checkboxes para seleção
            selecionados = []
            for idx, row in df_resultados.iterrows():
                if st.checkbox(
                    f"{row['CD_PROCEDIMENTO']} - {row['NM_PROCEDIMENTO']}",
                    key=f"check_proc_{row['CD_PROCEDIMENTO']}"
                ):
                    selecionados.append(row)
            
            if selecionados:
                st.markdown(f"**{len(selecionados)} procedimento(s) selecionado(s)**")
                
                # Formulário para adicionar em lote
                with st.form("form_adicionar_oracle_termo"):
                    df_modalidades = obter_modalidades_ativas(conn)
                    modalidade_selecionada = st.selectbox(
                        "Modalidade para todos os selecionados:",
                        options=df_modalidades['nome_modalidade'].tolist()
                    )
                    
                    # Multiselect para descrições
                    df_descricoes = obter_descricoes_ativas(conn)
                    descricoes_selecionadas = []
                    if len(df_descricoes) > 0:
                        descricoes_selecionadas = st.multiselect(
                            "Descrições (aplicadas a todos, até 7):",
                            options=df_descricoes['descricao'].tolist(),
                            max_selections=7,
                            key="desc_oracle_termo"
                        )
                    
                    if st.form_submit_button("➕ Adicionar Selecionados ao Delta Lake"):
                        id_modalidade = df_modalidades[
                            df_modalidades['nome_modalidade'] == modalidade_selecionada
                        ]['id_modalidade'].iloc[0]
                        
                        # Converter descrições para IDs
                        ids_descricoes = []
                        if len(df_descricoes) > 0:
                            for desc in descricoes_selecionadas:
                                id_desc = df_descricoes[df_descricoes['descricao'] == desc]['id_descricao'].iloc[0]
                                ids_descricoes.append(id_desc)
                        
                        sucesso = 0
                        for proc in selecionados:
                            if adicionar_procedimento(
                                conn,
                                int(proc['CD_PROCEDIMENTO']),
                                proc['NM_PROCEDIMENTO'],
                                id_modalidade,
                                ids_descricoes
                            ):
                                sucesso += 1
                        
                        st.success(f"✅ {sucesso}/{len(selecionados)} procedimento(s) adicionado(s) com sucesso!")
                        del st.session_state['resultados_busca_termo']
                        st.rerun()

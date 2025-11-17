"""
Módulo de importação inicial do CSV
"""

import streamlit as st
import pandas as pd
from pathlib import Path
from config import TABLE_MODALIDADES, TABLE_DESCRICOES, TABLE_PROCEDIMENTOS
from database import execute_query, execute_command


def carregar_csv(file_path=None, uploaded_file=None):
    """
    Carrega o CSV de procedimentos
    
    Args:
        file_path: Caminho do arquivo local
        uploaded_file: Arquivo enviado via upload
        
    Returns:
        DataFrame ou None se erro
    """
    try:
        if uploaded_file is not None:
            df = pd.read_csv(uploaded_file, sep=';', encoding='utf-8')
        elif file_path:
            df = pd.read_csv(file_path, sep=';', encoding='utf-8')
        else:
            return None
        
        # Garantir que as colunas esperadas existem
        expected_cols = ['CD_PROCEDIMENTO', 'NM_PROCEDIMENTO', 'MODALIDADE', 
                        'DESCRICAO_1', 'DESCRICAO_2', 'DESCRICAO_3', 'DESCRICAO_4',
                        'DESCRICAO_5', 'DESCRICAO_6', 'DESCRICAO_7']
        
        for col in expected_cols:
            if col not in df.columns:
                st.error(f"❌ Coluna esperada '{col}' não encontrada no CSV")
                return None
        
        return df
    except Exception as e:
        st.error(f"❌ Erro ao carregar CSV: {str(e)}")
        return None


def extrair_modalidades_unicas(df):
    """Extrai modalidades únicas do CSV"""
    return sorted(df['MODALIDADE'].dropna().unique().tolist())


def extrair_descricoes_unicas(df):
    """Extrai descrições únicas do CSV"""
    descricoes = set()
    for col in ['DESCRICAO_1', 'DESCRICAO_2', 'DESCRICAO_3', 'DESCRICAO_4',
                'DESCRICAO_5', 'DESCRICAO_6', 'DESCRICAO_7']:
        valores = df[col].dropna().unique()
        valores = [v for v in valores if v and str(v).strip() != '']
        descricoes.update(valores)
    
    return sorted(list(descricoes))


def importar_modalidades(conn, modalidades):
    """
    Importa modalidades para a tabela Gold
    
    Args:
        conn: Conexão com Databricks
        modalidades: Lista de modalidades
        
    Returns:
        Tupla (sucesso, erros)
    """
    sucesso = 0
    erros = 0
    
    for modalidade in modalidades:
        # Verificar se já existe
        query_check = f"""
        SELECT COUNT(*) as total 
        FROM {TABLE_MODALIDADES} 
        WHERE UPPER(nome_modalidade) = UPPER('{modalidade}')
        """
        df_check = execute_query(conn, query_check)
        
        if len(df_check) > 0 and df_check['total'].iloc[0] > 0:
            erros += 1
            continue
        
        # Inserir
        command = f"""
        INSERT INTO {TABLE_MODALIDADES} (nome_modalidade, ativo, dt_cadastro, dt_atualizacao)
        VALUES ('{modalidade}', TRUE, CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP())
        """
        
        if execute_command(conn, command):
            sucesso += 1
        else:
            erros += 1
    
    return sucesso, erros


def importar_descricoes(conn, descricoes):
    """
    Importa descrições para a tabela Gold
    
    Args:
        conn: Conexão com Databricks
        descricoes: Lista de descrições
        
    Returns:
        Tupla (sucesso, erros)
    """
    sucesso = 0
    erros = 0
    
    for descricao in descricoes:
        # Verificar se já existe
        query_check = f"""
        SELECT COUNT(*) as total 
        FROM {TABLE_DESCRICOES} 
        WHERE UPPER(descricao) = UPPER('{descricao}')
        """
        df_check = execute_query(conn, query_check)
        
        if len(df_check) > 0 and df_check['total'].iloc[0] > 0:
            erros += 1
            continue
        
        # Inserir
        command = f"""
        INSERT INTO {TABLE_DESCRICOES} (descricao, ativo, dt_cadastro, dt_atualizacao)
        VALUES ('{descricao}', TRUE, CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP())
        """
        
        if execute_command(conn, command):
            sucesso += 1
        else:
            erros += 1
    
    return sucesso, erros


def obter_id_modalidade(conn, nome_modalidade):
    """Obtém o ID de uma modalidade pelo nome"""
    query = f"""
    SELECT id_modalidade 
    FROM {TABLE_MODALIDADES} 
    WHERE UPPER(nome_modalidade) = UPPER('{nome_modalidade}')
    LIMIT 1
    """
    df = execute_query(conn, query)
    if len(df) > 0:
        return df['id_modalidade'].iloc[0]
    return None


def obter_id_descricao(conn, descricao):
    """Obtém o ID de uma descrição pelo texto"""
    query = f"""
    SELECT id_descricao 
    FROM {TABLE_DESCRICOES} 
    WHERE UPPER(descricao) = UPPER('{descricao}')
    LIMIT 1
    """
    df = execute_query(conn, query)
    if len(df) > 0:
        return df['id_descricao'].iloc[0]
    return None


def importar_procedimentos(conn, df, modalidades_selecionadas=None):
    """
    Importa procedimentos para a tabela Gold
    
    Args:
        conn: Conexão com Databricks
        df: DataFrame com os procedimentos
        modalidades_selecionadas: Lista de modalidades para filtrar (None = todas)
        
    Returns:
        Tupla (sucesso, erros, duplicados, detalhes)
    """
    sucesso = 0
    erros = 0
    duplicados = 0
    erros_modalidade = 0
    erros_insercao = 0
    
    # Filtrar por modalidades se especificado
    if modalidades_selecionadas:
        df = df[df['MODALIDADE'].isin(modalidades_selecionadas)]
    
    for idx, row in df.iterrows():
        cd_procedimento = row['CD_PROCEDIMENTO']
        nm_procedimento = row['NM_PROCEDIMENTO']
        modalidade = row['MODALIDADE']
        
        # Verificar se já existe
        query_check = f"""
        SELECT COUNT(*) as total 
        FROM {TABLE_PROCEDIMENTOS} 
        WHERE cd_procedimento = {cd_procedimento}
        """
        df_check = execute_query(conn, query_check)
        
        if len(df_check) > 0 and df_check['total'].iloc[0] > 0:
            duplicados += 1
            continue
        
        # Obter ID da modalidade
        id_modalidade = obter_id_modalidade(conn, modalidade)
        if not id_modalidade:
            erros += 1
            erros_modalidade += 1
            continue
        
        # Preparar IDs de descrições
        desc_values = []
        for i in range(1, 8):
            desc = row[f'DESCRICAO_{i}']
            if pd.notna(desc) and str(desc).strip():
                # Buscar ID da descrição
                id_desc = obter_id_descricao(conn, str(desc).strip())
                if id_desc:
                    desc_values.append(str(id_desc))
                else:
                    desc_values.append("NULL")
            else:
                desc_values.append("NULL")
        
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
            sucesso += 1
        else:
            erros += 1
            erros_insercao += 1
    
    detalhes = {
        'erros_modalidade': erros_modalidade,
        'erros_insercao': erros_insercao
    }
    
    return sucesso, erros, duplicados, detalhes


def renderizar_pagina_importar_csv(conn):
    """
    Renderiza a página de importação do CSV
    
    Args:
        conn: Conexão com Databricks
    """
    st.subheader("📊 Importação Inicial do CSV")
    
    st.markdown("""
    Esta página permite importar dados do arquivo `procedimentos.csv` para popular as tabelas Gold.
    
    **Processo de importação:**
    1. Carregar o arquivo CSV
    2. Importar modalidades únicas
    3. Importar descrições únicas
    4. Importar procedimentos (vinculando modalidades e descrições)
    """)
    
    # ===== ESTATÍSTICAS ATUAIS =====
    st.markdown("---")
    st.markdown("### 📈 Dados Atuais no Banco")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        query_mod = f"SELECT COUNT(*) as total FROM {TABLE_MODALIDADES}"
        df_mod = execute_query(conn, query_mod)
        total_mod = df_mod['total'].iloc[0] if len(df_mod) > 0 else 0
        st.metric("🏷️ Modalidades", total_mod)
    
    with col2:
        query_desc = f"SELECT COUNT(*) as total FROM {TABLE_DESCRICOES}"
        df_desc = execute_query(conn, query_desc)
        total_desc = df_desc['total'].iloc[0] if len(df_desc) > 0 else 0
        st.metric("📝 Descrições", total_desc)
    
    with col3:
        query_proc = f"SELECT COUNT(*) as total FROM {TABLE_PROCEDIMENTOS}"
        df_proc = execute_query(conn, query_proc)
        total_proc = df_proc['total'].iloc[0] if len(df_proc) > 0 else 0
        st.metric("🔬 Procedimentos", total_proc)
    
    # Mostrar procedimentos com nomes duplicados
    if total_proc > 0:
        with st.expander("🔍 Ver procedimentos com nomes repetidos (códigos diferentes)"):
            query_duplicados = f"""
            SELECT nm_procedimento, COUNT(*) as qtd, 
                   COLLECT_LIST(cd_procedimento) as codigos
            FROM {TABLE_PROCEDIMENTOS}
            GROUP BY nm_procedimento
            HAVING COUNT(*) > 1
            ORDER BY qtd DESC
            """
            df_dup = execute_query(conn, query_duplicados)
            
            if len(df_dup) > 0:
                st.info(f"📊 {len(df_dup)} nomes de procedimentos aparecem com códigos diferentes")
                st.dataframe(df_dup, use_container_width=True)
            else:
                st.success("✅ Não há nomes de procedimentos duplicados")
    
    st.markdown("---")
    
    # ===== CARREGAR CSV =====
    st.markdown("### 1️⃣ Carregar CSV")
    
    # Tentar carregar arquivo padrão
    default_path = Path(__file__).parent.parent.parent / "procedimentos.csv"
    default_path_str = str(default_path.absolute())
    
    col1, col2 = st.columns(2)
    
    with col1:
        usar_padrao = st.checkbox(
            "Usar arquivo padrão",
            value=default_path.exists(),
            help=f"Caminho: {default_path_str}"
        )
    
    with col2:
        uploaded_file = None
        if not usar_padrao:
            uploaded_file = st.file_uploader(
                "Upload do CSV:",
                type=['csv'],
                help="Arquivo CSV delimitado por ';'"
            )
    
    # Carregar dados
    df = None
    if usar_padrao and default_path.exists():
        df = carregar_csv(file_path=default_path_str)
        if df is not None:
            st.success(f"✅ Arquivo padrão carregado ({len(df)} registros)")
    elif uploaded_file is not None:
        df = carregar_csv(uploaded_file=uploaded_file)
        if df is not None:
            st.success(f"✅ Arquivo carregado ({len(df)} registros)")
    
    if df is None:
        st.info("👆 Carregue um arquivo CSV para continuar")
        st.stop()
    
    # ===== ANÁLISE DO CSV =====
    st.markdown("---")
    st.markdown("### 📋 Análise do CSV")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total de Registros", len(df))
    
    with col2:
        modalidades_unicas = extrair_modalidades_unicas(df)
        st.metric("Modalidades Únicas", len(modalidades_unicas))
    
    with col3:
        descricoes_unicas = extrair_descricoes_unicas(df)
        st.metric("Descrições Únicas", len(descricoes_unicas))
    
    # Análise de duplicados no CSV
    st.markdown("---")
    duplicados_csv = df[df.duplicated(subset=['CD_PROCEDIMENTO'], keep=False)]
    if len(duplicados_csv) > 0:
        codigos_duplicados = duplicados_csv['CD_PROCEDIMENTO'].unique()
        st.warning(f"⚠️ **ATENÇÃO: {len(codigos_duplicados)} códigos aparecem duplicados no CSV!**")
        st.error(f"🔴 Total de {len(duplicados_csv)} linhas duplicadas (apenas a primeira será importada)")
        
        with st.expander("🔍 Ver códigos duplicados no CSV"):
            df_dup_analise = duplicados_csv.groupby('CD_PROCEDIMENTO').agg({
                'NM_PROCEDIMENTO': 'first',
                'MODALIDADE': 'first',
                'CD_PROCEDIMENTO': 'count'
            }).rename(columns={'CD_PROCEDIMENTO': 'QUANTIDADE'})
            df_dup_analise = df_dup_analise.sort_values('QUANTIDADE', ascending=False)
            st.dataframe(df_dup_analise, use_container_width=True)
            
            st.info("""
            **Ação recomendada:** Limpe o CSV removendo as linhas duplicadas.  
            O sistema só importa a primeira ocorrência de cada código.
            """)
    else:
        st.success("✅ Nenhum código duplicado no CSV")
    
    # Preview dos dados
    with st.expander("👁️ Visualizar dados do CSV"):
        st.dataframe(df.head(20), use_container_width=True)
    
    # ===== IMPORTAR MODALIDADES =====
    st.markdown("---")
    st.markdown("### 2️⃣ Importar Modalidades")
    
    st.markdown(f"**Modalidades encontradas:** {', '.join(modalidades_unicas)}")
    
    if st.button("➕ Importar Modalidades", key="btn_importar_modalidades"):
        with st.spinner("Importando modalidades..."):
            sucesso, erros = importar_modalidades(conn, modalidades_unicas)
        
        if sucesso > 0:
            st.success(f"✅ {sucesso} modalidade(s) importada(s) com sucesso!")
        if erros > 0:
            st.warning(f"⚠️ {erros} modalidade(s) já existiam ou tiveram erro")
    
    # ===== IMPORTAR DESCRIÇÕES =====
    st.markdown("---")
    st.markdown("### 3️⃣ Importar Descrições")
    
    with st.expander(f"📝 Ver {len(descricoes_unicas)} descrições"):
        for desc in descricoes_unicas:
            st.markdown(f"- {desc}")
    
    if st.button("➕ Importar Descrições", key="btn_importar_descricoes"):
        with st.spinner("Importando descrições..."):
            sucesso, erros = importar_descricoes(conn, descricoes_unicas)
        
        if sucesso > 0:
            st.success(f"✅ {sucesso} descrição(ões) importada(s) com sucesso!")
        if erros > 0:
            st.warning(f"⚠️ {erros} descrição(ões) já existiam ou tiveram erro")
    
    # ===== IMPORTAR PROCEDIMENTOS =====
    st.markdown("---")
    st.markdown("### 4️⃣ Importar Procedimentos")
    
    st.markdown("**Filtrar por modalidades (opcional):**")
    modalidades_importar = st.multiselect(
        "Selecione as modalidades para importar:",
        options=modalidades_unicas,
        default=modalidades_unicas,
        key="modalidades_importar"
    )
    
    if modalidades_importar:
        df_filtrado = df[df['MODALIDADE'].isin(modalidades_importar)]
        st.info(f"📊 {len(df_filtrado)} procedimento(s) serão importados")
        
        if st.button("➕ Importar Procedimentos", key="btn_importar_procedimentos"):
            with st.spinner("Importando procedimentos..."):
                sucesso, erros, duplicados, detalhes = importar_procedimentos(conn, df, modalidades_importar)
            
            st.markdown("**Resultado da importação:**")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("✅ Importados", sucesso)
            with col2:
                st.metric("❌ Erros", erros)
                if erros > 0:
                    st.caption(f"Modalidade não encontrada: {detalhes['erros_modalidade']}")
                    st.caption(f"Erro na inserção: {detalhes['erros_insercao']}")
            with col3:
                st.metric("⚠️ Duplicados", duplicados)
            
            if sucesso > 0:
                st.success(f"✅ Importação concluída! {sucesso} procedimento(s) adicionado(s).")
    else:
        st.warning("⚠️ Selecione pelo menos uma modalidade para importar")
    
    # ===== IMPORTAÇÃO COMPLETA =====
    st.markdown("---")
    st.markdown("### 🚀 Importação Completa")
    
    st.warning("""
    **⚠️ Atenção:** Esta opção importa TUDO de uma vez:
    - Todas as modalidades
    - Todas as descrições
    - Todos os procedimentos
    
    Use apenas se as tabelas estiverem vazias ou se souber o que está fazendo.
    """)
    
    if st.button("🚀 Importar Tudo", key="btn_importar_tudo", type="primary"):
        with st.spinner("Importando tudo..."):
            # Modalidades
            st.info("Importando modalidades...")
            suc_mod, err_mod = importar_modalidades(conn, modalidades_unicas)
            
            # Descrições
            st.info("Importando descrições...")
            suc_desc, err_desc = importar_descricoes(conn, descricoes_unicas)
            
            # Procedimentos
            st.info("Importando procedimentos...")
            suc_proc, err_proc, dup_proc, det_proc = importar_procedimentos(conn, df)
        
        st.markdown("### 📊 Resultado Final")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("**Modalidades:**")
            st.metric("Importadas", suc_mod)
            st.metric("Erros/Duplicadas", err_mod)
        
        with col2:
            st.markdown("**Descrições:**")
            st.metric("Importadas", suc_desc)
            st.metric("Erros/Duplicadas", err_desc)
        
        with col3:
            st.markdown("**Procedimentos:**")
            st.metric("Importados", suc_proc)
            st.metric("Erros", err_proc)
            if err_proc > 0:
                st.caption(f"Modalidade não encontrada: {det_proc['erros_modalidade']}")
                st.caption(f"Erro na inserção: {det_proc['erros_insercao']}")
            st.metric("Duplicados", dup_proc)
            
        # Mostrar resumo detalhado
        st.markdown("---")
        st.markdown("### 📋 Resumo da Importação")
        total_csv = len(df)
        total_importado = suc_proc
        total_nao_importado = err_proc + dup_proc
        
        st.info(f"""
        **CSV:** {total_csv} procedimentos  
        **Importados:** {total_importado}  
        **Não importados:** {total_nao_importado}
        - Duplicados (já existiam): {dup_proc}
        - Erros de modalidade: {det_proc['erros_modalidade']}
        - Erros de inserção: {det_proc['erros_insercao']}
        """)
        
        st.success("✅ Importação completa finalizada!")

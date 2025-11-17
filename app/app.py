"""
Radiologia - Organização de Laudos
Aplicação Streamlit para gerenciar procedimentos radiológicos no Delta Lake
"""

import streamlit as st
import os

# Imports dos módulos locais
from config import TABLE_MODALIDADES, TABLE_DESCRICOES, TABLE_PROCEDIMENTOS
from database import (
    get_databricks_connection,
    criar_tabelas_gold,
    verificar_tabelas_existem,
    execute_query
)
from modules import (
    renderizar_pagina_modalidades,
    renderizar_pagina_descricoes,
    renderizar_pagina_procedimentos,
    renderizar_pagina_importar_csv
)

# Configurar página
st.set_page_config(
    page_title="Radiologia - Organização de Laudos",
    page_icon="📋",
    layout="wide"
)

# Aplicar CSS customizado para fontes e correções visuais
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Oxygen:wght@300;400;700&display=swap');
    
    @font-face {
        font-family: 'Pitanga';
        src: url('./assets/Pitanga-Regular.ttf') format('truetype');
    }
    
    /* Fonte para títulos (h1, h2, h3) */
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Pitanga', sans-serif !important;
    }
    
    /* Fonte para corpo do texto */
    html, body, [class*="css"], p, div, span, label {
        font-family: 'Oxygen', sans-serif !important;
    }
    
    /* Manter fonte monospace para código */
    code, pre {
        font-family: 'Courier New', monospace !important;
    }
    
    /* Corrigir sobreposição de texto nos selectbox */
    [data-baseweb="select"] {
        margin-top: 0.5rem;
    }
    
    /* Garantir espaçamento adequado nos labels */
    .stSelectbox > label {
        margin-bottom: 0.5rem;
        display: block;
    }
    
    /* Ajustar altura dos selectbox */
    [data-baseweb="select"] > div {
        min-height: 2.5rem;
    }
</style>
""", unsafe_allow_html=True)

# =====================================================================
# INTERFACE PRINCIPAL
# =====================================================================

st.title("📋 Radiologia - Organização de Laudos")
st.markdown("---")

# Obter HTTP Path do SQL Warehouse (configurado no app.yaml)
http_path = os.getenv("DATABRICKS_HTTP_PATH")

# Conectar ao SQL Warehouse
try:
    conn = get_databricks_connection(http_path)
    st.sidebar.success("✅ Conectado ao Databricks")
except Exception as e:
    st.error(f"❌ Erro ao conectar ao SQL Warehouse: {str(e)}")
    st.error("Verifique se DATABRICKS_HTTP_PATH está configurado no app.yaml")
    
    if 'connection_error' in st.session_state:
        error_details = st.session_state.connection_error
        with st.expander("🔍 Detalhes do Erro"):
            st.json(error_details)
    
    st.stop()

# Verificar e criar tabelas Gold se necessário
with st.spinner("Verificando tabelas Gold..."):
    if not verificar_tabelas_existem(conn):
        st.info("🔨 Criando tabelas Gold no Delta Lake...")
        if criar_tabelas_gold(conn):
            st.success("✅ Tabelas criadas com sucesso!")
        else:
            st.error("❌ Erro ao criar tabelas")
            st.stop()
    else:
        st.sidebar.info("✅ Tabelas Gold prontas")

# =====================================================================
# NAVEGAÇÃO
# =====================================================================

st.sidebar.markdown("---")
st.sidebar.header("� Navegação")

pagina = st.sidebar.radio(
    "Selecione a página:",
    ["🏠 Início", "🏷️ Modalidades", "📝 Descrições", "🔬 Procedimentos", "📊 Importar CSV"],
    key="navegacao"
)

# =====================================================================
# PÁGINAS
# =====================================================================

if pagina == "🏠 Início":
    st.markdown("""
    ## Bem-vindo ao Sistema de Organização de Laudos
    
    Este aplicativo permite gerenciar procedimentos radiológicos no Delta Lake (camada Gold).
    
    ### Funcionalidades:
    
    - **🏷️ Modalidades**: Gerenciar catálogo de modalidades (TC, ANGIOTC, RM, etc.)
    - **📝 Descrições**: Gerenciar catálogo de descrições anatômicas/técnicas
    - **🔬 Procedimentos**: Adicionar procedimentos vinculando modalidade e descrições
      - Entrada manual
      - Busca por código no Oracle Lake
      - Busca por termo no Oracle Lake
    - **📊 Importar CSV**: Carga inicial a partir do arquivo procedimentos.csv
    
    ### Tabelas Gold:
    - `{TABLE_MODALIDADES}`
    - `{TABLE_DESCRICOES}`
    - `{TABLE_PROCEDIMENTOS}`
    
    👈 Use o menu lateral para navegar entre as páginas.
    """)
    
    # Estatísticas rápidas
    st.markdown("---")
    st.subheader("📊 Estatísticas Rápidas")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        query_modalidades = f"SELECT COUNT(*) as total FROM {TABLE_MODALIDADES} WHERE ativo = TRUE"
        df_modal = execute_query(conn, query_modalidades)
        total_modalidades = df_modal['total'].iloc[0] if len(df_modal) > 0 else 0
        st.metric("Modalidades Ativas", total_modalidades)
    
    with col2:
        query_descricoes = f"SELECT COUNT(*) as total FROM {TABLE_DESCRICOES} WHERE ativo = TRUE"
        df_desc = execute_query(conn, query_descricoes)
        total_descricoes = df_desc['total'].iloc[0] if len(df_desc) > 0 else 0
        st.metric("Descrições Ativas", total_descricoes)
    
    with col3:
        query_procedimentos = f"SELECT COUNT(*) as total FROM {TABLE_PROCEDIMENTOS} WHERE ativo = TRUE"
        df_proc = execute_query(conn, query_procedimentos)
        total_procedimentos = df_proc['total'].iloc[0] if len(df_proc) > 0 else 0
        st.metric("Procedimentos Ativos", total_procedimentos)

elif pagina == "🏷️ Modalidades":
    renderizar_pagina_modalidades(conn)

elif pagina == "📝 Descrições":
    renderizar_pagina_descricoes(conn)

elif pagina == "🔬 Procedimentos":
    renderizar_pagina_procedimentos(conn)

elif pagina == "📊 Importar CSV":
    renderizar_pagina_importar_csv(conn)

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
    deletar_tabelas_gold,
    execute_query
)
from modules import (
    renderizar_dashboard,
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

# CSS desabilitado temporariamente para testes
# st.markdown("""
# <style>
# </style>
# """, unsafe_allow_html=True)

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

# Botão de reset (apenas para admin/desenvolvimento)
st.sidebar.markdown("---")
with st.sidebar.expander("⚙️ Configurações Avançadas", expanded=False):
    st.warning("⚠️ **CUIDADO**: Esta ação deleta TODAS as tabelas e dados!")
    confirmar_reset = st.text_input(
        "Digite 'DELETAR' para confirmar:",
        key="confirmar_reset"
    )
    if st.button("🗑️ Deletar Tabelas Gold", type="secondary"):
        if confirmar_reset == "DELETAR":
            if deletar_tabelas_gold(conn):
                st.success("✅ Tabelas deletadas! Recarregue a página para recriar.")
                st.balloons()
        else:
            st.error("❌ Confirmação incorreta. Digite 'DELETAR' para confirmar.")

# =====================================================================
# NAVEGAÇÃO
# =====================================================================

st.sidebar.markdown("---")
st.sidebar.header("Navegação")

pagina = st.sidebar.radio(
    "Selecione a página:",
    ["📊 Dashboard", "🏷️ Modalidades", "📝 Descrições", "🔬 Procedimentos", "📥 Importar CSV"],
    key="navegacao"
)

# =====================================================================
# PÁGINAS
# =====================================================================

if pagina == "📊 Dashboard":
    renderizar_dashboard(conn)

elif pagina == "🏷️ Modalidades":
    renderizar_pagina_modalidades(conn)

elif pagina == "📝 Descrições":
    renderizar_pagina_descricoes(conn)

elif pagina == "🔬 Procedimentos":
    renderizar_pagina_procedimentos(conn)

elif pagina == "📥 Importar CSV":
    renderizar_pagina_importar_csv(conn)

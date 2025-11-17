"""
Script de inicialização para rodar o app no Databricks

Este script deve ser executado ANTES de iniciar o Streamlit no Databricks:
1. Conecta ao Oracle Lake usando a biblioteca Lake
2. Disponibiliza a função run_sql globalmente
3. Configura o ambiente para o Streamlit

Uso no Databricks:
%run /Workspace/Libraries/Lake
%run /path/to/init_databricks.py
"""

import os
import sys

# Verificar se estamos no Databricks
if not os.path.exists('/Workspace'):
    print("⚠️ Este script deve ser executado apenas no Databricks")
    sys.exit(1)

# Conectar ao Oracle Lake
try:
    # A função connect_to_datalake é fornecida pela biblioteca Lake
    # que deve ser carregada antes com: %run /Workspace/Libraries/Lake
    
    if 'connect_to_datalake' not in globals():
        print("❌ Biblioteca Lake não carregada. Execute: %run /Workspace/Libraries/Lake")
        sys.exit(1)
    
    # Conectar ao datalake
    connect_to_datalake(
        username="USR_PROD_INFORMATICA_SAUDE",
        password=dbutils.secrets.get(scope="INNOVATION_RAW", key="USR_PROD_INFORMATICA_SAUDE"),
        layer="RAWZN",
        level="LOW",
        dbx_secret_scope="INNOVATION_RAW"
    )
    
    print("✅ Conexão com Oracle Lake estabelecida!")
    print("✅ Função run_sql disponível globalmente")
    print("✅ Ambiente pronto para Streamlit")
    
except Exception as e:
    print(f"❌ Erro ao conectar ao Oracle Lake: {str(e)}")
    sys.exit(1)

"""
Conexão com Oracle Lake usando JayDeBeAPI (mesma abordagem da biblioteca Lake)
Adaptado para funcionar no Streamlit rodando em cluster Databricks
"""

import streamlit as st
import pandas as pd
import os
import sys

# Conexão global com Oracle Lake
_lake_connection = None

@st.cache_resource
def init_lake_connection():
    """
    Inicializa conexão com Oracle Lake usando JayDeBeAPI
    Mesma abordagem da biblioteca Lake do Databricks
    """
    global _lake_connection
    
    try:
        # Importar JayDeBeAPI
        try:
            import jaydebeapi
        except ImportError:
            st.error("❌ Biblioteca JayDeBeAPI não instalada. Execute: pip install JayDeBeAPI")
            return None
        
        # Obter credenciais
        # No Databricks Apps, usar secrets (recomendação do admin)
        username = "USR_PROD_INFORMATICA_SAUDE"
        
        # Tentar obter senha do Streamlit secrets (Databricks App secrets)
        try:
            password = st.secrets.get("ORACLE_PASSWORD")
        except:
            password = None
        
        # Fallback: variável de ambiente
        if not password:
            password = os.environ.get("ORACLE_PASSWORD")
        
        if not password:
            st.error("❌ Senha do Oracle não configurada")
            st.info("""
            💡 Configure o secret ORACLE_PASSWORD no Databricks App:
            1. Vá em App Settings → Secrets
            2. Adicione: ORACLE_PASSWORD = (senha do USR_PROD_INFORMATICA_SAUDE)
            3. O secret fica protegido e não aparece no código fonte
            """)
            return None
        
        # String JDBC para RAWZN LOW (mesma do Lake.py)
        jdbc_url = 'jdbc:oracle:thin:@(description=(retry_count=2)(retry_delay=3)(SOURCE_ROUTE = YES)(ADDRESS = (PROTOCOL = TCP)(HOST = 10.20.1.79)(PORT = 1521))(address=(protocol=tcps)(port=1522)(host=dbraw.adb.sa-saopaulo-1.oraclecloud.com))(connect_data=(service_name=ga7aea8a1e872fc_dbrawzn_low.adb.oraclecloud.com))(security=(ssl_server_cert_dn="CN=adb.sa-saopaulo-1.oraclecloud.com, OU=Oracle ADB SAOPAULO, O=Oracle Corporation, L=Redwood City, ST=California, C=US")))'
        
        # Caminho do driver JDBC
        # Tentar caminho relativo (para Databricks Apps) primeiro
        jdbc_driver_path = os.path.join(os.path.dirname(__file__), '..', 'ojdbc11.jar')
        
        # Fallback: caminho absoluto (para clusters)
        if not os.path.exists(jdbc_driver_path):
            jdbc_driver_path = "/Workspace/Libraries/DatalakeConnector/ojdbc11.jar"
        
        if not os.path.exists(jdbc_driver_path):
            st.error(f"❌ Driver JDBC não encontrado")
            st.info("""
            💡 Para Databricks Apps, coloque o arquivo ojdbc11.jar na pasta app/
            Para clusters, o driver deve estar em /Workspace/Libraries/DatalakeConnector/
            """)
            return None
        
        # Conectar ao Oracle
        with st.spinner("Conectando ao Oracle Lake..."):
            connection = jaydebeapi.connect(
                "oracle.jdbc.driver.OracleDriver",
                jdbc_url,
                {
                    'user': username,
                    'password': password,
                    'v$session.osuser': "DATABRICKS_STREAMLIT"
                },
                jdbc_driver_path
            )
            
            # Configurar conexão (mesmas configurações do Lake.py)
            connection.jconn.setAutoCommit(False)
            connection.jconn.setReadOnly(True)
            connection.jconn.setDefaultRowPrefetch(10_000)
        
        _lake_connection = connection
        st.success("✅ Conexão com Oracle Lake estabelecida!")
        return connection
        
    except Exception as e:
        st.error(f"❌ Erro ao conectar ao Oracle Lake: {str(e)}")
        st.exception(e)
        return None


def execute_lake_query(query):
    """
    Executa query no Oracle Lake usando JayDeBeAPI
    Mesma lógica da função run_sql do Lake.py
    
    Args:
        query: Query SQL para executar
        
    Returns:
        DataFrame pandas com os resultados
    """
    global _lake_connection
    
    try:
        # Inicializar conexão se necessário
        if _lake_connection is None:
            _lake_connection = init_lake_connection()
            
        if _lake_connection is None:
            return pd.DataFrame()
        
        # Limpar query (remover ; final se houver)
        query = query.strip()
        if query.endswith(";"):
            query = query[:-1]
        
        # Executar query
        cursor = None
        try:
            cursor = _lake_connection.cursor()
            cursor.arraysize = 10_000
            cursor.execute(query)
            
            # Verificar se é SELECT (tem resultados)
            if cursor.description is None:
                # Não é SELECT (INSERT/UPDATE/DELETE)
                _lake_connection.commit()
                return None
            
            # Obter colunas e resultados
            columns = [desc[0] for desc in cursor.description]
            results = cursor.fetchall()
            
            return pd.DataFrame(results, columns=columns)
            
        finally:
            if cursor is not None:
                try:
                    cursor.close()
                except:
                    pass
                    
    except Exception as e:
        st.error(f"❌ Erro ao executar query: {str(e)}")
        return pd.DataFrame()

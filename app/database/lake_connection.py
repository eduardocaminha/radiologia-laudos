"""
Conexão com Oracle Lake
- Em Databricks Apps: usa Serving Endpoint (API HTTP)
- Em cluster: usa JayDeBeAPI direto
"""

import streamlit as st
import pandas as pd
import os
import sys
import requests

# Conexão global com Oracle Lake
_lake_connection = None

# URL do Serving Endpoint (configurar via env var)
ORACLE_ENDPOINT_URL = os.environ.get('ORACLE_ENDPOINT_URL')


def execute_lake_query_via_endpoint(query):
    """
    Executa query no Oracle Lake via Serving Endpoint (HTTP)
    Usado em Databricks Apps onde JayDeBeAPI não funciona
    """
    if not ORACLE_ENDPOINT_URL:
        st.error("❌ ORACLE_ENDPOINT_URL não configurado")
        return pd.DataFrame()
    
    try:
        response = requests.post(
            f"{ORACLE_ENDPOINT_URL}/query",
            json={'query': query},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                return pd.DataFrame(result['data'])
            else:
                st.error(f"❌ Erro no endpoint: {result.get('error')}")
                return pd.DataFrame()
        else:
            st.error(f"❌ Erro HTTP {response.status_code}: {response.text}")
            return pd.DataFrame()
            
    except Exception as e:
        st.error(f"❌ Erro ao chamar endpoint: {str(e)}")
        return pd.DataFrame()


@st.cache_resource
def init_lake_connection():
    """
    Inicializa conexão com Oracle Lake usando JayDeBeAPI
    Mesma abordagem da biblioteca Lake do Databricks
    """
    global _lake_connection
    
    try:
        # Instalar JDK automaticamente se necessário
        try:
            import jdk
            if not os.environ.get('JAVA_HOME'):
                with st.spinner("Instalando Java JDK..."):
                    java_home = jdk.install('17')
                    os.environ['JAVA_HOME'] = java_home
                    os.environ['PATH'] = f"{java_home}/bin:{os.environ.get('PATH', '')}"
                    st.info(f"✅ Java instalado em: {java_home}")
        except Exception as e:
            st.warning(f"⚠️ Não foi possível instalar Java automaticamente: {str(e)}")
        
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
        
        # String JDBC para RAWZN LOW - usando apenas endpoint público (TCPS)
        # Databricks Apps não tem acesso ao IP privado 10.20.1.79
        jdbc_url = 'jdbc:oracle:thin:@(description=(retry_count=2)(retry_delay=3)(address=(protocol=tcps)(port=1522)(host=dbraw.adb.sa-saopaulo-1.oraclecloud.com))(connect_data=(service_name=ga7aea8a1e872fc_dbrawzn_low.adb.oraclecloud.com))(security=(ssl_server_cert_dn="CN=adb.sa-saopaulo-1.oraclecloud.com, OU=Oracle ADB SAOPAULO, O=Oracle Corporation, L=Redwood City, ST=California, C=US")))'
        
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
    Executa query no Oracle Lake
    - Se ORACLE_ENDPOINT_URL configurado: usa API HTTP
    - Senão: usa JayDeBeAPI direto
    
    Args:
        query: Query SQL para executar
        
    Returns:
        DataFrame pandas com os resultados
    """
    # Se endpoint configurado, usar API HTTP
    if ORACLE_ENDPOINT_URL:
        return execute_lake_query_via_endpoint(query)
    
    # Senão, usar JayDeBeAPI direto
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

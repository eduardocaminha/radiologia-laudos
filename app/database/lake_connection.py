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
        
        # Verificar se dbutils está disponível (injetado pelo Databricks)
        try:
            # No Databricks, dbutils já está disponível globalmente
            if 'dbutils' not in globals():
                # Tentar obter do IPython/Databricks runtime
                from IPython import get_ipython
                ipython = get_ipython()
                if ipython and hasattr(ipython, 'user_ns'):
                    dbutils = ipython.user_ns.get('dbutils')
                    if dbutils is None:
                        raise RuntimeError("dbutils não encontrado no namespace")
                else:
                    raise RuntimeError("Ambiente IPython não disponível")
            else:
                dbutils = globals()['dbutils']
        except Exception as e:
            st.error(f"❌ Erro ao acessar dbutils: {str(e)}")
            st.info("💡 Certifique-se de estar rodando em um cluster Databricks (não Serverless)")
            return None
        
        # Obter credenciais do Secrets Manager
        try:
            username = "USR_PROD_INFORMATICA_SAUDE"
            password = dbutils.secrets.get(scope="INNOVATION_RAW", key="USR_PROD_INFORMATICA_SAUDE")
        except Exception as e:
            st.error(f"❌ Erro ao obter credenciais: {str(e)}")
            return None
        
        # String JDBC para RAWZN LOW (mesma do Lake.py)
        jdbc_url = 'jdbc:oracle:thin:@(description=(retry_count=2)(retry_delay=3)(SOURCE_ROUTE = YES)(ADDRESS = (PROTOCOL = TCP)(HOST = 10.20.1.79)(PORT = 1521))(address=(protocol=tcps)(port=1522)(host=dbraw.adb.sa-saopaulo-1.oraclecloud.com))(connect_data=(service_name=ga7aea8a1e872fc_dbrawzn_low.adb.oraclecloud.com))(security=(ssl_server_cert_dn="CN=adb.sa-saopaulo-1.oraclecloud.com, OU=Oracle ADB SAOPAULO, O=Oracle Corporation, L=Redwood City, ST=California, C=US")))'
        
        # Caminho do driver JDBC
        jdbc_driver_path = "/Workspace/Libraries/DatalakeConnector/ojdbc11.jar"
        
        if not os.path.exists(jdbc_driver_path):
            st.error(f"❌ Driver JDBC não encontrado: {jdbc_driver_path}")
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

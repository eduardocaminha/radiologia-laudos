"""
Databricks Serving Endpoint para queries Oracle Lake
Roda em cluster com Java e acesso à rede privada Oracle
"""

from flask import Flask, request, jsonify
import jaydebeapi
import pandas as pd
import os

app = Flask(__name__)

# Configuração Oracle (mesma do Lake.py)
ORACLE_CONFIG = {
    'username': 'USR_PROD_INFORMATICA_SAUDE',
    'jdbc_url': 'jdbc:oracle:thin:@(description=(retry_count=2)(retry_delay=3)(SOURCE_ROUTE = YES)(ADDRESS = (PROTOCOL = TCP)(HOST = 10.20.1.79)(PORT = 1521))(address=(protocol=tcps)(port=1522)(host=dbraw.adb.sa-saopaulo-1.oraclecloud.com))(connect_data=(service_name=ga7aea8a1e872fc_dbrawzn_low.adb.oraclecloud.com))(security=(ssl_server_cert_dn="CN=adb.sa-saopaulo-1.oraclecloud.com, OU=Oracle ADB SAOPAULO, O=Oracle Corporation, L=Redwood City, ST=California, C=US")))',
    'jdbc_driver': '/Workspace/Libraries/DatalakeConnector/ojdbc11.jar'
}

# Conexão global (reutilizar)
_connection = None


def get_oracle_connection():
    """Obter ou criar conexão Oracle"""
    global _connection
    
    if _connection is None:
        # Obter senha do dbutils
        from pyspark.sql import SparkSession
        spark = SparkSession.builder.getOrCreate()
        password = spark.conf.get("spark.oracle.password")
        
        # Conectar
        _connection = jaydebeapi.connect(
            "oracle.jdbc.driver.OracleDriver",
            ORACLE_CONFIG['jdbc_url'],
            {
                'user': ORACLE_CONFIG['username'],
                'password': password,
                'v$session.osuser': "DATABRICKS_ENDPOINT"
            },
            ORACLE_CONFIG['jdbc_driver']
        )
        
        # Configurar conexão
        _connection.jconn.setAutoCommit(False)
        _connection.jconn.setReadOnly(True)
        _connection.jconn.setDefaultRowPrefetch(10_000)
    
    return _connection


@app.route('/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({'status': 'healthy'})


@app.route('/query', methods=['POST'])
def execute_query():
    """
    Executar query no Oracle Lake
    
    Body JSON:
    {
        "query": "SELECT * FROM RAWZN.RAW_HSP_TB_PROCEDIMENTO WHERE CD_PROCEDIMENTO = 123"
    }
    
    Response:
    {
        "success": true,
        "data": [...],
        "columns": [...],
        "row_count": 10
    }
    """
    try:
        # Obter query do request
        data = request.get_json()
        query = data.get('query')
        
        if not query:
            return jsonify({
                'success': False,
                'error': 'Query não fornecida'
            }), 400
        
        # Limpar query
        query = query.strip()
        if query.endswith(';'):
            query = query[:-1]
        
        # Executar query
        conn = get_oracle_connection()
        cursor = conn.cursor()
        cursor.arraysize = 10_000
        cursor.execute(query)
        
        # Obter resultados
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        
        cursor.close()
        
        # Converter para formato JSON-friendly
        data = [dict(zip(columns, row)) for row in rows]
        
        return jsonify({
            'success': True,
            'data': data,
            'columns': columns,
            'row_count': len(data)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/procedimento/codigo/<int:cd_procedimento>', methods=['GET'])
def buscar_por_codigo(cd_procedimento):
    """Buscar procedimento por código"""
    query = f"""
    SELECT DISTINCT CD_PROCEDIMENTO, NM_PROCEDIMENTO
    FROM RAWZN.RAW_HSP_TB_PROCEDIMENTO
    WHERE CD_PROCEDIMENTO = {cd_procedimento}
    """
    
    return execute_query_internal(query)


@app.route('/procedimento/termo', methods=['POST'])
def buscar_por_termo():
    """
    Buscar procedimento por termo
    
    Body JSON:
    {
        "termo": "TOMOGRAFIA"
    }
    """
    data = request.get_json()
    termo = data.get('termo', '')
    
    if not termo:
        return jsonify({
            'success': False,
            'error': 'Termo não fornecido'
        }), 400
    
    query = f"""
    SELECT DISTINCT CD_PROCEDIMENTO, NM_PROCEDIMENTO
    FROM RAWZN.RAW_HSP_TB_PROCEDIMENTO
    WHERE UPPER(NM_PROCEDIMENTO) LIKE UPPER('%{termo}%')
    ORDER BY NM_PROCEDIMENTO
    FETCH FIRST 100 ROWS ONLY
    """
    
    return execute_query_internal(query)


def execute_query_internal(query):
    """Helper para executar query e retornar JSON"""
    try:
        conn = get_oracle_connection()
        cursor = conn.cursor()
        cursor.arraysize = 10_000
        cursor.execute(query)
        
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        cursor.close()
        
        data = [dict(zip(columns, row)) for row in rows]
        
        return jsonify({
            'success': True,
            'data': data,
            'columns': columns,
            'row_count': len(data)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)

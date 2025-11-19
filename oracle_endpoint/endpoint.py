"""
Databricks Serving Endpoint para queries Oracle Lake
Roda em cluster com Java e acesso à rede privada Oracle
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import jaydebeapi
import pandas as pd
import os
from typing import Optional, List, Dict, Any

app = FastAPI(title="Oracle Lake API", version="1.0.0")

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
        # Obter senha do dbutils.secrets (mesma forma que nos notebooks)
        try:
            from pyspark.dbutils import DBUtils
            from pyspark.sql import SparkSession
            spark = SparkSession.builder.getOrCreate()
            dbutils = DBUtils(spark)
            password = dbutils.secrets.get(scope="INNOVATION_RAW", key="USR_PROD_INFORMATICA_SAUDE")
        except:
            # Fallback: tentar do ambiente
            import os
            password = os.environ.get("ORACLE_PASSWORD")
            if not password:
                raise Exception("Senha Oracle não encontrada (dbutils.secrets ou ORACLE_PASSWORD)")
        
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


# Modelos Pydantic
class QueryRequest(BaseModel):
    query: str

class TermoRequest(BaseModel):
    termo: str

class QueryResponse(BaseModel):
    success: bool
    data: Optional[List[Dict[str, Any]]] = None
    columns: Optional[List[str]] = None
    row_count: Optional[int] = None
    error: Optional[str] = None


@app.get("/health")
async def health():
    """Health check"""
    return {"status": "healthy"}


@app.post("/query", response_model=QueryResponse)
async def execute_query(request: QueryRequest):
    """
    Executar query no Oracle Lake
    
    Body JSON:
    ```json
    {
        "query": "SELECT * FROM RAWZN.RAW_HSP_TB_PROCEDIMENTO WHERE CD_PROCEDIMENTO = 123"
    }
    ```
    """
    try:
        query = request.query.strip()
        
        if not query:
            raise HTTPException(status_code=400, detail="Query não fornecida")
        
        # Limpar query
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
        
        return QueryResponse(
            success=True,
            data=data,
            columns=columns,
            row_count=len(data)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/procedimento/codigo/{cd_procedimento}", response_model=QueryResponse)
async def buscar_por_codigo(cd_procedimento: int):
    """Buscar procedimento por código"""
    query = f"""
    SELECT DISTINCT CD_PROCEDIMENTO, NM_PROCEDIMENTO
    FROM RAWZN.RAW_HSP_TB_PROCEDIMENTO
    WHERE CD_PROCEDIMENTO = {cd_procedimento}
    """
    
    return await execute_query_internal(query)


@app.post("/procedimento/termo", response_model=QueryResponse)
async def buscar_por_termo(request: TermoRequest):
    """
    Buscar procedimento por termo
    
    Body JSON:
    ```json
    {
        "termo": "TOMOGRAFIA"
    }
    ```
    """
    if not request.termo:
        raise HTTPException(status_code=400, detail="Termo não fornecido")
    
    query = f"""
    SELECT DISTINCT CD_PROCEDIMENTO, NM_PROCEDIMENTO
    FROM RAWZN.RAW_HSP_TB_PROCEDIMENTO
    WHERE UPPER(NM_PROCEDIMENTO) LIKE UPPER('%{request.termo}%')
    ORDER BY NM_PROCEDIMENTO
    FETCH FIRST 100 ROWS ONLY
    """
    
    return await execute_query_internal(query)


async def execute_query_internal(query: str) -> QueryResponse:
    """Helper para executar query e retornar resposta"""
    try:
        conn = get_oracle_connection()
        cursor = conn.cursor()
        cursor.arraysize = 10_000
        cursor.execute(query)
        
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        cursor.close()
        
        data = [dict(zip(columns, row)) for row in rows]
        
        return QueryResponse(
            success=True,
            data=data,
            columns=columns,
            row_count=len(data)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8080)

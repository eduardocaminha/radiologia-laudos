"""
Script para criar/atualizar Databricks Serving Endpoint
Execute em um notebook Databricks
"""

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.serving import ServedEntityInput, EndpointCoreConfigInput

# Configuração
ENDPOINT_NAME = "oracle-lake-api"
CLUSTER_ID = "SEU_CLUSTER_ID"  # Substitua pelo ID do cluster com Java

# Inicializar cliente
w = WorkspaceClient()

# Configuração do endpoint
endpoint_config = EndpointCoreConfigInput(
    name=ENDPOINT_NAME,
    served_entities=[
        ServedEntityInput(
            name="oracle-query-service",
            entity_name="oracle_endpoint",  # Nome do modelo/código
            entity_version="1",
            workload_size="Small",
            scale_to_zero_enabled=False  # Manter sempre ativo
        )
    ]
)

try:
    # Tentar criar endpoint
    print(f"Criando endpoint {ENDPOINT_NAME}...")
    endpoint = w.serving_endpoints.create_and_wait(
        name=ENDPOINT_NAME,
        config=endpoint_config
    )
    print(f"✅ Endpoint criado: {endpoint.name}")
    print(f"URL: {endpoint.url}")
    
except Exception as e:
    if "already exists" in str(e):
        # Atualizar endpoint existente
        print(f"Atualizando endpoint {ENDPOINT_NAME}...")
        endpoint = w.serving_endpoints.update_config_and_wait(
            name=ENDPOINT_NAME,
            served_entities=endpoint_config.served_entities
        )
        print(f"✅ Endpoint atualizado: {endpoint.name}")
    else:
        print(f"❌ Erro: {e}")
        raise

print(f"\n🎯 Endpoint URL: {endpoint.url}")
print(f"📝 Use essa URL no Streamlit app")

"""
Configurações e constantes do projeto
"""

# Schema e tabelas Gold no Delta Lake
SCHEMA_GOLD = "innovation_dev.gold"
TABLE_MODALIDADES = f"{SCHEMA_GOLD}.radiologia_laudos_modalidades"
TABLE_DESCRICOES = f"{SCHEMA_GOLD}.radiologia_laudos_descricoes"
TABLE_PROCEDIMENTOS = f"{SCHEMA_GOLD}.radiologia_laudos_procedimentos"

# Configurações Oracle Lake
ORACLE_SCHEMA = "RAWZN"
ORACLE_TABLE_PROCEDIMENTO_HSP = f"{ORACLE_SCHEMA}.RAW_HSP_TB_PROCEDIMENTO"
ORACLE_TABLE_PROCEDIMENTO_PSC = f"{ORACLE_SCHEMA}.RAW_PSC_TB_PROCEDIMENTO"

# Limites de busca
MAX_RESULTADOS_BUSCA = 50

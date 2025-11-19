"""
Configurações e constantes do projeto
"""

# Schema e tabelas Gold no Delta Lake
SCHEMA_GOLD = "innovation_dev.gold"
TABLE_MODALIDADES = f"{SCHEMA_GOLD}.radiologia_laudos_modalidades"
TABLE_DESCRICOES = f"{SCHEMA_GOLD}.radiologia_laudos_descricoes"
TABLE_PROCEDIMENTOS = f"{SCHEMA_GOLD}.radiologia_laudos_procedimentos"

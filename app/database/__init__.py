"""
Módulo de acesso a dados (Databricks SQL Warehouse e Oracle Lake)
"""

from .connections import get_databricks_connection, buscar_procedimento_oracle
from .queries import execute_query, execute_command
from .schema import criar_tabelas_gold, verificar_tabelas_existem

__all__ = [
    'get_databricks_connection',
    'buscar_procedimento_oracle',
    'execute_query',
    'execute_command',
    'criar_tabelas_gold',
    'verificar_tabelas_existem'
]

-- ============================================================================
-- Renomear coluna: dt_procedimento_realizado → tms_procedimento_realizado
-- ============================================================================
-- Execute este script UMA VEZ no Databricks
-- ============================================================================

-- 1. Verificar schema atual
DESCRIBE innovation_dev.bronze.radiologia_laudos_extraidos;

-- 2. Renomear coluna
ALTER TABLE innovation_dev.bronze.radiologia_laudos_extraidos
RENAME COLUMN dt_procedimento_realizado TO tms_procedimento_realizado;

-- 3. Verificar schema atualizado
DESCRIBE innovation_dev.bronze.radiologia_laudos_extraidos;

-- 4. Validar dados (verificar se timestamp está preservado)
SELECT 
    accession_number,
    tms_procedimento_realizado,
    ano_mes,
    dt_carga
FROM innovation_dev.bronze.radiologia_laudos_extraidos
LIMIT 10;

-- 5. Verificar estatísticas
SELECT 
    COUNT(*) as total_registros,
    COUNT(tms_procedimento_realizado) as registros_com_timestamp,
    MIN(tms_procedimento_realizado) as timestamp_min,
    MAX(tms_procedimento_realizado) as timestamp_max
FROM innovation_dev.bronze.radiologia_laudos_extraidos;

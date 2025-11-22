-- ============================================================================
-- Renomear colunas TIMESTAMP: dt_* → tms_*
-- ============================================================================
-- Execute este script UMA VEZ no Databricks
-- Padrão: tms_ para TIMESTAMP, dt_ para DATE
-- ============================================================================

-- 1. Verificar schema atual
DESCRIBE innovation_dev.bronze.radiologia_laudos_extraidos;

-- 2. Renomear colunas TIMESTAMP
ALTER TABLE innovation_dev.bronze.radiologia_laudos_extraidos
RENAME COLUMN dt_procedimento_realizado TO tms_procedimento_realizado;

ALTER TABLE innovation_dev.bronze.radiologia_laudos_extraidos
RENAME COLUMN dt_carga TO tms_carga;

-- 3. Verificar schema atualizado
DESCRIBE innovation_dev.bronze.radiologia_laudos_extraidos;

-- 4. Validar dados (verificar se timestamps estão preservados)
SELECT 
    accession_number,
    tms_procedimento_realizado,
    tms_carga,
    ano_mes
FROM innovation_dev.bronze.radiologia_laudos_extraidos
LIMIT 10;

-- 5. Verificar estatísticas
SELECT 
    COUNT(*) as total_registros,
    COUNT(tms_procedimento_realizado) as registros_com_timestamp,
    MIN(tms_procedimento_realizado) as timestamp_min,
    MAX(tms_procedimento_realizado) as timestamp_max
FROM innovation_dev.bronze.radiologia_laudos_extraidos;

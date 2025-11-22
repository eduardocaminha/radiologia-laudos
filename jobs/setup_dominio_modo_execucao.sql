-- ============================================================================
-- Setup: Tabela de Domínio para modo_execucao
-- ============================================================================
-- Execute este script UMA VEZ no Databricks para criar a tabela de domínio
-- e padronizar os dados existentes
-- ============================================================================

-- 1. Criar tabela de domínio
CREATE TABLE IF NOT EXISTS innovation_dev.gold.radiologia_laudos_modo_execucao (
    id_modo_execucao INT NOT NULL,
    codigo STRING NOT NULL,
    nome STRING NOT NULL,
    descricao STRING,
    ativo BOOLEAN,
    dt_criacao TIMESTAMP,
    dt_atualizacao TIMESTAMP
) USING DELTA
COMMENT 'Tabela de domínio para valores válidos de modo_execucao';

-- Nota: Delta Lake não suporta UNIQUE constraints e DEFAULT values nativamente
-- A unicidade é garantida pela lógica de inserção (MERGE)
-- Valores padrão são definidos explicitamente no MERGE

-- 2. Inserir valores padrão (usando MERGE para evitar duplicatas)
MERGE INTO innovation_dev.gold.radiologia_laudos_modo_execucao AS target
USING (
    SELECT 1 AS id_modo_execucao, 'job_diario' AS codigo, 'Job Diário' AS nome, 
           'Extração diária automática (D-1) executada pelo job agendado' AS descricao
    UNION ALL
    SELECT 2, 'reprocessamento_historico', 'Reprocessamento Histórico',
           'Reprocessamento de períodos anteriores em lotes semanais'
) AS source
ON target.id_modo_execucao = source.id_modo_execucao
WHEN NOT MATCHED THEN
    INSERT (id_modo_execucao, codigo, nome, descricao, ativo, dt_criacao, dt_atualizacao)
    VALUES (source.id_modo_execucao, source.codigo, source.nome, source.descricao, TRUE, CURRENT_TIMESTAMP(), NULL);

-- 3. Verificar valores inseridos
SELECT * FROM innovation_dev.gold.radiologia_laudos_modo_execucao ORDER BY id_modo_execucao;

-- ============================================================================
-- Padronização dos Dados Existentes
-- ============================================================================

-- 4. Verificar valores atuais na tabela Bronze
SELECT 
    modo_execucao,
    COUNT(*) as total_registros,
    MIN(dt_carga) as primeira_carga,
    MAX(dt_carga) as ultima_carga
FROM innovation_dev.bronze.radiologia_laudos_extraidos
GROUP BY modo_execucao
ORDER BY total_registros DESC;

-- 5. Atualizar valores antigos para o padrão
-- Mapear 'incremental' → 'job_diario'
UPDATE innovation_dev.bronze.radiologia_laudos_extraidos
SET modo_execucao = 'job_diario'
WHERE modo_execucao = 'incremental';

-- Mapear 'reprocessamento' → 'reprocessamento_historico'
UPDATE innovation_dev.bronze.radiologia_laudos_extraidos
SET modo_execucao = 'reprocessamento_historico'
WHERE modo_execucao = 'reprocessamento';

-- 6. Verificar se há valores inválidos
SELECT DISTINCT modo_execucao
FROM innovation_dev.bronze.radiologia_laudos_extraidos
WHERE modo_execucao NOT IN (
    SELECT codigo 
    FROM innovation_dev.gold.radiologia_laudos_modo_execucao 
    WHERE ativo = TRUE
);

-- Se retornar algum valor, investigar e corrigir manualmente

-- 7. Validação final - todos os registros devem ter modo válido
SELECT 
    b.modo_execucao,
    m.nome,
    COUNT(*) as total_registros
FROM innovation_dev.bronze.radiologia_laudos_extraidos b
LEFT JOIN innovation_dev.gold.radiologia_laudos_modo_execucao m 
    ON b.modo_execucao = m.codigo
GROUP BY b.modo_execucao, m.nome
ORDER BY total_registros DESC;

-- ============================================================================
-- Queries de Monitoramento
-- ============================================================================

-- Volume por modo de execução
SELECT 
    m.codigo,
    m.nome,
    COUNT(*) as total_laudos,
    COUNT(DISTINCT b.accession_number) as laudos_unicos,
    MIN(b.dt_carga) as primeira_carga,
    MAX(b.dt_carga) as ultima_carga
FROM innovation_dev.bronze.radiologia_laudos_extraidos b
INNER JOIN innovation_dev.gold.radiologia_laudos_modo_execucao m 
    ON b.modo_execucao = m.codigo
GROUP BY m.codigo, m.nome
ORDER BY total_laudos DESC;

-- Histórico de cargas por dia e modo
SELECT 
    DATE(b.dt_carga) as dia_carga,
    m.nome as modo_execucao,
    COUNT(*) as total_laudos,
    COUNT(DISTINCT b.cd_paciente) as pacientes_unicos
FROM innovation_dev.bronze.radiologia_laudos_extraidos b
INNER JOIN innovation_dev.gold.radiologia_laudos_modo_execucao m 
    ON b.modo_execucao = m.codigo
GROUP BY dia_carga, m.nome
ORDER BY dia_carga DESC, total_laudos DESC
LIMIT 30;

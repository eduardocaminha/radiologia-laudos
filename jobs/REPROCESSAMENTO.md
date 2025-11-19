# 🔄 Reprocessamento Histórico de Laudos

Notebook para processar laudos de períodos anteriores em **lotes semanais**.

## 📋 Quando Usar

- ✅ **Carga inicial histórica** (ex: processar últimos 6 meses)
- ✅ **Reprocessamento após correções** (ex: bug corrigido, reprocessar dados)
- ✅ **Períodos específicos** (ex: processar apenas Janeiro/2025)
- ✅ **Recuperação de falhas** (ex: job diário falhou por 1 semana)

## 🚀 Como Usar

### 1. Configurar Parâmetros

```python
data_inicio: 2024-06-01      # Data inicial (YYYY-MM-DD)
data_fim: 2024-12-31         # Data final (YYYY-MM-DD)
tamanho_lote: 7              # Dias por lote (7, 14 ou 30)
modo_teste: false            # true = apenas conta, false = processa
```

### 2. Executar

**Opção A: Via UI Databricks**
1. Abra o notebook `reprocessamento_historico`
2. Configure os widgets no topo
3. Run All

**Opção B: Via CLI**
```bash
databricks jobs run-now --job-id <JOB_ID> \
  --notebook-params '{
    "data_inicio":"2024-06-01",
    "data_fim":"2024-12-31",
    "tamanho_lote":"7",
    "modo_teste":"false"
  }'
```

## 📊 Exemplos de Uso

### Exemplo 1: Carga Inicial (6 meses)
```python
data_inicio: 2024-06-01
data_fim: 2024-12-01
tamanho_lote: 7        # ~26 lotes de 1 semana
modo_teste: false
```

**Resultado:**
- 26 lotes processados
- ~6 meses de dados
- Tempo estimado: 30-60 minutos

### Exemplo 2: Reprocessar Janeiro/2025
```python
data_inicio: 2025-01-01
data_fim: 2025-02-01
tamanho_lote: 7        # ~4 lotes
modo_teste: false
```

### Exemplo 3: Teste Antes de Processar
```python
data_inicio: 2024-06-01
data_fim: 2024-12-01
tamanho_lote: 7
modo_teste: true       # ← Apenas mostra estatísticas
```

**Output:**
```
📦 LOTE 1/26
   Período: 2024-06-01 até 2024-06-08
   📊 15,234 procedimentos realizados
   📄 12,456 laudos extraídos
   🧪 MODO TESTE - Estatísticas:
      - Accession numbers únicos: 12,456
      - Procedimentos distintos: 81
      - Pacientes distintos: 10,234
```

## ⚙️ Configuração de Lotes

### Tamanho Recomendado

| Período Total | Tamanho Lote | Nº Lotes | Tempo Estimado |
|---------------|--------------|----------|----------------|
| 1 mês | 7 dias | ~4 | 5-10 min |
| 3 meses | 7 dias | ~13 | 15-30 min |
| 6 meses | 7 dias | ~26 | 30-60 min |
| 1 ano | 14 dias | ~26 | 30-60 min |
| 2 anos | 30 dias | ~24 | 30-60 min |

### Por Que Lotes?

**❌ Sem Lotes (processar tudo de uma vez):**
- Timeout do Oracle
- Memória insuficiente
- Difícil recuperar de erros
- Sem progresso visível

**✅ Com Lotes:**
- Processamento controlado
- Recuperação de erros (continua do lote que falhou)
- Progresso visível
- Otimização incremental

## 🔍 Monitoramento

### Durante a Execução

```
📦 LOTE 5/26
   Período: 2024-06-29 até 2024-07-06
   Dias: 7
----------------------------------------------------------------------
   ✅ Tabela temporária limpa
   📊 18,234 procedimentos realizados
   📄 15,123 laudos extraídos
   ✅ Merge concluído - 15,123 laudos processados
   ⏱️  Tempo: 45.3s
```

### Resumo Final

```
======================================================================
📊 RESUMO DO REPROCESSAMENTO HISTÓRICO
======================================================================
Período processado:          2024-06-01 até 2024-12-01
Total de lotes:              26
Lotes processados com sucesso: 26
Lotes com erro:              0
Procedimentos realizados:    456,789
Laudos extraídos:            389,234
Tempo total:                 35.2 minutos
Tempo médio por lote:        81.2 segundos
======================================================================

✅ Reprocessamento concluído!
   Dados salvos em: innovation_dev.bronze.radiologia_laudos_extraidos

🔧 Otimizando tabela Delta...
✅ Otimização concluída!
```

## 🛡️ Segurança e Idempotência

### Merge Inteligente

O notebook usa **Delta Lake MERGE** para evitar duplicatas:

```python
delta_table.merge(
    source,
    "target.accession_number = source.accession_number"
).whenMatchedUpdateAll()   # Atualiza se já existe
 .whenNotMatchedInsertAll() # Insere se não existe
```

**Resultado:**
- ✅ Pode reprocessar o mesmo período múltiplas vezes
- ✅ Não cria duplicatas
- ✅ Atualiza dados se necessário

### Modo Teste

Sempre teste antes de processar grandes volumes:

```python
modo_teste: true  # ← Apenas mostra estatísticas, não salva
```

## 🚨 Tratamento de Erros

### Lote com Erro

Se um lote falhar, o processo **continua** para os próximos:

```
📦 LOTE 12/26
   ❌ ERRO no lote 12: ORA-01013: user requested cancel of current operation

📦 LOTE 13/26
   ✅ Processado com sucesso
```

### Resumo de Erros

```
⚠️  LOTES COM ERRO:

   Lote 12 (2024-08-12 - 2024-08-19):
   ORA-01013: user requested cancel of current operation
```

### Reprocessar Lotes com Erro

Basta rodar novamente com o período específico:

```python
data_inicio: 2024-08-12
data_fim: 2024-08-19
tamanho_lote: 7
modo_teste: false
```

## 📈 Verificação Pós-Processamento

### Contagem por Mês

```sql
SELECT 
    ano_mes,
    COUNT(*) as total_laudos,
    COUNT(DISTINCT accession_number) as laudos_unicos,
    COUNT(DISTINCT cd_procedimento) as procedimentos_distintos
FROM innovation_dev.bronze.radiologia_laudos_extraidos
WHERE dt_processamento >= '2024-06-01'
  AND dt_processamento < '2024-12-01'
GROUP BY ano_mes
ORDER BY ano_mes;
```

### Verificar Duplicatas

```sql
SELECT accession_number, COUNT(*) as count
FROM innovation_dev.bronze.radiologia_laudos_extraidos
WHERE dt_processamento >= '2024-06-01'
  AND dt_processamento < '2024-12-01'
GROUP BY accession_number
HAVING COUNT(*) > 1;
```

Deve retornar **0 linhas**! ✅

## 💡 Dicas

### 1. Comece Pequeno
```python
# Teste com 1 mês primeiro
data_inicio: 2024-11-01
data_fim: 2024-12-01
tamanho_lote: 7
modo_teste: true  # ← Sempre teste primeiro!
```

### 2. Ajuste o Tamanho do Lote

- **Muitos dados por dia?** → Use lotes menores (7 dias)
- **Poucos dados por dia?** → Use lotes maiores (30 dias)
- **Erros de timeout?** → Reduza o tamanho do lote

### 3. Execute Fora do Horário de Pico

- Madrugada (02:00 - 06:00)
- Finais de semana
- Evita impacto no Oracle de produção

### 4. Monitore o Progresso

O notebook mostra progresso em tempo real:
- Lote atual / Total
- Tempo por lote
- Laudos processados

## 🔗 Relação com Job Diário

| Aspecto | Job Diário | Reprocessamento Histórico |
|---------|-----------|---------------------------|
| **Frequência** | Automático (02:00 AM) | Manual (sob demanda) |
| **Período** | D-1 (1 dia) | Customizado (semanas/meses) |
| **Lotes** | Não usa | Sim (7-30 dias) |
| **Uso** | Operação normal | Carga inicial / Correções |
| **Merge** | Sim | Sim |
| **Duplicatas** | Evita | Evita |

## ✅ Checklist

Antes de executar:

- [ ] Configurei `data_inicio` e `data_fim`
- [ ] Escolhi `tamanho_lote` adequado
- [ ] Rodei em `modo_teste: true` primeiro
- [ ] Verifiquei as estatísticas do teste
- [ ] Configurei `modo_teste: false` para processar
- [ ] Executei fora do horário de pico
- [ ] Monitorei o progresso
- [ ] Verifiquei duplicatas após conclusão

---

**Pronto para processar histórico!** 🚀

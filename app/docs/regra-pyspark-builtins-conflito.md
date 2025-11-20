# Regra: Conflito de Funções Builtin com PySpark

## Problema

Ao usar `from pyspark.sql.functions import *` em notebooks Databricks, as funções `min()`, `max()`, `sum()`, `abs()`, `round()`, etc. do PySpark sobrescrevem as funções builtin do Python.

## ❌ Código Problemático

```python
from pyspark.sql.functions import *

# Erro: min() do PySpark espera 1 argumento (uma coluna)
valor_minimo = min(10, 20)  # TypeError: min() takes 1 positional argument but 2 were given

# Erro: max() do PySpark espera 1 argumento (uma coluna)
valor_maximo = max(10, 20)  # TypeError: max() takes 1 positional argument but 2 were given

# Erro: sum() do PySpark espera 1 argumento (uma coluna)
total = sum([1, 2, 3])  # TypeError
```

## ✅ Soluções

### Solução 1: Usar Operador Ternário (Recomendado para 2 valores)

```python
from pyspark.sql.functions import *

# Para min() com 2 valores
valor_minimo = a if a < b else b

# Para max() com 2 valores
valor_maximo = a if a > b else b

# Exemplo real:
lote_fim = lote_fim_calculado if lote_fim_calculado < data_fim else data_fim
tempo_medio = total_tempo / lotes if lotes > 0 else 0
```

### Solução 2: Usar Builtins Explicitamente

```python
from pyspark.sql.functions import *
import builtins

# Usar builtins explicitamente
valor_minimo = builtins.min(10, 20)
valor_maximo = builtins.max(10, 20)
total = builtins.sum([1, 2, 3])
```

### Solução 3: Importar Apenas Funções Necessárias (Melhor Prática)

```python
# ✅ Importar apenas o que precisa
from pyspark.sql.functions import col, lit, current_timestamp, desc, count, when

# Agora min() e max() builtin funcionam normalmente
valor_minimo = min(10, 20)
valor_maximo = max(10, 20)
```

### Solução 4: Alias na Importação

```python
from pyspark.sql.functions import min as spark_min, max as spark_max

# Usar spark_min/spark_max para PySpark
df.agg(spark_min('coluna'), spark_max('coluna'))

# min/max builtin funcionam normalmente
valor_minimo = min(10, 20)
valor_maximo = max(10, 20)
```

## 📋 Funções Afetadas

Funções builtin do Python que são sobrescritas por `import *`:

- `min()` → Use `builtins.min()` ou operador ternário
- `max()` → Use `builtins.max()` ou operador ternário
- `sum()` → Use `builtins.sum()`
- `abs()` → Use `builtins.abs()`
- `round()` → Use `builtins.round()`
- `pow()` → Use `builtins.pow()`
- `hash()` → Use `builtins.hash()`

## 🎯 Regra Geral

**SEMPRE que usar `from pyspark.sql.functions import *` em notebooks Databricks:**

1. **Prefira operador ternário** para `min()`/`max()` com 2 valores:
   ```python
   resultado = a if a < b else b  # min
   resultado = a if a > b else b  # max
   ```

2. **Use `builtins.`** quando precisar de funções builtin:
   ```python
   import builtins
   total = builtins.sum([1, 2, 3])
   ```

3. **Melhor ainda: evite `import *`**, importe apenas o necessário:
   ```python
   from pyspark.sql.functions import col, lit, current_timestamp
   ```

## 🔍 Como Identificar o Problema

Se você ver erros como:
- `TypeError: min() takes 1 positional argument but 2 were given`
- `TypeError: max() takes 1 positional argument but 2 were given`
- `TypeError: sum() of empty sequence`

**Causa:** Conflito entre PySpark functions e Python builtins.

**Solução:** Aplicar uma das soluções acima.

## 📌 Aplicar Esta Regra

- ✅ **Todos os notebooks Databricks**
- ✅ **Jobs PySpark**
- ✅ **Scripts que usam `pyspark.sql.functions`**
- ✅ **Código que mistura lógica Python com transformações Spark**

## 📝 Exemplos Reais do Projeto

### Exemplo 1: Cálculo de Lote Final
```python
# ❌ Errado
lote_fim = min(lote_inicio + timedelta(days=dias_por_lote), data_fim)

# ✅ Correto
lote_fim_calculado = lote_inicio + timedelta(days=dias_por_lote)
lote_fim = lote_fim_calculado if lote_fim_calculado < data_fim else data_fim
```

### Exemplo 2: Tempo Médio
```python
# ❌ Errado
tempo_medio = total_tempo / max(lotes_processados, 1)

# ✅ Correto
tempo_medio = total_tempo / lotes_processados if lotes_processados > 0 else 0
```

### Exemplo 3: Agregações Spark (Correto)
```python
from pyspark.sql.functions import min, max

# ✅ Correto - usando min/max do PySpark em DataFrames
df.agg(
    min('dt_procedimento_realizado'),
    max('dt_procedimento_realizado')
)
```

## 🚨 Atenção Especial

Este problema é **muito comum** em projetos Databricks e pode causar:
- Erros difíceis de debugar
- Comportamento inesperado
- Falhas em produção

**Sempre revise imports quando usar `pyspark.sql.functions`!**

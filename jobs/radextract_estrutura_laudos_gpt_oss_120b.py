from datetime import datetime
import json

from pyspark.sql.functions import col

from radextract_core.structure_report import RadiologyReportStructurer
from radextract_core.sanitize import preprocess_report


dbutils.widgets.text("data_inicio", "", "Data início (YYYY-MM-DD)")
dbutils.widgets.text("data_fim", "", "Data fim (YYYY-MM-DD)")
dbutils.widgets.text("limit_registros", "100", "Limite de laudos")
dbutils.widgets.text(
    "output_table",
    "innovation_dev.gold.radiologia_laudos_estruturados",
    "Tabela destino",
)


data_inicio = dbutils.widgets.get("data_inicio")
data_fim = dbutils.widgets.get("data_fim")
limit_registros = int(dbutils.widgets.get("limit_registros"))
output_table = dbutils.widgets.get("output_table")


bronze_table = "innovation_dev.bronze.radiologia_laudos_extraidos"

df = spark.table(bronze_table)

if data_inicio:
    df = df.filter(col("tms_procedimento_realizado") >= data_inicio)

if data_fim:
    df = df.filter(col("tms_procedimento_realizado") < data_fim)


df = df.filter(col("ds_laudo_medico").isNotNull())

if limit_registros > 0:
    df = df.limit(limit_registros)


pdf = df.select("accession_number", "ds_laudo_medico").toPandas()


structurer = RadiologyReportStructurer(
    api_key=None,
    model_id="databricks-gpt-oss-120b",
    temperature=0.0,
)


result_rows = []

for row in pdf.itertuples(index=False):
    texto = row.ds_laudo_medico
    if not isinstance(texto, str) or not texto.strip():
        continue
    texto_clean = preprocess_report(texto)
    r = structurer.predict(texto_clean)
    result_rows.append(
        {
            "accession_number": row.accession_number,
            "segments_json": json.dumps(r["segments"], ensure_ascii=False),
            "annotated_document_json": json.dumps(
                r["annotated_document_json"], ensure_ascii=False
            ),
            "text_formatado": r["text"],
            "raw_prompt": r["raw_prompt"],
            "modelo": structurer.model_id,
            "temperatura": float(structurer.temperature),
            "tms_carga": datetime.utcnow(),
        }
    )


if result_rows:
    df_out = spark.createDataFrame(result_rows)
    if spark.catalog.tableExists(output_table):
        df_out.write.format("delta").mode("append").saveAsTable(output_table)
    else:
        df_out.write.format("delta").mode("overwrite").saveAsTable(output_table)

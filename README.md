# Radiologia – Laudos

Aplicação Streamlit para organizar o download e a preparação de laudos provenientes do lake Oracle, consolidando os dados em uma tabela Delta (camada Gold) com as colunas `NM_PROCEDIMENTO`, `CD_PROCEDIMENTO`, `MODALIDADE` e `DESCRICAO_1` … `DESCRICAO_7`.

O app consome o arquivo `procedimentos.csv` (delimitado por `;`), filtra modalidades específicas (inicialmente **TC** e **ANGIOTC**), gera a lista única das descrições e oferece um template de `CREATE TABLE` pronto para ser executado no Lakehouse.

## Estrutura

```
radiologia-laudos/
├── README.md
└── app/
    ├── app.py
    ├── app.yaml
    └── requirements.txt
```

## Como executar localmente

```bash
cd radiologia-laudos/app
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

O app tenta carregar automaticamente `../procedimentos.csv`. Caso o arquivo esteja em outro caminho, utilize o uploader na interface.

## Publicação (Databricks Apps)

1. Faça upload desta pasta para o workspace.
2. Crie um App apontando para `app/app.py` (utilize `app/app.yaml` como blueprint).
3. Conceda permissões ao SQL Warehouse e ao diretório Delta/Lakehouse onde a tabela será gravada.

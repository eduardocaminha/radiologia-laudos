"""Provider custom do LangExtract para Databricks Model Serving (gpt-oss-120b).

Este módulo define um provider de LLM que integra o LangExtract diretamente
com um endpoint de Model Serving do Databricks, usando o SDK oficial
(`databricks-sdk`).

Ele é registrado no roteador interno do LangExtract com o padrão de modelo
`^databricks-gpt-oss-120b$`, permitindo que chamadas com
`model_id="databricks-gpt-oss-120b"` utilizem automaticamente este provider.

Dependências (apenas em runtime dentro do Databricks):
- databricks-sdk

Nenhuma dependência Databricks é importada em tempo de import do módulo para
não quebrar ambientes locais fora do cluster.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from typing import Any

from langextract.core import base_model, types
from langextract.providers import router


def _call_databricks_endpoint(
    prompts: Sequence[str],
    endpoint: str,
    temperature: float | None,
    max_tokens: int | None,
) -> list[list[types.ScoredOutput]]:
    """Chama o endpoint de Model Serving do Databricks para um batch de prompts.

    Esta função é isolada para permitir import lazy do `databricks-sdk` apenas
    em runtime dentro do Databricks.
    """

    try:
        from databricks.sdk import WorkspaceClient
        from databricks.sdk.service.serving import ChatMessage, ChatMessageRole
    except Exception as e:  # pragma: no cover - depende de ambiente Databricks
        raise RuntimeError(
            "databricks-sdk não está disponível no ambiente atual. "
            "Instale `databricks-sdk` ou execute este código dentro de um "
            "cluster Databricks."
        ) from e

    w = WorkspaceClient()

    resultados: list[list[types.ScoredOutput]] = []

    for prompt in prompts:
        response = w.serving_endpoints.query(
            name=endpoint,
            messages=[
                ChatMessage(role=ChatMessageRole.USER, content=prompt),
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )

        message = response.choices[0].message
        content = getattr(message, "content", message)

        # Normalizar diferentes formatos de retorno do SDK
        if isinstance(content, list):
            parts: list[str] = []
            for part in content:
                if hasattr(part, "text"):
                    parts.append(part.text or "")
                elif isinstance(part, dict):
                    parts.append(str(part.get("text", "")))
                else:
                    parts.append(str(part))
            text = "\n".join(p for p in parts if p)
        elif isinstance(content, str):
            text = content
        else:
            text = str(content)

        resultados.append([types.ScoredOutput(score=None, output=text)])

    return resultados


@router.register(r"^databricks-gpt-oss-120b$", priority=100)
class DatabricksGPTOSSLanguageModel(base_model.BaseLanguageModel):
    """Provider LangExtract para o endpoint Databricks `databricks-gpt-oss-120b`.

    Este provider implementa a interface `BaseLanguageModel` do LangExtract e
    usa o SDK Databricks para chamar um endpoint de Model Serving em batch.

    Parâmetros aceitos via factory/ModelConfig (provider_kwargs):
    - model_id: string do modelo (default "databricks-gpt-oss-120b")
    - endpoint: nome do endpoint de Serving no Databricks (default = model_id)
    - temperature: temperatura de amostragem (default 0.0)
    - max_tokens: limite de tokens de saída (default 2048)
    """

    def __init__(
        self,
        model_id: str | None = None,
        endpoint: str | None = None,
        temperature: float | None = 0.0,
        max_tokens: int | None = 2048,
        **kwargs: Any,
    ) -> None:
        # kwargs adicionais (como constraint, format_type, etc.) são tratados
        # pela superclasse e armazenados em _extra_kwargs.
        super().__init__(**kwargs)

        self.model_id = model_id or "databricks-gpt-oss-120b"
        self.endpoint = endpoint or self.model_id
        self.temperature = temperature
        self.max_tokens = max_tokens

    @classmethod
    def get_model_patterns(cls) -> tuple[str, ...]:  # pragma: no cover - usado por plugins
        """Padrões de modelo compatíveis com este provider.

        Mantido para compatibilidade com o mecanismo de plugins, embora aqui
        usemos o registro direto via decorator.
        """

        return (r"^databricks-gpt-oss-120b$",)

    def infer(
        self, batch_prompts: Sequence[str], **kwargs: Any
    ) -> Iterator[Sequence[types.ScoredOutput]]:
        """Executa inferência para um batch de prompts.

        Args:
            batch_prompts: lista de prompts de entrada.
            **kwargs: parâmetros opcionais (ex.: temperature, max_tokens,
                endpoint) que podem sobrescrever os defaults.

        Returns:
            Iterador de sequências de `ScoredOutput`, uma lista por prompt.
        """

        # Mescla kwargs de runtime com os armazenados na inicialização.
        merged = self.merge_kwargs(kwargs)

        endpoint = merged.get("endpoint", self.endpoint)
        temperature = merged.get("temperature", self.temperature)
        max_tokens = merged.get("max_tokens", self.max_tokens)

        resultados = _call_databricks_endpoint(
            prompts=batch_prompts,
            endpoint=endpoint,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        for outputs in resultados:
            yield outputs

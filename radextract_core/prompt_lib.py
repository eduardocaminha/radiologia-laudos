"""Utilitários de processamento para prompts de estruturação de laudos.

Este módulo fornece funções auxiliares para processar e formatar prompts
usados no sistema LangExtract para estruturação de laudos radiológicos.
"""

import dataclasses
import json
from typing import Optional

from langextract.data import ExampleData
from langextract.data_lib import enum_asdict_factory

from .prompt_instruction import PROMPT_INSTRUCTION


def clean_dict(obj):
    """Removes null values and empty objects/lists from dictionary recursively.

    This function recursively traverses a dictionary or list structure
    and removes any keys with null values, empty dictionaries, or empty
    lists to create cleaner JSON output for the prompt examples.

    Args:
        obj: The object to clean (dict, list, or primitive value).

    Returns:
        The cleaned object with null/empty values removed.
    """
    if isinstance(obj, dict):
        cleaned = {}
        for key, value in obj.items():
            cleaned_value = clean_dict(value)
            # Only include non-null, non-empty values
            if (
                cleaned_value is not None
                and cleaned_value != {}
                and cleaned_value != []
            ):
                cleaned[key] = cleaned_value
        return cleaned
    elif isinstance(obj, list):
        return [clean_dict(item) for item in obj if clean_dict(item) is not None]
    else:
        return obj


def generate_markdown_prompt(
    examples: list[ExampleData], input_text: Optional[str] = None
) -> str:
    """Generate markdown prompt with examples using LangExtract's enum_asdict_factory.

    Args:
        examples: List of ExampleData objects for few-shot learning
        input_text: Optional input text to include in inference example

    Returns:
        Formatted markdown string containing the complete prompt
    """
    examples_list = []

    for i, example in enumerate(examples, 1):
        example_dict = dataclasses.asdict(example, dict_factory=enum_asdict_factory)

        # Clean up null values and empty objects
        cleaned_extractions = clean_dict({"extractions": example_dict["extractions"]})
        json_output = json.dumps(cleaned_extractions, indent=2)

        example_section = f"""## Example {i}

**Input Text:**
```
{example.text}
```

**Expected Output:**
```json
{json_output}
```"""
        examples_list.append(example_section)

    examples_formatted = "\n\n---\n\n".join(examples_list)

    # Format inference section if input text provided
    inference_section = ""
    if input_text:
        inference_section = f"""

## Inference Example:

**Input Text:**
```
{input_text}
```

**Expected Output:**
"""

    return PROMPT_INSTRUCTION.format(
        examples=examples_formatted, inference_section=inference_section
    )

"""Utilitários de pré-processamento de texto para laudos radiológicos.

Este módulo fornece funções para pré-processar e sanitizar o texto de laudos
radiológicos antes de ser processado pelo sistema LangExtract. Inclui operações
como normalização de espaços em branco, remoção de caracteres inválidos e
limpeza estrutural básica para melhorar a robustez e a consistência do modelo.

Exemplo de uso típico:

    from sanitize import preprocess_report
    
    texto_limpo = preprocess_report(relatorio_bruto)
"""

from __future__ import annotations

import re

import ftfy

_TRANSLATE = str.maketrans(
    {
        0x2022: "*",
        0x25CF: "*",
        0x27A1: "->",
        0xF0E0: "->",
        0x2192: "->",
        0x2190: "<-",
        0x00D7: "x",
        0x2191: "up",
        0x2642: "male",
        0x2640: "female",
        0x2010: "-",
        0x2013: "-",
        0x2014: "-",
        0x00A0: " ",
    }
)

_WS = re.compile(r"[ \t]+")
_BLANKS = re.compile(r"\n\s*\n\s*\n+")

# Structure normalization patterns
_BEGIN = re.compile(r"---\s*BEGIN [^-]+---\n*", re.I)
_END = re.compile(r"\n*---\s*END [^-]+---\s*", re.I)
_HEADER = re.compile(r"\*{3}\s*([^*]+?)\s*\*{3}", re.I)
_BULLET_HDR = re.compile(r"^[ \t]*[\*\u2022\u25CF-]+\s*", re.M)
_ENUM = re.compile(r"^[ \t]*(\d+)[\)\.][ \t]+", re.M)


def sanitize_text(text: str) -> str:
    """Sanitizes Unicode characters and normalizes whitespace.

    Applies ftfy text repair, translates problematic Unicode symbols to ASCII
    equivalents, normalizes whitespace, and removes excessive blank lines.

    Args:
        text: The input text to sanitize.

    Returns:
        Sanitized text with Unicode issues resolved and whitespace normalized.
    """
    out = ftfy.fix_text(text, remove_control_chars=True, normalization="NFC")
    out = out.translate(_TRANSLATE)
    out = _WS.sub(" ", out)
    out = out.replace("\r\n", "\n").replace("\r", "\n")
    out = _BLANKS.sub("\n\n", out)
    return out.strip()


def normalize_structure(text: str) -> str:
    """Normalizes structural elements in radiology reports.

    Removes report wrappers, converts asterisk headers to colon format,
    removes bullet prefixes, and standardizes enumerations.

    Args:
        text: The input text to normalize.

    Returns:
        Text with structural elements normalized for consistent formatting.
    """
    text = _BEGIN.sub("", text)
    text = _END.sub("", text)
    text = _HEADER.sub(lambda m: f"{m.group(1).strip()}:", text)
    text = _BULLET_HDR.sub("", text)
    text = _ENUM.sub(lambda m: f"{m.group(1)}. ", text)
    return text.strip()


def preprocess_report(raw: str) -> str:
    """Preprocesses radiology reports with sanitization and normalization.

    Combines Unicode sanitization and structural normalization to prepare
    radiology reports for downstream processing. This is the main entry point
    for text preprocessing.

    Args:
        raw: The raw radiology report text.

    Returns:
        Preprocessed text ready for structured extraction.
    """
    return normalize_structure(sanitize_text(raw))

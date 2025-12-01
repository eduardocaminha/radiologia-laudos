"""Funcionalidade principal de estruturação de laudos radiológicos usando LangExtract.

Este módulo fornece a classe RadiologyReportStructurer, que processa laudos
radiológicos brutos e os converte em segmentos estruturados categorizados como
seções de prefixo, corpo ou sufixo, com anotações de significância clínica
(normal, minor, significant).

A estruturação usa LangExtract com prompting guiado por exemplos para extrair
segmentos com intervalos de caracteres, permitindo funcionalidade de realce ao
passar o mouse no frontend.

Integração backend-frontend:
- O backend gera segmentos com intervalos de caracteres (startPos/endPos)
- O frontend cria spans interativas que destacam o trecho correspondente do
  texto de entrada ao passar o mouse
- Os níveis de significância controlam o estilo CSS para diferenciação visual
- Os tipos de segmento organizam o conteúdo em seções estruturadas
  (EXAMINATION, FINDINGS, IMPRESSION)

Exemplo de uso:

    structurer = RadiologyReportStructurer(
        api_key="sua_api_key_aqui",
        model_id="gemini-2.5-flash"
    )
    result = structurer.predict("ACHADOS: Tomografia de tórax normal...")
"""

import collections
import dataclasses
import itertools
from enum import Enum
from functools import wraps
from typing import Any, TypedDict

import langextract as lx
import langextract.data

from . import prompt_instruction
from . import prompt_lib
from . import report_examples


class FrontendIntervalDict(TypedDict):
    """Character interval for frontend with startPos and endPos."""

    startPos: int
    endPos: int


class SegmentDict(TypedDict):
    """Segment dictionary for JSON response."""

    type: str
    label: str | None
    content: str
    intervals: list[FrontendIntervalDict]
    significance: str | None


class SerializedExtractionDict(TypedDict):
    """Serialized extraction for JSON response."""

    extraction_text: str | None
    extraction_class: str | None
    attributes: dict[str, str] | None
    char_interval: dict[str, int | None] | None
    alignment_status: str | None


class ResponseDict(TypedDict):
    """Complete response dictionary structure."""

    segments: list[SegmentDict]
    annotated_document_json: dict[str, Any]
    text: str
    raw_prompt: str


FINDINGS_HEADER = "FINDINGS:"
IMPRESSION_HEADER = "IMPRESSION:"
EXAMINATION_HEADER = "EXAMINATION:"
SECTION_ATTRIBUTE_KEY = "section"
START_POSITION = "startPos"
END_POSITION = "endPos"

EXAM_PREFIXES = ("EXAMINATION:", "EXAM:", "STUDY:")

EXAMINATION_LABEL = "examination"
PREFIX_LABEL = "prefix"

SIGNIFICANCE_NORMAL = "normal"
SIGNIFICANCE_MINOR = "minor"
SIGNIFICANCE_SIGNIFICANT = "significant"
SIGNIFICANCE_NOT_APPLICABLE = "not_applicable"


def _initialize_langextract_patches():
    """Initialize LangExtract patches for proper alignment behavior.

    This function applies necessary patches to LangExtract's Resolver.align method to force accept_match_lesser=False and set fuzzy_alignment_threshold to 0.50. This should be called before using LangExtract functionality.

    Note: This is a temporary workaround until LangExtract exposes
    accept_match_lesser and fuzzy_alignment_threshold parameters via its public API.
    """
    # Store original method
    original_align = lx.resolver.Resolver.align

    @wraps(original_align)
    def _align_patched(self, *args, **kwargs):
        # Set default if not explicitly provided
        kwargs.setdefault("accept_match_lesser", False)
        # Set fuzzy matching threshold to 0.50
        kwargs.setdefault("fuzzy_alignment_threshold", 0.50)
        return original_align(self, *args, **kwargs)

    # Apply the patch
    lx.resolver.Resolver.align = _align_patched


class ReportSectionType(Enum):
    """Enum representing sections of a radiology report with their extraction class names."""

    PREFIX = "findings_prefix"
    BODY = "findings_body"
    SUFFIX = "findings_suffix"

    @property
    def display_name(self) -> str:
        """Returns the lowercase section type name for display purposes."""
        return self.name.lower()


@dataclasses.dataclass
class Segment:
    """Represents a single merged segment of text in the final structured report.

    Attributes:
        type: The section type (prefix, body, or suffix).
        label: Optional section label for organization.
        content: The text content of this segment.
        intervals: List of character position intervals.
        significance: Optional clinical significance indicator.
    """

    type: ReportSectionType
    label: str | None
    content: str
    intervals: list[FrontendIntervalDict]
    significance: str | None = None

    def to_dict(self) -> SegmentDict:
        """Converts the segment to a dictionary representation.

        Returns:
            A dictionary containing all segment data with type as display name.
        """
        return SegmentDict(
            type=self.type.display_name,
            label=self.label,
            content=self.content,
            intervals=self.intervals,
            significance=self.significance,
        )


class RadiologyReportStructurer:
    """Structures radiology reports using LangExtract and large language models.

    This class processes raw radiology report text and converts it
    into structured segments categorized as prefix, body, or suffix
    sections with appropriate labeling and clinical significance annotations.
    """

    api_key: str | None
    model_id: str
    temperature: float
    examples: list[langextract.data.ExampleData]
    _patches_initialized: bool

    def __init__(
        self,
        api_key: str | None = None,
        model_id: str = "gemini-2.5-flash",
        temperature: float = 0.0,
    ):
        """Initializes the RadiologyReportStructurer.

        Args:
            api_key: API key for the language model service.
            model_id: Identifier for the specific model to use.
            temperature: Sampling temperature for model generation.
        """
        self.api_key = api_key
        self.model_id = model_id
        self.temperature = temperature
        self.examples = report_examples.get_examples_for_model()
        self._patches_initialized = False

    def _ensure_patches_initialized(self):
        """Ensure LangExtract patches are initialized before use."""
        if not self._patches_initialized:
            _initialize_langextract_patches()
            self._patches_initialized = True

    def _generate_formatted_prompt_with_examples(
        self, input_text: str | None = None
    ) -> str:
        """Generates a comprehensive, markdown-formatted prompt including examples.

        Args:
            input_text: Optional input text to include in the prompt display.

        Returns:
            A markdown-formatted string containing the full prompt and examples.
        """
        return prompt_lib.generate_markdown_prompt(self.examples, input_text)

    def predict(self, report_text: str, max_char_buffer: int = 2000) -> ResponseDict:
        """Processes a radiology report text into structured format.

        Takes raw radiology report text and uses LangExtract with example-guided
        prompting to extract structured segments with character intervals and
        clinical significance annotations.

        Args:
            report_text: Raw radiology report text to be processed.
            max_char_buffer: Maximum character buffer size for processing.

        Returns:
            A dictionary containing:
                - segments: List of structured report segments
                - annotated_document_json: Raw extraction results
                - text: Formatted text representation

        Raises:
            ValueError: If report_text is empty or whitespace-only.
        """
        if not report_text.strip():
            raise ValueError("Report text cannot be empty")

        try:
            result = self._perform_langextract(report_text, max_char_buffer)
            return self._build_response(result, report_text)
        except (ValueError, TypeError, AttributeError) as e:
            return ResponseDict(
                text=f"Error processing report: {str(e)}",
                segments=[],
                annotated_document_json={},
                raw_prompt="",
            )

    def _perform_langextract(
        self, report_text: str, max_char_buffer: int
    ) -> langextract.data.AnnotatedDocument:
        """Performs LangExtract processing on the input text.

        Args:
            report_text: Raw radiology report text to be processed.
            max_char_buffer: Maximum character buffer size for processing.

        Returns:
            LangExtract result object containing extractions.

        Raises:
            ValueError: If LangExtract processing fails.
            TypeError: If invalid parameters are provided.
        """
        self._ensure_patches_initialized()
        return lx.extract(
            text_or_documents=report_text,
            prompt_description=prompt_instruction.PROMPT_INSTRUCTION.split(
                "# Few-Shot Examples"
            )[0],
            examples=self.examples,
            model_id=self.model_id,
            api_key=self.api_key,
            max_char_buffer=max_char_buffer,
            temperature=self.temperature,
            # accept_match_lesser handled via monkey-patch
            # (Resolver.align patched at import time)
        )

    def _build_response(
        self, result: langextract.data.AnnotatedDocument, report_text: str
    ) -> ResponseDict:
        """Builds the final response dictionary from LangExtract results.

        Args:
            result: LangExtract result object containing extractions.
            report_text: Original input text for prompt generation.

        Returns:
            Dictionary containing structured segments and metadata.
        """
        segments = self._build_segments_from_langextract_result(result)
        organized_segments = self._organize_segments_by_label(segments)

        response: ResponseDict = {
            "segments": [segment.to_dict() for segment in organized_segments],
            "annotated_document_json": self._serialize_extraction_results(result),
            "text": self._format_segments_to_text(organized_segments),
            "raw_prompt": self._generate_formatted_prompt_with_examples(report_text),
        }

        return response

    def _serialize_extraction_results(
        self, result: langextract.data.AnnotatedDocument
    ) -> dict[str, Any]:
        """Serializes LangExtract results for JSON response.

        Args:
            result: LangExtract result object containing extractions.

        Returns:
            Dictionary containing serialized extraction data or error information.
        """
        try:
            if not hasattr(result, "extractions"):
                return {"error": "No extractions found in result"}

            return {
                "extractions": [
                    self._serialize_single_extraction(extraction)
                    for extraction in result.extractions
                ]
            }
        except (AttributeError, TypeError, KeyError) as e:
            return {
                "error": "Failed to serialize extraction result",
                "error_message": str(e),
                "fallback_string": str(result),
            }

    def _serialize_single_extraction(
        self, extraction: langextract.data.Extraction
    ) -> SerializedExtractionDict:
        """Serializes a single extraction to dictionary format."""
        return {
            "extraction_text": extraction.extraction_text,
            "extraction_class": extraction.extraction_class,
            "attributes": extraction.attributes,
            "char_interval": self._extract_char_interval(extraction),
            "alignment_status": self._get_alignment_status_string(extraction),
        }

    def _get_alignment_status_string(
        self, extraction: langextract.data.Extraction
    ) -> str | None:
        """Extracts alignment status from extraction as string."""
        status = getattr(extraction, "alignment_status", None)
        return str(status) if status is not None else None

    def _build_segments_from_langextract_result(
        self, result: langextract.data.AnnotatedDocument
    ) -> list[Segment]:
        """Builds segments from LangExtract result data using one-segment-per-interval strategy.

        Creates exactly one segment per character interval to enable precise
        frontend hover-to-highlight functionality. Processes only
        langextract.data.Extraction objects for consistent typing.

        Args:
            result: LangExtract result object containing extractions.

        Returns:
            List of Segment objects optimized for frontend rendering and interaction.
        """
        segments_list = []

        for extraction in result.extractions:
            section_type = self._map_section(extraction.extraction_class)

            if section_type is None:
                continue

            section_label = self._determine_section_label(
                extraction.attributes, section_type
            )
            significance_val = self._extract_clinical_significance(
                extraction.attributes
            )
            intervals = self._get_intervals_from_extraction_dict(
                extraction, extraction.char_interval
            )

            segments_list.extend(
                self._create_segments_for_intervals(
                    section_type,
                    section_label,
                    extraction.extraction_text,
                    intervals,
                    significance_val,
                )
            )

        return segments_list

    def _determine_section_label(
        self,
        attributes: dict[str, str] | None,
        section_type: ReportSectionType,
    ) -> str:
        """Determines the appropriate section label for a segment."""
        if attributes and isinstance(attributes, dict):
            section_label = attributes.get(SECTION_ATTRIBUTE_KEY)
            if section_label:
                return section_label
        return section_type.display_name

    def _extract_clinical_significance(
        self, attributes: dict[str, str] | None
    ) -> str | None:
        """Extracts clinical significance from attributes safely."""
        if not attributes or not isinstance(attributes, dict):
            return None

        try:
            sig_raw = attributes.get("clinical_significance")
            if sig_raw is not None:
                return getattr(sig_raw, "value", str(sig_raw)).lower()
        except (AttributeError, TypeError):
            pass
        return None

    def _create_segments_for_intervals(
        self,
        section_type: ReportSectionType,
        section_label: str,
        content: str,
        intervals: list[FrontendIntervalDict],
        significance: str | None,
    ) -> list[Segment]:
        """Creates segment objects for the given intervals."""
        if not intervals:
            return [
                Segment(
                    type=section_type,
                    label=section_label,
                    content=content,
                    intervals=[],
                    significance=significance,
                )
            ]
        return [
            Segment(
                type=section_type,
                label=section_label,
                content=content,
                intervals=[interval],
                significance=significance,
            )
            for interval in intervals
        ]

    def _map_section(self, extraction_class: str) -> ReportSectionType | None:
        """Maps extraction class string to ReportSectionType enum."""
        extraction_class = extraction_class.lower().strip()

        for section_type in ReportSectionType:
            if section_type.value == extraction_class:
                return section_type

        return None

    def _get_intervals_from_extraction_dict(
        self,
        extraction: langextract.data.Extraction,
        char_interval: langextract.data.CharInterval | dict[str, int] | None = None,
    ) -> list[FrontendIntervalDict]:
        """Extracts character intervals from extraction data.

        Returns a list of interval dictionaries from the extraction's
        char_interval in the format expected by the frontend.

        Args:
            extraction: langextract.data.Extraction object containing interval data.
            char_interval: Optional override for character interval data.

        Returns:
            List of dictionaries with startPos and endPos keys.
        """
        interval_list = []
        try:
            char_interval = (
                char_interval if char_interval is not None else extraction.char_interval
            )

            if char_interval is not None:
                # Handle both dict and object formats for char_interval (langextract.data.CharInterval object or dict override)
                if isinstance(char_interval, dict):
                    start_pos = char_interval.get("start_pos")
                    end_pos = char_interval.get("end_pos")
                else:
                    start_pos = getattr(char_interval, "start_pos", None)
                    end_pos = getattr(char_interval, "end_pos", None)

                start_position, end_position = self._extract_positions(
                    start_pos, end_pos
                )
                if start_position is not None and end_position is not None:
                    interval_list.append(
                        FrontendIntervalDict(
                            startPos=start_position, endPos=end_position
                        )
                    )
        except Exception:
            pass
        return interval_list

    def _extract_positions(self, start_obj, end_obj) -> tuple[int | None, int | None]:
        """Extracts position integers from potentially complex objects.

        Handles possible slice objects or direct integers for start and end positions.
        """
        if hasattr(start_obj, "start"):
            start_obj = start_obj.start
        if hasattr(end_obj, "stop"):
            end_obj = end_obj.stop

        try:
            start_position = int(start_obj) if start_obj is not None else None
            end_position = int(end_obj) if end_obj is not None else None
            if start_position is not None and end_position is not None:
                return (start_position, end_position)
        except Exception:
            pass
        return (None, None)

    def _extract_char_interval(
        self, extraction: langextract.data.Extraction
    ) -> dict[str, int | None] | None:
        """Extracts character interval information from an extraction."""
        char_interval = extraction.char_interval
        if char_interval is None:
            return None

        return {
            "start_pos": getattr(char_interval, "start_pos", None),
            "end_pos": getattr(char_interval, "end_pos", None),
        }

    def _format_segments_to_text(self, segments: list[Segment]) -> str:
        """Formats segments into a readable text representation.

        Merges segments with the same label into coherent paragraphs
        while preserving the original order of labels as they appear
        in the document.
        """
        grouped = self._group_segments_by_type_and_label(segments)
        formatted_parts: list[str] = []

        self._render_prefix_sections(grouped, segments, formatted_parts)
        self._render_body_sections(grouped, formatted_parts)
        self._render_suffix_sections(grouped, formatted_parts)

        return "\n".join(formatted_parts).rstrip()

    def _group_segments_by_type_and_label(
        self, segments: list[Segment]
    ) -> collections.OrderedDict[tuple[ReportSectionType, str | None], list[str]]:
        """Groups segments by (type, label) preserving insertion order.

        Creates a dictionary keyed by (ReportSectionType, label) tuples
        that maintains the order segments are first encountered.
        Deduplicates content within each group while preserving
        the original sequence of unique content items.

        Args:
            segments: List of Segment objects to group.

        Returns:
            OrderedDict mapping (type, label) tuples to lists of unique content strings.
        """
        grouped: collections.OrderedDict[
            tuple[ReportSectionType, str | None], list[str]
        ] = collections.OrderedDict()
        for seg in segments:
            key = (seg.type, seg.label)
            grouped.setdefault(key, [])
            if seg.content not in grouped[key]:
                grouped[key].append(seg.content.strip())
        return grouped

    def _render_prefix_sections(
        self,
        grouped: collections.OrderedDict[
            tuple[ReportSectionType, str | None], list[str]
        ],
        segments: list[Segment],
        formatted_parts: list[str],
    ) -> None:
        """Renders PREFIX sections with appropriate headers."""
        add = formatted_parts.append

        def blank() -> None:
            formatted_parts.append("")

        structured_prefix_exists = any(
            seg.type == ReportSectionType.PREFIX
            and seg.label
            and seg.label.lower() != PREFIX_LABEL
            for seg in segments
        )

        if structured_prefix_exists:
            for (stype, label), contents in grouped.items():
                if stype is not ReportSectionType.PREFIX:
                    continue

                if label and label.lower() == EXAMINATION_LABEL:
                    add(EXAMINATION_HEADER)
                    blank()
                    for c in contents:
                        stripped = self._strip_exam_prefix(c)
                        if stripped:
                            add(stripped)
                    blank()
                elif label and label.lower() != PREFIX_LABEL:
                    for c in contents:
                        if c:
                            add(c)
                    blank()
                else:
                    for c in contents:
                        if c:
                            add(c)
                    blank()
        else:
            plain_prefix = []
            for (stype, _), contents in grouped.items():
                if stype is ReportSectionType.PREFIX:
                    plain_prefix.extend(contents)
            if plain_prefix:
                add("\n\n".join(plain_prefix).rstrip())

    def _render_body_sections(
        self,
        grouped: collections.OrderedDict[
            tuple[ReportSectionType, str | None], list[str]
        ],
        formatted_parts: list[str],
    ) -> None:
        """Renders BODY (FINDINGS) sections."""
        add = formatted_parts.append

        def blank() -> None:
            formatted_parts.append("")

        body_items = [
            (k, v) for k, v in grouped.items() if k[0] is ReportSectionType.BODY
        ]
        if body_items:
            if formatted_parts:
                blank()
            add(FINDINGS_HEADER)
            blank()
            for (_, label), contents in body_items:
                combined = " ".join(contents).strip()
                if combined:
                    add(f"{label}: {combined}")
                    blank()

    def _render_suffix_sections(
        self,
        grouped: collections.OrderedDict[
            tuple[ReportSectionType, str | None], list[str]
        ],
        formatted_parts: list[str],
    ) -> None:
        """Renders SUFFIX (IMPRESSION) sections."""
        add = formatted_parts.append

        def blank() -> None:
            formatted_parts.append("")

        suffix_items = [
            (k, v) for k, v in grouped.items() if k[0] is ReportSectionType.SUFFIX
        ]
        if suffix_items:
            if formatted_parts and formatted_parts[-1].strip():
                blank()
            add(IMPRESSION_HEADER)
            blank()
            suffix_block = "\n".join(
                itertools.chain.from_iterable(v for _, v in suffix_items)
            ).rstrip()
            add(suffix_block)

    def _organize_segments_by_label(self, segments: list[Segment]) -> list[Segment]:
        """Organizes segments into the correct order for presentation.

        Orders segments by section type (prefix → body → suffix), groups
        body segments by label while preserving original appearance order,
        and maintains extraction order for segments with the same label.

        Args:
            segments: List of Segment objects to organize.

        Returns:
            List of segments in proper presentation order.
        """
        prefix_segments = [
            segment for segment in segments if segment.type == ReportSectionType.PREFIX
        ]
        body_segments = [
            segment for segment in segments if segment.type == ReportSectionType.BODY
        ]
        suffix_segments = [
            segment for segment in segments if segment.type == ReportSectionType.SUFFIX
        ]

        body_segments_by_label: dict[str, list[Segment]] = {}
        labels_in_order: list[str] = []

        for segment in body_segments:
            if segment.label:
                if segment.label not in body_segments_by_label:
                    body_segments_by_label[segment.label] = []
                    labels_in_order.append(segment.label)
                body_segments_by_label[segment.label].append(segment)

        organized_segments = []
        organized_segments.extend(prefix_segments)

        for label in labels_in_order:
            organized_segments.extend(body_segments_by_label[label])

        organized_segments.extend(suffix_segments)

        return organized_segments

    def _strip_exam_prefix(self, text: str) -> str:
        """Removes common examination prefixes from a string."""
        upper = text.upper()
        for prefix in EXAM_PREFIXES:
            if upper.startswith(prefix):
                return text[len(prefix) :].lstrip()
        return text.strip()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Оркестратор пайплайна построения лекции из PDF.
"""

import logging
from pathlib import Path
from typing import List, Optional

from .models.lecture_model import DocumentBlock, DocumentSection
from .stage2_layout import extract_layout, normalize_headers, build_sections, flatten_paragraphs
from .stage3_images.image_linker import ImageLinker
from .stage5_semantics.semantic_segmenter import segment_by_llm
from .stage6_slides.slide_builder import build_slides_heuristic, sections_to_lecture
from .pipeline_csv import (
    export_stage_1_layout_parsing,
    export_stage_2_block_normalization,
    export_stage_3_header_detection,
    export_stage_4_image_linking,
    export_stage_5_slide_builder,
    export_stage_6_lecture,
)

from .models import Lecture

PROCESS_RESULT_DIR = Path(__file__).parent / "process_result"


def build_lecture(
    blocks: List[DocumentBlock],
    pdf_paths: List[Path],
    parser_temp_dir: Optional[Path] = None,
    output_images_dir: Optional[Path] = None,
    process_result_dir: Optional[Path] = None,
    pdf_selected_pages: Optional[List[Optional[List[int]]]] = None,
) -> Lecture:
    """
    Строит модель лекции из DocumentBlock и PDF.

    Args:
        blocks: Список DocumentBlock от LayoutParser (TEXT + IMAGE, используются IMAGE для image linking)
        pdf_paths: Пути к PDF для layout extraction через unstructured
        parser_temp_dir: Временная директория парсера (для изображений)
        pdf_selected_pages: selected_pages для каждого PDF (None = все страницы)

    Returns:
        Lecture (совместим со scorm_builder)
    """
    if not pdf_paths:
        raise ValueError("pdf_paths обязателен для layout extraction (unstructured)")

    blocks = blocks or []
    csv_dir = process_result_dir if process_result_dir is not None else PROCESS_RESULT_DIR
    csv_dir.mkdir(parents=True, exist_ok=True)

    export_stage_1_layout_parsing(blocks or [], csv_dir)

    paragraphs: List = []
    sel_pages = pdf_selected_pages or [None] * max(len(pdf_paths), 1)
    for idx, pdf_path in enumerate(pdf_paths):
        sp = sel_pages[idx] if idx < len(sel_pages) else None
        paras = extract_layout(pdf_path, selected_pages=sp)
        paragraphs.extend(paras)

    if not paragraphs:
        raise ValueError("Layout extraction не вернул элементов. Проверьте PDF и наличие unstructured[pdf].")

    export_stage_2_block_normalization(paragraphs, csv_dir)
    export_stage_3_header_detection(paragraphs, csv_dir)

    paragraphs = normalize_headers(paragraphs)

    header_count = sum(1 for p in paragraphs if getattr(p, "is_header", False) or getattr(p, "header_level", 0) > 0)
    text_count = sum(1 for p in paragraphs if getattr(p, "header_level", 0) == 0)
    image_count = sum(1 for b in blocks if b.type == "IMAGE")
    logging.info(
        "Layout extraction (unstructured): элементов %d (заголовков %d, текстовых %d, изображений %d)",
        len(paragraphs),
        header_count,
        text_count,
        image_count,
    )

    document_sections = build_sections(paragraphs)
    flat_paragraphs = flatten_paragraphs(document_sections)

    linker = ImageLinker()
    linked_images = linker.link(blocks, flat_paragraphs)
    export_stage_4_image_linking(flat_paragraphs, linked_images, csv_dir)

    _assign_images_to_sections(document_sections, linked_images)

    language = _detect_language(flat_paragraphs)
    sections = segment_by_llm(document_sections, linked_images, language=language)
    if sections is None:
        logging.warning(
            "LLM недоступна или произошла ошибка — переход на fallback-режим (эвристики)",
        )
        sections = build_slides_heuristic(flat_paragraphs, linked_images)
    export_stage_5_slide_builder(sections, csv_dir)

    title = _extract_title(paragraphs, sections)
    description = _extract_description(paragraphs)
    keywords = _extract_keywords(paragraphs, sections)
    
    lecture = sections_to_lecture(sections, title=title, description=description, language=language)
    lecture.metadata["keywords"] = keywords
    export_stage_6_lecture(lecture, csv_dir)

    total_pages = lecture.get_total_pages()
    total_blocks = sum(
        len(p.content_blocks) for s in lecture.sections for p in s.pages
    )
    avg_blocks = total_blocks / total_pages if total_pages else 0
    logging.info(
        "Lecture pipeline: %d блоков → %d абзацев → %d изображений → %d разделов, %d страниц, ср. %.1f блоков/страницу",
        len(blocks),
        len(paragraphs),
        len(linked_images),
        len(sections),
        total_pages,
        avg_blocks,
    )
    return lecture


def _assign_images_to_sections(
    document_sections: List[DocumentSection],
    linked_images: List,
) -> None:
    """Добавляет LinkedImage в section.images по linked_paragraph_id или context_paragraph_ids."""
    para_to_section = {}
    for sec in document_sections:
        for p in sec.paragraphs:
            para_to_section[p.id] = sec
    for img in linked_images:
        ids_to_check = list(getattr(img, "context_paragraph_ids", []) or [])
        if getattr(img, "linked_paragraph_id", None) and img.linked_paragraph_id not in ids_to_check:
            ids_to_check.insert(0, img.linked_paragraph_id)
        if not ids_to_check and getattr(img, "linked_paragraph_id", None):
            ids_to_check = [img.linked_paragraph_id]
        for pid in ids_to_check:
            sec = para_to_section.get(pid)
            if sec and img not in sec.images:
                sec.images.append(img)
                break


def _extract_title(paragraphs: List, sections: List) -> str:
    """Первый H1 или заголовок первого слайда."""
    for p in paragraphs:
        if getattr(p, "header_level", 0) == 1:
            return p.text.strip()[:100]
    for sec in sections:
        if sec.slides and sec.slides[0].title:
            return sec.slides[0].title[:100]
    for p in paragraphs:
        if p.text and len(p.text) < 200:
            return p.text.strip()[:100]
    return "Лекция"


def _extract_description(paragraphs: List) -> str:
    """Первые 1–2 не-заголовочных абзаца."""
    parts = []
    for p in paragraphs:
        if getattr(p, "header_level", 0) > 0:
            continue
        if p.text and len(p.text) >= 10:
            parts.append(p.text.strip())
            if len(parts) >= 2 or (parts and len(" ".join(parts)) > 500):
                break
    return " ".join(parts)[:500] if parts else ""


def _detect_language(paragraphs: List) -> str:
    """Определение языка по кириллице/латинице."""
    text = " ".join(p.text for p in paragraphs if p.text)[:500]
    cyrillic = sum(1 for c in text if "\u0400" <= c <= "\u04FF")
    latin = sum(1 for c in text if c.isalpha() and ord(c) < 128)
    return "ru" if cyrillic > latin * 0.3 else "en"


def _extract_keywords(paragraphs: List, sections: List) -> List[str]:
    """Ключевые слова из заголовков H1."""
    kw = []
    for p in paragraphs:
        if getattr(p, "header_level", 0) == 1:
            kw.append(p.text.strip()[:50])
    for sec in sections:
        if sec.slides and sec.slides[0].title:
            kw.append(sec.slides[0].title[:50])
    return kw[:10]

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Оркестратор пайплайна построения лекции из PDF.

Пайплайн: Layout Parsing → Block Normalization → Header Detection → Image Linking → Slide Builder → Lecture
"""

import logging
import statistics
from pathlib import Path
from typing import List, Optional

from .models.lecture_model import DocumentBlock
from .layout.block_normalizer import BlockNormalizer, detect_headers
from .images.image_linker import ImageLinker
from .slides.slide_builder import build_slides_heuristic, sections_to_lecture
from .semantics.semantic_segmenter import segment_by_llm

from .models import Lecture


def build_lecture(
    blocks: List[DocumentBlock],
    parser_temp_dir: Optional[Path] = None,
    output_images_dir: Optional[Path] = None,  # legacy, не используется
) -> Lecture:
    """
    Строит модель лекции из DocumentBlock.
    
    Args:
        blocks: Список DocumentBlock от LayoutParser
        parser_temp_dir: Временная директория парсера (для изображений)
        output_images_dir: Deprecated, игнорируется
    
    Returns:
        Lecture (совместим со scorm_builder)
    """
    if not blocks:
        raise ValueError("Список блоков пуст")

    # 1. Normalize blocks (строки → абзацы)
    normalizer = BlockNormalizer()
    paragraphs = normalizer.normalize(blocks)
    
    # 2. Detect headers (H1, H2, H3)
    if paragraphs:
        font_sizes = [p.font_size for p in paragraphs]
        median_font = statistics.median(font_sizes)
        std_font = statistics.stdev(font_sizes) if len(font_sizes) > 1 else 0
        paragraphs = detect_headers(paragraphs, median_font, std_font)
    
    # 3. Link images
    linker = ImageLinker()
    linked_images = linker.link(blocks, paragraphs)

    # 4. Build slides: LLM при наличии ключа, иначе эвристики
    language = _detect_language(paragraphs)
    sections = segment_by_llm(paragraphs, linked_images, language=language)
    if sections is None:
        logging.warning(
            "LLM недоступна или произошла ошибка — переход на fallback-режим (эвристики)",
        )
        sections = build_slides_heuristic(paragraphs, linked_images)
    
    # 5. Extract metadata and convert to Lecture
    title = _extract_title(paragraphs, sections)
    description = _extract_description(paragraphs)
    keywords = _extract_keywords(paragraphs, sections)
    
    lecture = sections_to_lecture(sections, title=title, description=description, language=language)
    lecture.metadata["keywords"] = keywords

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

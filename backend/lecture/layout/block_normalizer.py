#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Нормализация блоков — объединение строк в абзацы, определение заголовков.

Пороги: indent_threshold=20px, paragraph_gap_threshold=15px.
Заголовки определяются по взвешенной комбинации признаков (H1, H2, H3).
"""

import logging
import statistics
import uuid
from typing import List, Tuple

from ..models.lecture_model import DocumentBlock, ParagraphBlock

INDENT_THRESHOLD = 20
PARAGRAPH_GAP_THRESHOLD = 15
HEADER_SCORE_THRESHOLD = 0.5


class BlockNormalizer:
    """Нормализатор блоков и детектор заголовков."""

    def __init__(
        self,
        indent_threshold: float = INDENT_THRESHOLD,
        paragraph_gap_threshold: float = PARAGRAPH_GAP_THRESHOLD,
        header_score_threshold: float = HEADER_SCORE_THRESHOLD,
    ):
        self.indent_threshold = indent_threshold
        self.paragraph_gap_threshold = paragraph_gap_threshold
        self.header_score_threshold = header_score_threshold

    def normalize(self, blocks: List[DocumentBlock]) -> List[ParagraphBlock]:
        """Объединяет текстовые DocumentBlock (строки) в ParagraphBlock (абзацы)."""
        text_blocks = [b for b in blocks if b.type == "TEXT" and b.text.strip()]
        if not text_blocks:
            return []
        paragraphs = self._merge_lines_to_paragraphs(text_blocks)
        logging.info("Block normalization: сформировано %d абзацев", len(paragraphs))
        return paragraphs

    def _merge_lines_to_paragraphs(self, lines: List[DocumentBlock]) -> List[ParagraphBlock]:
        """Объединяет строки в абзацы по критериям."""
        if not lines:
            return []
        paragraphs: List[ParagraphBlock] = []
        current_para_lines: List[DocumentBlock] = [lines[0]]

        for i in range(1, len(lines)):
            prev = lines[i - 1]
            curr = lines[i]
            prev_line = current_para_lines[-1]

            same_page = curr.page_number == prev_line.page_number
            x_diff = abs(curr.bbox[0] - prev_line.bbox[0])
            vertical_gap = curr.bbox[1] - prev_line.bbox[3] if curr.bbox and prev_line.bbox else 0
            font_diff = abs(curr.font_size - prev_line.font_size)
            same_bold = curr.is_bold == prev_line.is_bold

            should_merge = (
                same_page
                and x_diff < self.indent_threshold
                and 0 <= vertical_gap < self.paragraph_gap_threshold
                and font_diff < 2
                and same_bold
            )
            if should_merge:
                current_para_lines.append(curr)
            else:
                para = self._create_paragraph(current_para_lines)
                paragraphs.append(para)
                current_para_lines = [curr]

        if current_para_lines:
            para = self._create_paragraph(current_para_lines)
            paragraphs.append(para)
        return paragraphs

    def _create_paragraph(self, lines: List[DocumentBlock]) -> ParagraphBlock:
        """Создаёт ParagraphBlock из списка строк."""
        text = " ".join(l.text for l in lines)
        bboxes = [l.bbox for l in lines if l.bbox]
        if bboxes:
            x0 = min(b[0] for b in bboxes)
            y0 = min(b[1] for b in bboxes)
            x1 = max(b[2] for b in bboxes)
            y1 = max(b[3] for b in bboxes)
            bbox = (x0, y0, x1, y1)
        else:
            bbox = (0, 0, 0, 0)
        avg_font = statistics.mean(l.font_size for l in lines)
        is_bold = all(l.is_bold for l in lines)
        return ParagraphBlock(
            id=str(uuid.uuid4()),
            text=text,
            page_number=lines[0].page_number,
            bbox=bbox,
            font_size=avg_font,
            is_bold=is_bold,
            lines_count=len(lines),
            header_level=0,
        )


def normalize_blocks(blocks: List[DocumentBlock]) -> List[ParagraphBlock]:
    """Удобная функция: нормализует блоки в абзацы."""
    return BlockNormalizer().normalize(blocks)


SCIENTIFIC_HEADERS = (
    "введение", "методы", "результаты", "обсуждение", "заключение",
    "introduction", "methods", "results", "discussion", "conclusion",
)


def detect_headers(
    paragraphs: List[ParagraphBlock],
    median_font_size: float,
    std_font_size: float = 0,
) -> List[ParagraphBlock]:
    """
    Определяет заголовки (H1, H2, H3) по взвешенным признакам.
    
    Признаки:
    - короткий текст (< 100 символов, без точки в конце)
    - увеличенный вертикальный отступ сверху
    - крупный шрифт
    - жирный шрифт
    - центрирование (примерно по центру страницы — опционально)
    """
    if not paragraphs:
        return paragraphs
    font_sizes = [p.font_size for p in paragraphs]
    if median_font_size <= 0:
        median_font_size = statistics.median(font_sizes) or 12.0
    if std_font_size <= 0 and len(font_sizes) > 1:
        std_font_size = statistics.stdev(font_sizes)

    header_count = 0
    for i, p in enumerate(paragraphs):
        text = p.text.strip()
        t_lower = text.lower()[:80]
        if any(h in t_lower for h in SCIENTIFIC_HEADERS):
            p.header_level = 1
            header_count += 1
            continue
        score = 0.0
        if len(text) > 100 or text.endswith("."):
            continue
        if len(text) < 100 and not text.endswith("."):
            score += 0.2
        if p.font_size >= median_font_size * 1.2:
            score += 0.3
        elif p.font_size >= median_font_size * 1.1:
            score += 0.2
        if p.is_bold:
            score += 0.3
        if p.lines_count <= 2:
            score += 0.1
        vertical_gap = 0.0
        if i > 0 and paragraphs[i - 1].bbox and p.bbox:
            vertical_gap = p.bbox[1] - paragraphs[i - 1].bbox[3]
        if vertical_gap > 15:
            score += 0.2
        elif vertical_gap > 8:
            score += 0.1

        if score >= HEADER_SCORE_THRESHOLD:
            if p.font_size >= median_font_size * 1.5:
                p.header_level = 1
            elif p.font_size >= median_font_size * 1.2:
                p.header_level = 2
            else:
                p.header_level = 3
            header_count += 1

    logging.info("Header detection: найдено %d заголовков", header_count)
    return paragraphs

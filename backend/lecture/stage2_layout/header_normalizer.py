#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Финальная нормализация заголовков: продвижение пропущенных, понижение ложных.
"""

import logging
from typing import List, Optional

from ..models.lecture_model import ParagraphBlock

SHORT_TEXT_MAX_CHARS = 80
LONG_BLOCK_MIN_CHARS = 150
FONT_SIZE_TOLERANCE = 0.5
VERTICAL_GAP_INCREASE_RATIO = 1.3


def _median_font_size(paragraphs: List[ParagraphBlock], exclude_headers: bool = True) -> float:
    vals = [p.font_size for p in paragraphs if getattr(p, "header_level", 0) == 0 or not exclude_headers]
    if not vals:
        return 12.0
    sorted_vals = sorted(vals)
    mid = len(sorted_vals) // 2
    return sorted_vals[mid] if len(sorted_vals) % 2 else (sorted_vals[mid - 1] + sorted_vals[mid]) / 2


def _vertical_gap(prev: ParagraphBlock, curr: ParagraphBlock) -> Optional[float]:
    if prev.page_number != curr.page_number:
        return None
    p0, p1 = prev.bbox, curr.bbox
    if not p0 or not p1 or len(p0) < 4 or len(p1) < 4:
        return None
    return p1[1] - p0[3]


def _median_paragraph_gap(paragraphs: List[ParagraphBlock]) -> float:
    gaps: List[float] = []
    for i in range(1, len(paragraphs)):
        g = _vertical_gap(paragraphs[i - 1], paragraphs[i])
        if g is not None and g > 0:
            gaps.append(g)
    if not gaps:
        return 20.0
    sorted_gaps = sorted(gaps)
    mid = len(sorted_gaps) // 2
    return sorted_gaps[mid] if len(sorted_gaps) % 2 else (sorted_gaps[mid - 1] + sorted_gaps[mid]) / 2


def _promote_short_blocks_between_long(paragraphs: List[ParagraphBlock]) -> None:
    for i in range(1, len(paragraphs) - 1):
        p = paragraphs[i]
        if getattr(p, "header_level", 0) > 0:
            continue
        t = (p.text or "").strip()
        if not (0 < len(t) < SHORT_TEXT_MAX_CHARS and not t.endswith(".")):
            continue
        if _is_long(paragraphs[i - 1]) and _is_long(paragraphs[i + 1]):
            p.header_level = 1
            p.element_type = "header"
            p.is_header = True
            p.is_bold = True


def _is_long(p: ParagraphBlock) -> bool:
    return bool(p.text and len((p.text or "").strip()) >= LONG_BLOCK_MIN_CHARS)


def _demote_false_h2(paragraphs: List[ParagraphBlock]) -> None:
    median_font = _median_font_size(paragraphs)
    median_gap = _median_paragraph_gap(paragraphs)
    threshold = median_gap * VERTICAL_GAP_INCREASE_RATIO

    for i in range(len(paragraphs)):
        p = paragraphs[i]
        if getattr(p, "header_level", 0) != 2 or p.is_bold:
            continue
        if abs(p.font_size - median_font) > FONT_SIZE_TOLERANCE:
            continue

        prev = paragraphs[i - 1] if i > 0 else None
        nxt = paragraphs[i + 1] if i + 1 < len(paragraphs) else None
        if not (prev and getattr(prev, "header_level", 0) == 0 and nxt and getattr(nxt, "header_level", 0) == 0):
            continue

        gap_before = _vertical_gap(prev, p) if prev else None
        gap_after = _vertical_gap(p, nxt) if nxt else None
        if (gap_before is None or gap_before <= threshold) and (gap_after is None or gap_after <= threshold):
            p.header_level = 0
            p.element_type = "paragraph"
            p.is_header = False


def normalize_headers(paragraphs: List[ParagraphBlock]) -> List[ParagraphBlock]:
    if not paragraphs:
        return paragraphs
    _promote_short_blocks_between_long(paragraphs)
    _demote_false_h2(paragraphs)
    for p in paragraphs:
        p.is_header = getattr(p, "header_level", 0) > 0
    return paragraphs

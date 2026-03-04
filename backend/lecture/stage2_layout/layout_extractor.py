#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Извлечение структурированных элементов из PDF через unstructured.
"""

import os
os.environ.setdefault("NUMBA_DISABLE_JIT", "1")

import logging
import uuid
from pathlib import Path
from typing import List, Optional

from ..models.lecture_model import ParagraphBlock

TYPE_MAP = {
    "Title": "header",
    "NarrativeText": "paragraph",
    "ListItem": "paragraph",
    "FigureCaption": "caption",
    "Header": "header",
    "Footer": "paragraph",
}
DEFAULT_TYPE = "paragraph"


def extract_layout(
    pdf_path: Path,
    selected_pages: Optional[List[int]] = None,
) -> List[ParagraphBlock]:
    try:
        from unstructured.partition.pdf import partition_pdf
    except ImportError as e:
        logging.error("unstructured не установлен: %s. Установите: pip install 'unstructured[pdf]'", e)
        raise

    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF не найден: {pdf_path}")

    elements = partition_pdf(filename=str(path), include_page_breaks=True)
    paragraphs: List[ParagraphBlock] = []

    for el in elements:
        elem_type = str(getattr(el, "type", None) or type(el).__name__)
        text = (getattr(el, "text", None) or "").strip()
        if not text:
            continue

        internal_type = TYPE_MAP.get(elem_type, DEFAULT_TYPE)
        if internal_type == "paragraph" and elem_type == "Footer":
            continue

        metadata = getattr(el, "metadata", None)
        page_num = getattr(metadata, "page_number", None) if metadata else None
        if page_num is None and isinstance(metadata, dict):
            page_num = metadata.get("page_number", 1)
        if isinstance(page_num, (list, tuple)):
            page_num = page_num[0] if page_num else 1
        page_num = int(page_num) if page_num else 1
        if selected_pages and page_num not in selected_pages:
            continue

        element_type = "header" if internal_type == "header" else ("caption" if internal_type == "caption" else "paragraph")

        bbox = (0, 0, 0, 0)
        if hasattr(el, "metadata") and el.metadata:
            coords = getattr(el.metadata, "coordinates", None)
            if coords and hasattr(coords, "points"):
                pts = coords.points
                if pts and len(pts) >= 4:
                    xs = [p[0] for p in pts]
                    ys = [p[1] for p in pts]
                    bbox = (min(xs), min(ys), max(xs), max(ys))

        header_level = 1 if element_type == "header" else 0
        p = ParagraphBlock(
            id=str(uuid.uuid4()),
            text=text,
            page_number=int(page_num),
            bbox=bbox,
            font_size=12.0,
            is_bold=internal_type == "header",
            lines_count=1,
            header_level=header_level,
            element_type=element_type,
        )
        paragraphs.append(p)

    paragraphs = _assign_header_levels_by_position(paragraphs)
    for p in paragraphs:
        p.is_header = p.header_level > 0
    return paragraphs


def _assign_header_levels_by_position(paragraphs: List[ParagraphBlock]) -> List[ParagraphBlock]:
    header_indices = [i for i, p in enumerate(paragraphs) if p.element_type == "header"]
    if not header_indices:
        return paragraphs

    for j, idx in enumerate(header_indices):
        prev_idx = header_indices[j - 1] if j > 0 else -1
        has_text_between = any(
            paragraphs[k].element_type == "paragraph" or paragraphs[k].element_type == "caption"
            for k in range(prev_idx + 1, idx)
        )
        if j == 0 or has_text_between:
            paragraphs[idx].header_level = 1
        else:
            paragraphs[idx].header_level = 2

    return paragraphs

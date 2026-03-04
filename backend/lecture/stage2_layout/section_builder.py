#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Реконструкция структуры документа: ParagraphBlock[] → DocumentSection[].
"""

import logging
import uuid
from typing import List

from ..models.lecture_model import ParagraphBlock, DocumentSection


def build_sections(paragraphs: List[ParagraphBlock]) -> List[DocumentSection]:
    if not paragraphs:
        return []

    sections: List[DocumentSection] = []
    current: DocumentSection | None = None

    for p in paragraphs:
        is_section_header = getattr(p, "is_header", False) and getattr(p, "header_level", 0) == 1
        if is_section_header:
            current = DocumentSection(
                id=str(uuid.uuid4()),
                title=(p.text or "").strip(),
                paragraphs=[],
                images=[],
                page_numbers=[p.page_number],
            )
            sections.append(current)
        elif current is not None:
            current.paragraphs.append(p)
            if p.page_number not in current.page_numbers:
                current.page_numbers.append(p.page_number)
        else:
            current = DocumentSection(
                id=str(uuid.uuid4()),
                title="Введение",
                paragraphs=[p],
                images=[],
                page_numbers=[p.page_number],
            )
            sections.append(current)

    for sec in sections:
        sec.page_numbers = sorted(set(sec.page_numbers))

    header_count = sum(1 for p in paragraphs if getattr(p, "is_header", False) or getattr(p, "header_level", 0) > 0)
    avg_paras = sum(len(s.paragraphs) for s in sections) / len(sections) if sections else 0
    logging.info(
        "Section builder: %d ParagraphBlock, %d заголовков → %d Section, ср. %.1f абзацев в разделе",
        len(paragraphs),
        header_count,
        len(sections),
        avg_paras,
    )
    return sections


def flatten_paragraphs(sections: List[DocumentSection]) -> List[ParagraphBlock]:
    result: List[ParagraphBlock] = []
    for sec in sections:
        result.extend(sec.paragraphs)
    return result

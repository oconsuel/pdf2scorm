#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Построение слайдов (эвристический режим без LLM).

Fallback: H1 / научные разделы → новый раздел, H2 → новый слайд.
Длинные абзацы (>500 символов) разбиваются на предложения.
"""

import logging
import re
import uuid
from typing import List, Optional, Set

from ..models.lecture_model import (
    ParagraphBlock,
    LinkedImage,
    Slide,
    Section,
    Lecture,
    LectureSection,
    LecturePage,
    TextBlock,
    ImageBlock,
)

MAX_CHARS_PER_SLIDE = 380
MAX_TEXT_BLOCKS_PER_SLIDE = 4
MAX_PARAGRAPH_CHARS_BEFORE_SPLIT = 500

# Научные разделы: новый Section при таком заголовке
SCIENTIFIC_SECTION_HEADERS = (
    "введение", "методы", "результаты", "обсуждение", "заключение",
    "introduction", "methods", "results", "discussion", "conclusion",
)


def _split_sentences(text: str) -> List[str]:
    """Разбивает текст на предложения."""
    if not text or len(text) <= MAX_PARAGRAPH_CHARS_BEFORE_SPLIT:
        return [text] if text else []
    parts = re.split(r'(?<=[.!?])\s+', text)
    return [p.strip() for p in parts if p.strip()]


def _is_scientific_section_header(text: str) -> bool:
    """Проверяет, является ли заголовок разделом научной статьи."""
    t = text.strip().lower()[:50]
    return any(h in t for h in SCIENTIFIC_SECTION_HEADERS)


class SlideBuilder:
    """Строит слайды из абзацев и изображений (эвристики)."""

    def __init__(
        self,
        max_chars: int = MAX_CHARS_PER_SLIDE,
        max_blocks: int = MAX_TEXT_BLOCKS_PER_SLIDE,
    ):
        self.max_chars = max_chars
        self.max_blocks = max_blocks

    def build(
        self,
        paragraphs: List[ParagraphBlock],
        linked_images: List[LinkedImage],
    ) -> List[Section]:
        """
        Эвристика: H1 = новый раздел, H2 = новый слайд.
        Текст распределяется с ограничением по длине и количеству блоков.
        """
        if not paragraphs:
            return self._sections_from_images_only(linked_images)

        sections: List[Section] = []
        current_section: Optional[Section] = None
        current_slide: Optional[Slide] = None
        slide_chars = 0
        slide_blocks = 0

        def flush_slide(title: str):
            nonlocal current_slide, current_section, slide_chars, slide_blocks
            if current_slide and (current_slide.title or current_slide.text_blocks or current_slide.images):
                if current_section is None:
                    current_section = Section(
                        id=str(uuid.uuid4()),
                        title=title or "Содержание",
                        order=len(sections) + 1,
                    )
                    sections.append(current_section)
                current_section.slides.append(current_slide)
            current_slide = Slide(
                id=str(uuid.uuid4()),
                title=title,
                text_blocks=[],
                images=[],
                source_pages=[],
            )
            slide_chars = 0
            slide_blocks = 0

        def add_to_slide(text: str, page: int, para_id: Optional[str] = None):
            nonlocal current_slide, current_section, slide_chars, slide_blocks
            if current_slide is None:
                current_slide = Slide(
                    id=str(uuid.uuid4()),
                    title="Содержание",
                    text_blocks=[],
                    images=[],
                    source_pages=[],
                )
            if current_section is None:
                current_section = Section(
                    id=str(uuid.uuid4()),
                    title="Содержание",
                    order=1,
                )
                sections.append(current_section)
            if slide_blocks >= self.max_blocks or slide_chars + len(text) > self.max_chars:
                flush_slide(current_slide.title or "Страница")
            current_slide.text_blocks.append(text)
            if page not in current_slide.source_pages:
                current_slide.source_pages.append(page)
            if para_id and para_id not in current_slide.paragraph_ids:
                current_slide.paragraph_ids.append(para_id)
            slide_chars += len(text)
            slide_blocks += 1

        for p in paragraphs:
            header_text = p.text.strip()[:100]
            is_section_header = p.header_level == 1 or _is_scientific_section_header(p.text)
            if is_section_header:
                flush_slide(header_text)
                current_section = Section(
                    id=str(uuid.uuid4()),
                    title=header_text,
                    order=len(sections) + 1,
                )
                sections.append(current_section)
                current_slide = Slide(
                    id=str(uuid.uuid4()),
                    title=header_text,
                    text_blocks=[],
                    images=[],
                    source_pages=[p.page_number],
                    paragraph_ids=[p.id] if p.id else [],
                )
                slide_chars = 0
                slide_blocks = 0
            elif p.header_level >= 2:
                flush_slide(header_text)
                current_slide = Slide(
                    id=str(uuid.uuid4()),
                    title=header_text,
                    text_blocks=[],
                    images=[],
                    source_pages=[p.page_number],
                    paragraph_ids=[p.id] if p.id else [],
                )
                slide_chars = 0
                slide_blocks = 0
            else:
                if len(p.text) > MAX_PARAGRAPH_CHARS_BEFORE_SPLIT:
                    for sent in _split_sentences(p.text):
                        if sent:
                            add_to_slide(sent, p.page_number, p.id)
                    if current_slide:
                        for img in linked_images:
                            if img.linked_paragraph_id == p.id and img not in current_slide.images:
                                current_slide.images.append(img)
                else:
                    add_to_slide(p.text, p.page_number, p.id)
                    if current_slide:
                        for img in linked_images:
                            if img.linked_paragraph_id == p.id and img not in current_slide.images:
                                current_slide.images.append(img)

        flush_slide("")

        sections = _postprocess_heuristic_sections(sections)
        _place_between_paragraph_images(sections, linked_images)
        _split_heuristic_slides_with_many_blocks(sections)
        _log_heuristic_structure(sections)
        logging.info("Slide builder: сформировано %d разделов, %d слайдов",
                     len(sections), sum(len(s.slides) for s in sections))
        return sections

    def _sections_from_images_only(self, images: List[LinkedImage]) -> List[Section]:
        if not images:
            return [Section(id=str(uuid.uuid4()), title="Содержание", order=1, slides=[
                Slide(id=str(uuid.uuid4()), title="Страница 1", text_blocks=[], images=[], source_pages=[]),
            ])]
        sec = Section(id=str(uuid.uuid4()), title="Содержание", order=1)
        for img in images:
            sec.slides.append(Slide(
                id=str(uuid.uuid4()),
                title="Изображение",
                text_blocks=[],
                images=[img],
                source_pages=[img.page_number],
            ))
        return [sec]


def _place_between_paragraph_images(sections: List[Section], linked_images: List[LinkedImage]) -> None:
    """Размещает изображения на ближайший слайд (linked_paragraph_id или context_paragraph_ids)."""
    placed = {id(img) for sec in sections for slid in sec.slides for img in slid.images}
    for img in linked_images:
        if id(img) in placed:
            continue
        para_ids = list(getattr(img, "context_paragraph_ids", []) or [])
        if img.linked_paragraph_id and img.linked_paragraph_id not in para_ids:
            para_ids.insert(0, img.linked_paragraph_id)
        if not para_ids:
            para_ids = [img.linked_paragraph_id] if img.linked_paragraph_id else []
        for sec in sections:
            for slid in sec.slides:
                if any(pid in slid.paragraph_ids for pid in para_ids) and img not in slid.images:
                    slid.images.append(img)
                    placed.add(id(img))
                    break
            if id(img) in placed:
                break
        if id(img) in placed:
            continue
        if sections and sections[-1].slides:
            sections[-1].slides[-1].images.append(img)
        elif sections:
            sections[-1].slides.append(Slide(
                id=str(uuid.uuid4()),
                title="Изображение",
                text_blocks=[],
                images=[img],
                source_pages=[img.page_number],
            ))
        else:
            sec = Section(id=str(uuid.uuid4()), title="Содержание", order=1)
            sec.slides.append(Slide(
                id=str(uuid.uuid4()),
                title="Изображение",
                text_blocks=[],
                images=[img],
                source_pages=[img.page_number],
            ))
            sections.append(sec)


def _split_heuristic_slides_with_many_blocks(sections: List[Section]) -> None:
    """Делит слайды с >4 текстовых блоков на несколько."""
    max_blocks = MAX_TEXT_BLOCKS_PER_SLIDE
    for sec in sections:
        new_slides: List[Slide] = []
        for s in sec.slides:
            if len(s.text_blocks) <= max_blocks:
                new_slides.append(s)
                continue
            for i in range(0, len(s.text_blocks), max_blocks):
                chunk = s.text_blocks[i:i + max_blocks]
                is_last = i + max_blocks >= len(s.text_blocks)
                new_slides.append(Slide(
                    id=str(uuid.uuid4()),
                    title=s.title,
                    text_blocks=chunk,
                    images=s.images if is_last else [],
                    source_pages=s.source_pages,
                    paragraph_ids=s.paragraph_ids if is_last else [],
                ))
        sec.slides[:] = new_slides


def _postprocess_heuristic_sections(sections: List[Section]) -> List[Section]:
    """Удаляет пустые слайды, объединяет короткие, обеспечивает мин. 1 слайд."""
    result: List[Section] = []
    for sec in sections:
        slides = [s for s in sec.slides if s.title or s.text_blocks or s.images]
        if len(slides) >= 2:
            merged: List[Slide] = []
            i = 0
            while i < len(slides):
                curr = slides[i]
                curr_chars = sum(len(t) for t in curr.text_blocks)
                if curr_chars < 80 and i + 1 < len(slides):
                    next_s = slides[i + 1]
                    merged.append(Slide(
                        id=curr.id,
                        title=curr.title or next_s.title,
                        text_blocks=curr.text_blocks + next_s.text_blocks,
                        images=curr.images + [img for img in next_s.images if img not in curr.images],
                        source_pages=sorted(set(curr.source_pages + next_s.source_pages)),
                        paragraph_ids=list(dict.fromkeys(curr.paragraph_ids + next_s.paragraph_ids)),
                    ))
                    i += 2
                    continue
                merged.append(curr)
                i += 1
            slides = merged
        if not slides:
            slides = [Slide(id=str(uuid.uuid4()), title=sec.title, text_blocks=[], images=[], source_pages=[])]
        result.append(Section(id=sec.id, title=sec.title, slides=slides, order=sec.order))
    return result


def _log_heuristic_structure(sections: List[Section]) -> None:
    """Логирует структуру лекции (fallback-режим)."""
    total_slides = sum(len(sec.slides) for sec in sections)
    total_blocks = sum(len(s.text_blocks) for sec in sections for s in sec.slides)
    avg = total_blocks / total_slides if total_slides else 0
    logging.info(
        "Структура лекции (fallback): %d разделов, %d слайдов, ср. %.1f текстовых блоков на слайд",
        len(sections),
        total_slides,
        avg,
    )


def build_slides_heuristic(
    paragraphs: List[ParagraphBlock],
    linked_images: List[LinkedImage],
) -> List[Section]:
    """Удобная функция: строит слайды по эвристикам."""
    return SlideBuilder().build(paragraphs, linked_images)


MAX_SENTENCES_ON_SLIDE = 2
MAX_CHARS_PER_SLIDE_TRUNCATE = 400


def _truncate_for_slide(
    text: str,
    max_sentences: int = MAX_SENTENCES_ON_SLIDE,
    max_chars: int = MAX_CHARS_PER_SLIDE_TRUNCATE,
) -> str:
    """Обрезает текст по предложениям: первые 1–2 полных предложения. Ограничивает макс. длину."""
    if not text or not text.strip():
        return text
    t = text.strip()
    sentences = re.split(r'(?<=[.!?])\s+', t)
    if len(sentences) <= max_sentences:
        result = t
    else:
        result = ' '.join(sentences[:max_sentences])
    if len(result) > max_chars:
        last_dot = result.rfind('.', 0, max_chars + 1)
        if last_dot > 0:
            result = result[: last_dot + 1]
        else:
            result = result[: max_chars - 3].rsplit(maxsplit=1)[0] + "..."
    return result


def sections_to_lecture(
    sections: List[Section],
    title: str = "Лекция",
    description: str = "",
    language: str = "ru",
) -> Lecture:
    """Section[] → Lecture (LectureSection, LecturePage, ContentBlock)."""
    lecture = Lecture(title=title, description=description, language=language)
    for sec in sections:
        ls = LectureSection(id=sec.id, title=sec.title, order=sec.order)
        for idx, slide in enumerate(sec.slides):
            page = LecturePage(
                id=slide.id,
                title=slide.title or f"Страница {idx + 1}",
                order=idx + 1,
            )
            for tb in slide.text_blocks:
                truncated = _truncate_for_slide(tb)
                page.add_block(TextBlock(content=truncated, params={"bold": False, "alignment": "left"}))
            for img in slide.images:
                page.add_block(ImageBlock(
                    content=img.image_path,
                    params={"alt": img.caption or "", "width": None, "height": None},
                ))
            ls.add_page(page)
        lecture.add_section(ls)
    return lecture

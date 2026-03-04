#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Семантическая сегментация через LLM (GPT-4o).

Chunking: документ разбивается на блоки 6-10 элементов, каждый обрабатывается отдельно.
Сжатие текста: абзацы ограничены 300 символами, удаляются формулы, ссылки, DOI.
"""

import logging
import re
import uuid
from typing import List, Optional, Tuple

from ..models.lecture_model import ParagraphBlock, LinkedImage, Slide, Section
from ..llm.llm_client import LLMClient
from ..layout.block_normalizer import SCIENTIFIC_HEADERS

MAX_PARAGRAPH_CHARS = 300
MAX_ITEMS_PER_REQUEST = 20
CHUNK_SIZE_MIN = 6
CHUNK_SIZE_MAX = 10
MAX_SLIDES_PER_CHUNK = 4
MAX_CHARS_PER_SLIDE = 380
MAX_TEXT_BLOCKS_PER_SLIDE = 4
MERGE_SLIDE_CHARS_THRESHOLD = 150  # слайды с текстом <150 символов можно объединять

# Паттерны для удаления из научного текста
RE_FORMULA = re.compile(r'\$[^$]+\$|\\[a-zA-Z]+\{[^}]*\}|\\\([^)]*\\\)')
RE_DOI = re.compile(r'doi:\s*[\d./a-zA-Z-]+', re.I)
RE_HTTP_LINK = re.compile(r'https?://\S+')
RE_FIG_REF = re.compile(r'\(?(?:Рис\.|Figure|Fig\.)\s*\d+[a-zA-Z]?\)?', re.I)


def _summarize_text(text: str, max_sentences: int = 2, max_chars: int = 200) -> str:
    """Сжимает текст до 1–2 предложений для слайда."""
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
        result = result[:last_dot + 1] if last_dot > 0 else result[:max_chars - 3] + "..."
    return result


def _compress_paragraph_text(text: str) -> str:
    """Сжимает текст для LLM: ограничение 300 символов, удаление формул, ссылок, DOI."""
    if not text or not text.strip():
        return ""
    t = text.strip()
    t = RE_FORMULA.sub(' ', t)
    t = RE_DOI.sub(' ', t)
    t = RE_HTTP_LINK.sub(' ', t)
    t = RE_FIG_REF.sub(' ', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t[:MAX_PARAGRAPH_CHARS] if len(t) > MAX_PARAGRAPH_CHARS else t


def _is_scientific_section(text: str) -> bool:
    """Проверяет, является ли текст научным разделом (Введение, Методы и т.д.)."""
    if not text:
        return False
    t = text.strip().lower()[:80]
    return any(h in t for h in SCIENTIFIC_HEADERS)


def _split_into_chunks(
    items: List[dict],
    size_min: int = CHUNK_SIZE_MIN,
    size_max: int = CHUNK_SIZE_MAX,
) -> List[List[dict]]:
    """Разбивает элементы на чанки с учётом структуры: H1/H2 и научные разделы как границы."""
    if not items:
        return []
    chunks: List[List[dict]] = []
    current: List[dict] = []

    for i, item in enumerate(items):
        is_boundary = False
        itype = item.get("type", "")
        text = item.get("text", "") or ""
        hl = item.get("header_level", 0)
        if itype == "header":
            is_boundary = hl in (1, 2) or _is_scientific_section(text)
        elif itype == "paragraph" and (hl in (1, 2) or _is_scientific_section(text)):
            is_boundary = True

        if is_boundary and current and len(current) >= size_min:
            chunks.append(current)
            current = []

        current.append(item)
        if len(current) >= size_max:
            chunks.append(current)
            current = []

    if current:
        chunks.append(current)
    return chunks


def _aggregate_slides(slides: List[Slide]) -> List[Slide]:
    """Объединяет соседние слайды с коротким текстом в один смысловой блок."""
    if len(slides) <= 1:
        return slides
    result: List[Slide] = []
    i = 0
    while i < len(slides):
        curr = slides[i]
        total_chars = sum(len(t) for t in curr.text_blocks)
        if total_chars < MERGE_SLIDE_CHARS_THRESHOLD and i + 1 < len(slides):
            next_slide = slides[i + 1]
            next_chars = sum(len(t) for t in next_slide.text_blocks)
            combined_chars = total_chars + next_chars
            if combined_chars <= MAX_CHARS_PER_SLIDE and (
                len(curr.text_blocks) + len(next_slide.text_blocks) <= MAX_TEXT_BLOCKS_PER_SLIDE
            ):
                merged = Slide(
                    id=curr.id,
                    title=curr.title or next_slide.title,
                    text_blocks=curr.text_blocks + next_slide.text_blocks,
                    images=curr.images + [img for img in next_slide.images if img not in curr.images],
                    source_pages=sorted(set(curr.source_pages + next_slide.source_pages)),
                    paragraph_ids=list(dict.fromkeys(curr.paragraph_ids + next_slide.paragraph_ids)),
                )
                result.append(merged)
                i += 2
                continue
        result.append(curr)
        i += 1
    return result


def _split_large_slides(slides: List[Slide]) -> List[Slide]:
    """Делит слайды с >4 текстовых блоков или >MAX_CHARS_PER_SLIDE на несколько."""
    result: List[Slide] = []
    for s in slides:
        total_chars = sum(len(t) for t in s.text_blocks)
        if len(s.text_blocks) <= MAX_TEXT_BLOCKS_PER_SLIDE and total_chars <= MAX_CHARS_PER_SLIDE:
            result.append(s)
            continue
        acc_blocks: List[str] = []
        acc_chars = 0
        for tb in s.text_blocks:
            if (acc_blocks and acc_chars + len(tb) > MAX_CHARS_PER_SLIDE) or len(acc_blocks) >= MAX_TEXT_BLOCKS_PER_SLIDE:
                result.append(Slide(
                    id=str(uuid.uuid4()),
                    title=s.title,
                    text_blocks=acc_blocks.copy(),
                    images=[],
                    source_pages=s.source_pages,
                    paragraph_ids=[],
                ))
                acc_blocks = []
                acc_chars = 0
            acc_blocks.append(tb)
            acc_chars += len(tb)
        if acc_blocks:
            result.append(Slide(
                id=str(uuid.uuid4()),
                title=s.title,
                text_blocks=acc_blocks,
                images=s.images,
                source_pages=s.source_pages,
                paragraph_ids=s.paragraph_ids,
            ))
    return result


def _postprocess_sections(sections: List[Section]) -> List[Section]:
    """Удаляет пустые слайды, объединяет слишком короткие, обеспечивает мин. 1 слайд в разделе."""
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


def _place_unplaced_images(sections: List[Section], linked_images: List[LinkedImage]) -> None:
    """Размещает неразмещённые изображения на ближайший слайд (по linked_paragraph_id или context_paragraph_ids)."""
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


def _log_lecture_structure(sections: List[Section]) -> None:
    """Логирует итоговую структуру лекции."""
    total_slides = sum(len(sec.slides) for sec in sections)
    total_blocks = sum(
        len(s.text_blocks) for sec in sections for s in sec.slides
    )
    avg = total_blocks / total_slides if total_slides else 0
    logging.info(
        "Структура лекции: %d разделов, %d слайдов, ср. %.1f текстовых блоков на слайд",
        len(sections),
        total_slides,
        avg,
    )


def segment_by_llm(
    paragraphs: List[ParagraphBlock],
    linked_images: List[LinkedImage],
    language: str = "ru",
) -> Optional[List[Section]]:
    """
    Семантическая сегментация через LLM с chunking.
    
    Returns:
        List[Section] при успехе, None при ошибке или недоступности LLM.
    """
    client = LLMClient()
    if not client.available:
        return None

    para_by_idx: dict = {}
    img_by_idx: dict = {}

    items: List[dict] = []
    for i, p in enumerate(paragraphs):
        para_by_idx[i] = p
        hl = getattr(p, "header_level", 0)
        if hl > 0:
            items.append({
                "idx": i,
                "type": "header",
                "text": (p.text or "").strip()[:200],
                "header_level": hl,
                "page": p.page_number,
            })
        else:
            compressed = _compress_paragraph_text(p.text or "")
            if compressed:
                items.append({
                    "idx": i,
                    "type": "paragraph",
                    "text": compressed,
                    "page": p.page_number,
                    "header_level": 0,
                })

    offset = len(paragraphs)
    for j, img in enumerate(linked_images):
        idx = offset + j
        img_by_idx[idx] = img
        items.append({
            "idx": idx,
            "type": "image",
            "caption": (img.caption or "")[:150],
            "page": img.page_number,
        })

    if not items:
        return None

    all_slides_data: List[dict] = []
    chunks = _split_into_chunks(items, CHUNK_SIZE_MIN, CHUNK_SIZE_MAX)
    logging.info("Semantic segmentation: сформировано %d чанков для обработки LLM", len(chunks))

    for chunk_idx, chunk in enumerate(chunks):
        if len(chunk) > MAX_ITEMS_PER_REQUEST:
            sub_chunks = [chunk[i:i + MAX_ITEMS_PER_REQUEST] for i in range(0, len(chunk), MAX_ITEMS_PER_REQUEST)]
            for sub in sub_chunks:
                result = _call_llm_chunk(client, sub, language)
                if result:
                    all_slides_data.extend(result)
        else:
            result = _call_llm_chunk(client, chunk, language)
            if result:
                all_slides_data.extend(result)

    if not all_slides_data:
        return None

    section = Section(id=str(uuid.uuid4()), title="Содержание", order=1)
    for s in all_slides_data:
        title = (s.get("title") or "Страница").strip()[:100]
        para_indices = s.get("paragraph_indices", [])
        image_indices = s.get("image_indices", [])

        text_blocks: List[str] = []
        paragraph_ids: List[str] = []
        source_pages_set = set()
        for idx in para_indices:
            if idx in para_by_idx:
                p = para_by_idx[idx]
                summarized = _summarize_text(p.text or "")
                if summarized:
                    text_blocks.append(summarized)
                    paragraph_ids.append(p.id)
                    source_pages_set.add(p.page_number)

        images: List[LinkedImage] = []
        for idx in image_indices:
            if idx in img_by_idx:
                images.append(img_by_idx[idx])
                source_pages_set.add(img_by_idx[idx].page_number)

        source_pages = sorted(source_pages_set) if source_pages_set else [1]
        slide = Slide(
            id=str(uuid.uuid4()),
            title=title,
            text_blocks=text_blocks,
            images=images,
            source_pages=source_pages,
            paragraph_ids=paragraph_ids,
        )
        section.slides.append(slide)

    section.slides = _aggregate_slides(section.slides)
    section.slides = _split_large_slides(section.slides)
    sections_list = _postprocess_sections([section])
    _place_unplaced_images(sections_list, linked_images)
    _log_lecture_structure(sections_list)
    logging.info(
        "Semantic segmentation (LLM): %d chunks → %d слайдов (после агрегации и постобработки)",
        len(chunks),
        sum(len(sec.slides) for sec in sections_list),
    )
    return sections_list


def _call_llm_chunk(
    client: LLMClient,
    chunk_items: List[dict],
    language: str,
) -> Optional[List[dict]]:
    """Вызывает LLM для одного чанка. Возвращает список слайдов из ответа."""
    logging.info("LLM request items: %d", len(chunk_items))
    result = client.generate_slide_structure(chunk_items, language=language)
    if not result or "slides" not in result:
        logging.warning(
            "LLM вернул пустой или некорректный ответ (result=%s)",
            type(result).__name__ if result else "None",
        )
        return None
    slides = result["slides"]
    if not isinstance(slides, list) or not slides:
        logging.warning("LLM вернул пустой список слайдов")
        return None
    logging.info("LLM slides returned: %d", len(slides))
    return slides

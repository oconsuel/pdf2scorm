#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Привязка изображений к тексту.

Поиск caption по ключевым словам (Figure, Fig., Рис., Рисунок, Diagram).
Если caption не найден — привязка к ближайшему абзацу по Y.
"""

import re
import logging
from typing import List, Optional

from ..models.lecture_model import DocumentBlock, ParagraphBlock, LinkedImage

CAPTION_KEYWORDS = (
    r"\b(Figure|Fig\.|Рис\.|Рисунок|Diagram|Table|Таблица)\s*[\d.:]*\s*",
    r"^(Figure|Fig\.|Рис\.|Рисунок|Diagram)\s*[\d.:]*",
)
MAX_CAPTION_LENGTH = 150
MAX_CAPTION_FONT_RATIO = 1.1  # caption font не больше 1.1 * median


class ImageLinker:
    """Связывает изображения с подписями или ближайшими абзацами."""

    def link(
        self,
        doc_blocks: List[DocumentBlock],
        paragraphs: List[ParagraphBlock],
    ) -> List[LinkedImage]:
        """
        Для каждого изображения в doc_blocks создаёт LinkedImage.
        """
        image_blocks = [b for b in doc_blocks if b.type == "IMAGE" and b.image_path]
        if not image_blocks:
            return []
        median_font = 12.0
        if paragraphs:
            median_font = sum(p.font_size for p in paragraphs) / len(paragraphs)

        linked: List[LinkedImage] = []
        for pos, img in enumerate(image_blocks):
            caption = self._find_caption(img, paragraphs, median_font)
            linked_para_id = None
            if caption:
                para = self._find_paragraph_with_text(paragraphs, caption)
                if para:
                    linked_para_id = para.id
            else:
                para = self._find_nearest_paragraph(img, paragraphs)
                if para:
                    linked_para_id = para.id
            context_ids = self._get_context_paragraph_ids(img, paragraphs, linked_para_id)
            linked.append(LinkedImage(
                image_path=img.image_path,
                caption=caption or "",
                position=pos,
                linked_paragraph_id=linked_para_id,
                page_number=img.page_number,
                bbox=img.bbox,
                context_paragraph_ids=context_ids,
            ))
        logging.info("Image linking: обработано %d изображений", len(linked))
        return linked

    def _find_caption(
        self,
        img: DocumentBlock,
        paragraphs: List[ParagraphBlock],
        median_font: float,
    ) -> Optional[str]:
        """Ищет подпись рядом с изображением."""
        img_y_center = (img.bbox[1] + img.bbox[3]) / 2 if img.bbox else 0
        for p in paragraphs:
            if p.page_number != img.page_number:
                continue
            if not p.text or len(p.text) > MAX_CAPTION_LENGTH:
                continue
            if p.font_size > median_font * MAX_CAPTION_FONT_RATIO:
                continue
            text = p.text.strip()
            for pat in CAPTION_KEYWORDS:
                if re.search(pat, text, re.IGNORECASE):
                    p_center = (p.bbox[1] + p.bbox[3]) / 2 if p.bbox else 0
                    if abs(p_center - img_y_center) < 150:
                        return text
        return None

    def _find_paragraph_with_text(
        self,
        paragraphs: List[ParagraphBlock],
        text_snippet: str,
    ) -> Optional[ParagraphBlock]:
        for p in paragraphs:
            if text_snippet in p.text or p.text in text_snippet:
                return p
        return None

    def _get_context_paragraph_ids(
        self,
        img: DocumentBlock,
        paragraphs: List[ParagraphBlock],
        linked_para_id: Optional[str],
    ) -> List[str]:
        """Абзацы до и после изображения в документе (для вставки на ближайший слайд)."""
        result = []
        if linked_para_id:
            result.append(linked_para_id)
        img_y = (img.bbox[1] + img.bbox[3]) / 2 if img.bbox else 0
        same_page = [p for p in paragraphs if p.page_number == img.page_number and p.bbox]
        above = [p for p in same_page if (p.bbox[1] + p.bbox[3]) / 2 < img_y]
        below = [p for p in same_page if (p.bbox[1] + p.bbox[3]) / 2 > img_y]
        if above:
            prev = max(above, key=lambda p: (p.bbox[1] + p.bbox[3]) / 2)
            if prev.id not in result:
                result.append(prev.id)
        if below:
            nxt = min(below, key=lambda p: (p.bbox[1] + p.bbox[3]) / 2)
            if nxt.id not in result:
                result.append(nxt.id)
        return result

    def _find_nearest_paragraph(
        self,
        img: DocumentBlock,
        paragraphs: List[ParagraphBlock],
    ) -> Optional[ParagraphBlock]:
        """Ближайший абзац по вертикали (Y)."""
        img_y = (img.bbox[1] + img.bbox[3]) / 2 if img.bbox else 0
        best = None
        best_dist = float("inf")
        for p in paragraphs:
            if p.page_number != img.page_number:
                continue
            p_y = (p.bbox[1] + p.bbox[3]) / 2 if p.bbox else 0
            d = abs(p_y - img_y)
            if d < best_dist:
                best_dist = d
                best = p
        return best


def link_images(
    doc_blocks: List[DocumentBlock],
    paragraphs: List[ParagraphBlock],
) -> List[LinkedImage]:
    """Удобная функция: привязывает изображения к контексту."""
    return ImageLinker().link(doc_blocks, paragraphs)

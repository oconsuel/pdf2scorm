#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Layout Parsing — извлечение геометрических блоков из PDF без семантической интерпретации.

Минимальная единица обработки — строка (line), а не span.
Использует PyMuPDF page.get_text("dict").
"""

import logging
import tempfile
import uuid
from pathlib import Path
from typing import List, Optional

import fitz

from ..models.lecture_model import DocumentBlock

MIN_IMAGE_SIZE = 32  # px


class LayoutParser:
    """Парсер PDF — извлекает DocumentBlock (строки текста и изображения)."""

    def __init__(self, pdf_path: Path):
        self.pdf_path = Path(pdf_path)
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF файл не найден: {pdf_path}")
        self.temp_dir: Optional[Path] = None

    def parse(self, selected_pages: Optional[List[int]] = None) -> List[DocumentBlock]:
        """
        Парсит PDF и возвращает список DocumentBlock.
        
        Args:
            selected_pages: Номера страниц (1-based). None — все страницы.
        
        Returns:
            Список DocumentBlock (TEXT — по одному на строку, IMAGE).
        """
        blocks: List[DocumentBlock] = []
        self.temp_dir = Path(tempfile.mkdtemp(prefix="pdf_parser_"))
        images_dir = self.temp_dir / "images"
        images_dir.mkdir(parents=True, exist_ok=True)

        pdf_doc = fitz.open(self.pdf_path)
        try:
            total_pages = len(pdf_doc)
            if selected_pages:
                pages_to_parse = sorted({p for p in selected_pages if 1 <= p <= total_pages})
            else:
                pages_to_parse = list(range(1, total_pages + 1))

            image_counter = 0
            for page_num in pages_to_parse:
                page = pdf_doc[page_num - 1]
                text_blocks = self._extract_text_blocks(page, page_num)
                image_blocks = self._extract_image_blocks(page, page_num, images_dir, image_counter)
                image_counter += len(image_blocks)
                page_blocks = text_blocks + image_blocks
                page_blocks.sort(key=lambda b: (b.bbox[1], b.bbox[0]))
                blocks.extend(page_blocks)
        finally:
            pdf_doc.close()

        logging.info("Layout parsing: извлечено %d блоков (текст+изображения)", len(blocks))
        return blocks

    def _extract_text_blocks(self, page: fitz.Page, page_number: int) -> List[DocumentBlock]:
        """Извлекает текстовые блоки. Минимальная единица — строка (line)."""
        result: List[DocumentBlock] = []
        try:
            text_dict = page.get_text("dict")
            if not text_dict or "blocks" not in text_dict:
                return result

            for block in text_dict.get("blocks", []):
                if "lines" not in block:
                    continue
                for line in block.get("lines", []):
                    spans = line.get("spans", [])
                    if not spans:
                        continue
                    # Объединяем все spans строки в один DocumentBlock
                    parts = []
                    font_sizes = []
                    is_bold_list = []
                    bboxes = []
                    for span in spans:
                        t = span.get("text", "").strip()
                        if t:
                            parts.append(t)
                            font_sizes.append(span.get("size", 12.0))
                            is_bold_list.append(bool(span.get("flags", 0) & 16))
                            bboxes.append(span.get("bbox", (0, 0, 0, 0)))
                    if not parts:
                        continue
                    text = " ".join(parts)
                    # bbox строки — объединение bbox всех spans
                    x0 = min(b[0] for b in bboxes)
                    y0 = min(b[1] for b in bboxes)
                    x1 = max(b[2] for b in bboxes)
                    y1 = max(b[3] for b in bboxes)
                    bbox = (x0, y0, x1, y1)
                    avg_font = sum(font_sizes) / len(font_sizes)
                    any_bold = any(is_bold_list)
                    result.append(DocumentBlock(
                        id=str(uuid.uuid4()),
                        type="TEXT",
                        page_number=page_number,
                        bbox=bbox,
                        text=text,
                        font_size=avg_font,
                        is_bold=any_bold,
                    ))
        except Exception as e:
            logging.error("Ошибка извлечения текста: %s", e)
        return result

    def _extract_image_blocks(
        self,
        page: fitz.Page,
        page_number: int,
        images_dir: Path,
        start_counter: int,
    ) -> List[DocumentBlock]:
        """Извлекает изображения. Игнорирует изображения < 32px по ширине/высоте."""
        result: List[DocumentBlock] = []
        image_list = page.get_images(full=True)
        processed_xrefs = set()

        for img in image_list:
            xref = img[0]
            if xref in processed_xrefs:
                continue
            processed_xrefs.add(xref)
            try:
                base_image = page.parent.extract_image(xref)
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]

                image_rects = page.get_image_rects(xref)
                if not image_rects:
                    try:
                        bbox_dict = page.get_image_bbox(xref)
                        if bbox_dict:
                            bbox = (bbox_dict.x0, bbox_dict.y0, bbox_dict.x1, bbox_dict.y1)
                        else:
                            continue
                    except Exception:
                        continue
                else:
                    rect = image_rects[0]
                    bbox = (rect.x0, rect.y0, rect.x1, rect.y1)

                width = bbox[2] - bbox[0]
                height = bbox[3] - bbox[1]
                if width < MIN_IMAGE_SIZE or height < MIN_IMAGE_SIZE:
                    continue

                idx = start_counter + len(result)
                image_filename = f"image_{page_number}_{idx}.{image_ext}"
                image_path = images_dir / image_filename
                image_path.write_bytes(image_bytes)
                rel_path = f"images/{image_filename}"

                result.append(DocumentBlock(
                    id=str(uuid.uuid4()),
                    type="IMAGE",
                    page_number=page_number,
                    bbox=bbox,
                    image_path=rel_path,
                ))
            except Exception:
                continue
        return result

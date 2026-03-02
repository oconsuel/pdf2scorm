#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Парсер PDF файлов для извлечения элементов (текст, изображения).

Атомарный извлекатель без семантической логики.
Группировка и структура — в lecture_builder.py
"""

import logging
from pathlib import Path
from typing import List, Optional
import tempfile

from models.lecture_model import ParsedElement

import fitz  # PyMuPDF


class PDFParser:
    """
    Парсер PDF файлов — извлекает элементы без семантической обработки.
    Использует PyMuPDF для извлечения текста и изображений.
    """
    
    def __init__(self, pdf_path: Path):
        self.pdf_path = Path(pdf_path)
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF файл не найден: {pdf_path}")
        self.temp_dir = None
    
    def parse(self, selected_pages: Optional[List[int]] = None) -> List[ParsedElement]:
        """
        Парсит PDF и извлекает элементы в порядке их появления.
        
        Args:
            selected_pages: Номера страниц (1-based). None — все страницы.
        """
        all_elements = []
        
        self.temp_dir = Path(tempfile.mkdtemp(prefix="pdf_parser_"))
        images_dir = self.temp_dir / 'images'
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
                
                text_elements = self._extract_text_pymupdf(page, page_num)
                
                image_elements = self._extract_images_pymupdf(
                    page, page_num, images_dir, image_counter
                )
                real_images = [e for e in image_elements if e.type == "image"]
                image_counter += len(real_images)
                
                page_elements = text_elements + image_elements
                page_elements.sort(key=lambda e: (e.bbox[1], e.bbox[0]))
                
                all_elements.extend(page_elements)
        
        finally:
            pdf_doc.close()
        
        for idx, element in enumerate(all_elements):
            element.order = idx
        
        return all_elements
    
    def _extract_text_pymupdf(self, page: fitz.Page, page_number: int) -> List[ParsedElement]:
        """Извлекает текстовые spans через PyMuPDF (один span = один ParsedElement)."""
        elements = []
        
        try:
            text_dict = page.get_text("dict")
            
            if not text_dict or "blocks" not in text_dict:
                return elements
            
            for block in text_dict.get("blocks", []):
                if "lines" not in block:
                    continue
                
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text = span.get("text", "").strip()
                        if not text:
                            continue
                        
                        font_size = span.get("size", 12.0)
                        font_flags = span.get("flags", 0)
                        is_bold = bool(font_flags & 16)
                        bbox = span.get("bbox", (0, 0, 0, 0))
                        
                        elements.append(ParsedElement(
                            type="text",
                            text=text,
                            font_size=font_size,
                            is_bold=is_bold,
                            bbox=bbox,
                            page_number=page_number,
                        ))
        
        except Exception as e:
            logging.error(f"Ошибка при извлечении текста через PyMuPDF: {e}")
        
        return elements
    
    def _extract_images_pymupdf(
        self,
        page: fitz.Page,
        page_number: int,
        images_dir: Path,
        start_counter: int
    ) -> List[ParsedElement]:
        """Извлекает изображения через PyMuPDF с координатами."""
        image_elements = []
        image_list = page.get_images(full=True)
        
        processed_xrefs = set()
        
        for img_idx, img in enumerate(image_list):
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
                
                if width < 10 or height < 10:
                    continue
                
                image_filename = f"image_{page_number}_{start_counter + len(image_elements)}.{image_ext}"
                image_path = images_dir / image_filename
                
                with open(image_path, "wb") as img_file:
                    img_file.write(image_bytes)
                
                relative_path = image_path.relative_to(self.temp_dir)
                
                image_elements.append(ParsedElement(
                    type="image",
                    image_path=str(relative_path),
                    bbox=bbox,
                    page_number=page_number,
                ))
            
            except Exception:
                continue
        
        return image_elements

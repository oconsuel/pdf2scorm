#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Парсер PDF файлов для извлечения элементов (текст, изображения).

Этот модуль - "тупой извлекатель" элементов без семантической логики.
Вся семантика (заголовки, группировка, структура) находится в lecture_builder.py
"""

import sys
from pathlib import Path
from typing import List, Optional
import tempfile

# Добавляем родительскую директорию в путь для импорта
parent_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(parent_dir))

# Импортируем модели
sys.path.insert(0, str(Path(__file__).parent.parent))
from models.lecture_model import ParsedElement

# Проверяем доступность библиотек
try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False
    raise ImportError("Необходимо установить PyMuPDF: pip install PyMuPDF")

# Проверяем доступность OCR библиотек (только для fallback)
try:
    import pytesseract
    from PIL import Image
    import cv2
    import os
    import subprocess
    
    # Пытаемся найти Tesseract в стандартных местах
    tesseract_path = None
    paths_to_check = [
        '/opt/homebrew/bin/tesseract',
        '/usr/local/bin/tesseract',
        '/usr/bin/tesseract',
    ]
    
    for path in paths_to_check:
        if os.path.exists(path):
            tesseract_path = path
            pytesseract.pytesseract.tesseract_cmd = path
            break
    
    if not tesseract_path:
        try:
            result = subprocess.run(['which', 'tesseract'], capture_output=True, text=True, timeout=2)
            if result.returncode == 0:
                tesseract_path = result.stdout.strip()
                pytesseract.pytesseract.tesseract_cmd = tesseract_path
        except:
            pass
    
    try:
        pytesseract.get_tesseract_version()
        HAS_OCR = True
    except Exception:
        HAS_OCR = False
except ImportError:
    HAS_OCR = False


class PDFParser:
    """
    Парсер PDF файлов - извлекает элементы без семантической обработки.
    
    Использует PyMuPDF для извлечения текста и изображений.
    OCR используется ТОЛЬКО как fallback, если текстовый слой отсутствует.
    """
    
    def __init__(self, pdf_path: Path, use_ocr: bool = False):
        """
        Инициализация парсера
        
        Args:
            pdf_path: Путь к PDF файлу
            use_ocr: Разрешить OCR как fallback (по умолчанию False)
        """
        self.pdf_path = Path(pdf_path)
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF файл не найден: {pdf_path}")
        
        self.temp_dir = None
        self.use_ocr_fallback = use_ocr and HAS_OCR
        
        import logging
        if use_ocr and not HAS_OCR:
            logging.warning(
                "⚠️ OCR запрошен, но Tesseract не установлен.\n"
                "   OCR будет использоваться только как fallback при отсутствии текстового слоя."
            )
    
    def parse(self, selected_pages: Optional[List[int]] = None) -> List[ParsedElement]:
        """
        Парсит PDF файл и извлекает элементы в порядке их появления
        
        Args:
            selected_pages: Список номеров страниц для парсинга (1-based). 
                          Если None - парсятся все страницы
        
        Returns:
            Список ParsedElement в порядке их появления в PDF
        """
        import logging
        all_elements = []
        
        # Создаем временную директорию для изображений
        self.temp_dir = Path(tempfile.mkdtemp(prefix="pdf_parser_"))
        images_dir = self.temp_dir / 'images'
        images_dir.mkdir(parents=True, exist_ok=True)
        
        pdf_doc = fitz.open(self.pdf_path)
        
        try:
            total_pages = len(pdf_doc)
            
            if selected_pages is not None and len(selected_pages) > 0:
                pages_to_parse = sorted(set([p for p in selected_pages if 1 <= p <= total_pages]))
            else:
                pages_to_parse = list(range(1, total_pages + 1))
            
            
            image_counter = 0
            
            for page_num in pages_to_parse:
                page_idx = page_num - 1
                
                page = pdf_doc[page_idx]
                
                # Извлекаем текст через PyMuPDF
                text_elements = self._extract_text_pymupdf(page, page_num)
                
                # OCR fallback временно отключен
                # if not text_elements and self.use_ocr_fallback:
                #     text_elements = self._extract_text_ocr_fallback(page, page_num, images_dir)
                
                # Извлекаем изображения
                image_elements = self._extract_images_pymupdf(
                    page, page_num, images_dir, image_counter
                )
                real_images = [e for e in image_elements if e.type == "image"]
                image_counter += len(real_images)
                
                # Объединяем и сортируем элементы по позиции (сверху вниз, слева направо)
                page_elements = text_elements + image_elements
                page_elements.sort(key=lambda e: (e.bbox[1] if e.bbox else 0, e.bbox[0] if e.bbox else 0))
                
                all_elements.extend(page_elements)
        
        finally:
            pdf_doc.close()
        
        # Устанавливаем порядок элементов
        for idx, element in enumerate(all_elements):
            element.order = idx
        
        logging.info(f"\n{'='*60}")
        logging.info(f"{'='*60}\n")
        
        return all_elements
    
    def _extract_text_pymupdf(self, page: fitz.Page, page_number: int) -> List[ParsedElement]:
        """
        Упрощенный парсер - атомарный уровень.
        
        Один ParsedElement = один span.
        НЕ формирует абзацы, НЕ объединяет spans.
        Группировка будет в lecture_builder.
        """
        elements = []
        
        try:
            # Используем get_text("dict") для детальной информации
            text_dict = page.get_text("dict")
            
            if not text_dict or "blocks" not in text_dict:
                return elements
            
            # Извлекаем каждый span отдельно, без группировки
            for block in text_dict.get("blocks", []):
                if "lines" not in block:
                    continue
                
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text = span.get("text", "").strip()
                        if not text:
                            continue
                        
                        # Извлекаем свойства span
                        font_size = span.get("size", 12.0)
                        font_flags = span.get("flags", 0)
                        is_bold = bool(font_flags & 16)  # Бит 4 = жирный
                        
                        # Bounding box span
                        bbox = span.get("bbox", (0, 0, 0, 0))
                        
                        # Создаем один элемент на каждый span
                        element = ParsedElement(
                            type="text",
                            text=text,
                            font_size=font_size,
                            is_bold=is_bold,
                            bbox=bbox,
                            page_number=page_number,
                        )
                        elements.append(element)
        
        except Exception as e:
            import logging
            logging.error(f"❌ Ошибка при извлечении текста через PyMuPDF: {e}")
        
        return elements
    
    def _extract_text_ocr_fallback(self, page: fitz.Page, page_number: int, images_dir: Path) -> List[ParsedElement]:
        """
        OCR fallback - используется ТОЛЬКО если текстовый слой отсутствует.
        
        Помечает элементы как OCR fallback для дальнейшей обработки.
        """
        if not HAS_OCR:
            return []
        
        elements = []
        
        try:
            # Конвертируем страницу в изображение
            mat = fitz.Matrix(2.0, 2.0)  # Высокое разрешение для OCR
            pix = page.get_pixmap(matrix=mat)
            page_image_path = images_dir / f"page_{page_number}_ocr_fallback.png"
            pix.save(page_image_path)
            
            # Извлекаем текст через OCR
            ocr_text = self._extract_text_from_image(page_image_path)
            
            if ocr_text and len(ocr_text.strip()) > 10:
                # Разбиваем на строки и создаем элементы
                # OCR не дает точных координат, используем приблизительные
                lines = [l.strip() for l in ocr_text.split('\n') if l.strip()]
                
                # Приблизительные координаты (OCR не дает точных bbox)
                y_start = 50
                line_height = 20
                
                for i, line in enumerate(lines):
                    if len(line) < 3:
                        continue
                    
                    # Приблизительный bbox для OCR текста
                    bbox = (50, y_start + i * line_height, 500, y_start + (i + 1) * line_height)
                    
                    element = ParsedElement(
                        type="text",
                        text=line,
                        font_size=12.0,  # OCR не дает точного размера
                        is_bold=False,    # OCR не дает точной информации о жирности
                        bbox=bbox,
                        page_number=page_number,
                    )
                    # Помечаем как OCR fallback
                    element.is_ocr_fallback = True
                    elements.append(element)
        
        except Exception as e:
            import logging
            logging.error(f"❌ Ошибка OCR fallback для страницы {page_number}: {e}")
        
        return elements
    
    def _extract_images_pymupdf(
        self,
        page: fitz.Page,
        page_number: int,
        images_dir: Path,
        start_counter: int
    ) -> List[ParsedElement]:
        """
        Извлекает изображения через PyMuPDF с правильными координатами.
        
        НЕ делает OCR изображений.
        НЕ связывает изображения с текстом.
        """
        import logging
        image_elements = []
        image_list = page.get_images(full=True)
        
        processed_xrefs = set()
        
        for img_idx, img in enumerate(image_list):
            xref = img[0]
            
            if xref in processed_xrefs:
                continue
            processed_xrefs.add(xref)
            
            try:
                # Извлекаем изображение
                base_image = page.parent.extract_image(xref)
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]
                
                # Получаем координаты изображения
                image_rects = page.get_image_rects(xref)
                
                if not image_rects:
                    try:
                        bbox_dict = page.get_image_bbox(xref)
                        if bbox_dict:
                            bbox = (bbox_dict.x0, bbox_dict.y0, bbox_dict.x1, bbox_dict.y1)
                        else:
                            continue
                    except:
                        continue
                else:
                    rect = image_rects[0]
                    bbox = (rect.x0, rect.y0, rect.x1, rect.y1)
                
                # Проверяем размер изображения
                width = bbox[2] - bbox[0]
                height = bbox[3] - bbox[1]
                
                # Фильтруем очень маленькие изображения (артефакты)
                if width < 10 or height < 10:
                    continue
                
                # Сохраняем изображение
                image_filename = f"image_{page_number}_{start_counter + len(image_elements)}.{image_ext}"
                image_path = images_dir / image_filename
                
                with open(image_path, "wb") as img_file:
                    img_file.write(image_bytes)
                
                # Сохраняем относительный путь от temp_dir
                relative_path = image_path.relative_to(self.temp_dir)
                
                element = ParsedElement(
                    type="image",
                    image_path=str(relative_path),
                    bbox=bbox,
                    page_number=page_number,
                )
                
                image_elements.append(element)
            
            except Exception as e:
                import logging
                continue
        
        return image_elements
    
    def _extract_text_from_image(self, image_path: Path) -> str:
        """Извлекает текст из изображения с помощью OCR (только для fallback)"""
        if not HAS_OCR:
            return ""
        
        try:
            pytesseract.get_tesseract_version()
        except Exception:
            return ""
        
        try:
            # Загружаем изображение
            img = cv2.imread(str(image_path))
            if img is None:
                return ""
            
            # Предобработка изображения
            if len(img.shape) == 3:
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            else:
                gray = img
            
            # Бинаризация
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Конвертируем в PIL Image
            pil_image = Image.fromarray(thresh)
            
            # Извлекаем текст
            text = pytesseract.image_to_string(
                pil_image,
                lang='rus+eng',
                config='--psm 6 --oem 3'
            ).strip()
            
            return text
        
        except Exception as e:
            import logging
            logging.error(f"❌ Ошибка при извлечении текста через OCR: {e}")
            return ""
    
    def cleanup(self):
        """Очищает временные файлы"""
        if self.temp_dir and self.temp_dir.exists():
            import shutil
            shutil.rmtree(self.temp_dir, ignore_errors=True)
            self.temp_dir = None

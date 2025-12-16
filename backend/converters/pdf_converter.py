#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Конвертер PDF файлов в SCORM
Использует PDFParser для извлечения элементов из PDF
"""

import sys
from pathlib import Path
from typing import Optional, List

# Добавляем родительскую директорию в путь для импорта
parent_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(parent_dir))

from converters.pdf_parser import PDFParser
from models import ParsedElement


class PDFConverter:
    """Конвертер PDF файлов в SCORM формат"""
    
    def parse(self, pdf_path: Path, selected_pages: Optional[List[int]] = None) -> List[ParsedElement]:
        """
        Парсит PDF файл и извлекает элементы (текст и изображения)
        
        Args:
            pdf_path: Путь к PDF файлу
            selected_pages: Список номеров страниц для парсинга (1-based). 
                          Если None - парсятся все страницы
        
        Returns:
            Список ParsedElement в порядке их появления в PDF
        """
        parser = PDFParser(pdf_path)
        try:
            elements = parser.parse(selected_pages)
            return elements
        finally:
            parser.cleanup()
    
    def convert(self, pdf_path: Path, output_dir: Path, selected_pages: Optional[List[int]] = None) -> list:
        """
        Конвертирует PDF файл в SCORM структуру
        
        Args:
            pdf_path: Путь к PDF файлу
            output_dir: Директория для выходных файлов
            selected_pages: Список номеров страниц для конвертации (1-based). Если None - конвертируются все страницы
        
        Returns:
            Список словарей с информацией о созданных файлах
        """
        try:
            # Используем существующий класс PDFToSCORM
            converter = PDFToSCORM(
                pdf_path=str(pdf_path),
                output_dir=str(output_dir),
                scorm_version='2004',
                title=pdf_path.stem
            )
            
            # Конвертируем PDF в изображения
            all_image_paths = converter.convert_pdf_to_images()
            
            # Фильтруем страницы, если указаны выбранные
            # selected_pages может быть: None, [] (пустой список), или [1, 2, 3...] (список страниц)
            selected_pages_sorted = None
            if selected_pages is not None and len(selected_pages) > 0:
                # Сортируем выбранные страницы
                selected_pages_sorted = sorted(set(selected_pages))
                # Фильтруем изображения по выбранным страницам
                image_paths = [all_image_paths[i - 1] for i in selected_pages_sorted if 1 <= i <= len(all_image_paths)]
                if len(image_paths) == 0:
                    image_paths = all_image_paths
                    selected_pages_sorted = None
            else:
                # Если страницы не выбраны (None или пустой список), используем все
                image_paths = all_image_paths
            
            # Создаём HTML файлы для каждой выбранной страницы
            html_files = []
            total_pages = len(image_paths)
            
            for new_index, image_path in enumerate(image_paths, 1):
                # Определяем оригинальный номер страницы
                if selected_pages_sorted and len(selected_pages_sorted) > 0:
                    original_page_num = selected_pages_sorted[new_index - 1]
                else:
                    original_page_num = new_index
                
                html_content = converter.create_slide_html(
                    page_num=new_index,  # Новый порядковый номер для навигации
                    total_pages=total_pages,
                    image_filename=image_path.name
                )
                
                html_filename = f'page_{new_index}.html'
                html_path = output_dir / html_filename
                
                # Сохраняем HTML с контентом для последующего применения настроек
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                
                html_files.append({
                    'path': html_path,
                    'type': 'sco',
                    'original_name': f'{pdf_path.stem}_page_{original_page_num}',
                    'html_content': html_content,  # Сохраняем для применения настроек
                })
            
            # Возвращаем список созданных HTML файлов и изображений
            result = html_files.copy()
            
            # Добавляем только используемые изображения как ресурсы
            for image_path in image_paths:
                result.append({
                    'path': image_path,
                    'type': 'resource',
                    'original_name': image_path.name,
                })
            
            return result
            
        except Exception as e:
            raise Exception(f"Ошибка конвертации PDF: {str(e)}")


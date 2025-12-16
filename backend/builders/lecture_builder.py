#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Построитель лекции из извлеченных элементов PDF.

Группирует элементы в абзацы, определяет заголовки и формирует структуру лекции.
"""

import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import uuid
import statistics
import logging
import shutil
import base64
import re

# Добавляем родительскую директорию в путь для импорта
parent_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(parent_dir))

# Импортируем модели
sys.path.insert(0, str(Path(__file__).parent.parent))
from models.lecture_model import (
    Lecture, LectureSection, LecturePage,
    TextBlock, ImageBlock, ListBlock, TableBlock,
    ParsedElement
)


def build_lecture(elements: List[ParsedElement], output_images_dir: Optional[Path] = None) -> Lecture:
    """
    Строит модель лекции из извлеченных элементов PDF.
    
    Args:
        elements: Список ParsedElement (атомарные spans) в порядке их появления в PDF
        output_images_dir: Директория для сохранения изображений (если None, создается images/ в корне проекта)
    
    Returns:
        Lecture - структурированная модель лекции
    """
    if not elements:
        raise ValueError("Список элементов пуст")
    
    # Определяем директорию для изображений: если не указана, создаем images/ в корне проекта
    if output_images_dir is None:
        # Корень проекта - на 3 уровня выше от этого файла (backend/builders/lecture_builder.py)
        project_root = Path(__file__).parent.parent.parent
        output_images_dir = project_root / "images"
    # Создаем папку images/ если её нет
    output_images_dir.mkdir(parents=True, exist_ok=True)
    
    # Обрабатываем изображения: сохраняем на диск и нормализуем пути
    _normalize_image_paths(elements, output_images_dir)
    
    # Группировка spans в строки и абзацы
    paragraphs, images = _normalize_elements_to_paragraphs(elements)
    
    # Считаем статистику шрифтов на основе абзацев
    text_paragraphs = [p for p in paragraphs if p['type'] == 'text']
    if not text_paragraphs:
        return _build_lecture_from_images_only(elements)
    
    # Вычисляем медианный размер шрифта из абзацев
    paragraph_font_sizes = [p['avg_font_size'] for p in text_paragraphs]
    median_font_size = statistics.median(paragraph_font_sizes) if paragraph_font_sizes else 12.0
    avg_font_size = statistics.mean(paragraph_font_sizes) if paragraph_font_sizes else 12.0
    
    # Порог для заголовков
    std_font_size = statistics.stdev(paragraph_font_sizes) if len(paragraph_font_sizes) > 1 else 0
    header_threshold = max(median_font_size * 1.3, avg_font_size + 1.5 * std_font_size)
    
    # Определяем заголовки на уровне абзацев
    headers = _identify_headers_from_paragraphs(paragraphs, header_threshold, median_font_size)
    
    # Первый заголовок → Lecture.title
    lecture_title = _extract_lecture_title_from_paragraphs(paragraphs, headers)
    
    # Генерируем метаданные
    description = _generate_description_from_paragraphs(paragraphs, headers)
    language = _detect_language_from_paragraphs(paragraphs)
    keywords = _extract_keywords_from_paragraphs(paragraphs, headers)
    
    # Создаем структуру лекции
    lecture = Lecture(
        title=lecture_title,
        description=description,
        language=language
    )
    lecture.metadata["keywords"] = keywords
    
    # Группируем абзацы по разделам и страницам
    sections = _build_sections_from_paragraphs(paragraphs, headers, header_threshold, images)
    
    for section in sections:
        lecture.add_section(section)
    
    return lecture


def _normalize_image_paths(elements: List[ParsedElement], output_images_dir: Path) -> None:
    """
    Обрабатывает и сохраняет изображения: копирует файлы, декодирует base64/blob и обновляет пути.
    
    Все изображения сохраняются в output_images_dir с уникальными именами (img_{uuid4()}.ext).
    После обработки все ParsedElement.image_path начинаются с "images/" (относительные пути).
    
    Обрабатывает:
    - Base64 данные (data:image/...;base64,...) → декодирует и сохраняет как файл
    - Локальные файлы (абсолютные пути) → копирует в images/ с новым именем
    - Относительные пути → нормализует с префиксом images/
    - Blob URL → логирует предупреждение (не могут быть обработаны в Python)
    
    Args:
        elements: Список ParsedElement с изображениями
        output_images_dir: Директория для сохранения изображений (images/ в корне проекта)
    """
    processed_count = 0
    skipped_count = 0
    error_count = 0
    
    for elem in elements:
        if elem.type != "image" or not elem.image_path:
            continue
        
        original_path = elem.image_path
        
        try:
            # Случай 1: Путь уже относительный и начинается с images/ - оставляем как есть
            if not Path(elem.image_path).is_absolute() and elem.image_path.startswith("images/"):
                processed_count += 1
                continue
            
            # Генерируем уникальное имя файла с uuid4()
            unique_id = str(uuid.uuid4())
            
            # Случай 2: Blob URL - не можем обработать в Python (специфичны для браузера)
            if elem.image_path.startswith("blob:"):
                logging.warning(f"⚠️ Blob URL не может быть обработан в Python (требуется браузер): {elem.image_path}")
                # Пробуем сохранить как placeholder или пропускаем
                # В реальности blob URL должны обрабатываться на фронтенде перед отправкой
                skipped_count += 1
                continue
            
            # Случай 3: Base64 данные (data:image/...;base64,...)
            if elem.image_path.startswith("data:image/"):
                try:
                    # Извлекаем base64 данные
                    # Формат: data:image/png;base64,iVBORw0KGgo...
                    match = re.match(r'data:image/(\w+);base64,(.+)', elem.image_path)
                    if match:
                        image_format = match.group(1).lower()
                        base64_data = match.group(2)
                        
                        # Определяем расширение файла
                        ext_map = {'png': '.png', 'jpeg': '.jpg', 'jpg': '.jpg', 'gif': '.gif', 'webp': '.webp'}
                        ext = ext_map.get(image_format, '.png')
                        
                        # Декодируем base64
                        image_bytes = base64.b64decode(base64_data)
                        
                        # Сохраняем файл
                        image_filename = f"img_{unique_id}{ext}"
                        dest_path = output_images_dir / image_filename
                        
                        with open(dest_path, 'wb') as f:
                            f.write(image_bytes)
                        
                        # Обновляем путь на относительный
                        elem.image_path = f"images/{image_filename}"
                        processed_count += 1
                        continue
                    else:
                        logging.warning(f"⚠️ Некорректный формат base64 данных: {elem.image_path[:50]}...")
                        skipped_count += 1
                        continue
                except Exception as e:
                    logging.error(f"❌ Ошибка при декодировании base64: {e}")
                    error_count += 1
                    continue
            
            # Случай 4: Абсолютный путь - копируем файл
            if Path(elem.image_path).is_absolute():
                source_path = Path(elem.image_path)
                if source_path.exists():
                    # Определяем расширение файла
                    ext = source_path.suffix or ".png"
                    image_filename = f"img_{unique_id}{ext}"
                    dest_path = output_images_dir / image_filename
                    
                    try:
                        shutil.copy2(source_path, dest_path)
                        # Обновляем путь на относительный
                        elem.image_path = f"images/{image_filename}"
                        processed_count += 1
                    except Exception as e:
                        logging.error(f"❌ Ошибка при копировании изображения {source_path}: {e}")
                        error_count += 1
                else:
                    logging.warning(f"⚠️ Файл изображения не найден: {source_path}")
                    skipped_count += 1
                continue
            
            # Случай 5: Относительный путь (не начинается с images/)
            # Нормализуем его, добавляя префикс images/
            image_filename = Path(elem.image_path).name
            elem.image_path = f"images/{image_filename}"
            processed_count += 1
            
        except Exception as e:
            logging.error(f"❌ Неожиданная ошибка при обработке изображения {original_path}: {e}")
            error_count += 1
            continue
    


def _normalize_elements_to_paragraphs(elements: List[ParsedElement]) -> List[Dict[str, Any]]:
    """
    Преднормализация элементов.
    
    1. Сортирует spans по (page_number, normalized_y, x0)
    2. Группирует spans в строки по line_id
    3. Группирует строки в абзацы по близости Y, font_size, is_bold
    
    Returns:
        Список словарей-абзацев: {
            'type': 'text' | 'image',
            'spans': List[ParsedElement],
            'text': str,
            'avg_font_size': float,
            'is_bold': bool,
            'bbox': Tuple,
            'page_number': int,
            'is_header': bool,
            'header_level': int
        }
    """
    # Сортируем spans по (page_number, normalized_y, x0)
    def normalize_y(bbox: Tuple[float, float, float, float]) -> float:
        """Нормализует Y координату для группировки в строки"""
        if not bbox or len(bbox) < 4:
            return 0.0
        # Округляем Y до ближайших 5 пикселей для группировки в строки
        return round(bbox[1] / 5.0) * 5.0
    
    sorted_elements = sorted(
        elements,
        key=lambda e: (
            e.page_number,
            normalize_y(e.bbox) if e.bbox and len(e.bbox) >= 4 else 0,
            e.bbox[0] if e.bbox and len(e.bbox) >= 4 else 0
        )
    )
    
    # Группируем spans в строки по line_id (page_number + normalized_y)
    lines = []
    current_line = []
    current_line_id = None
    
    for elem in sorted_elements:
        if elem.type != "text" or not elem.text:
            # Изображения обрабатываем отдельно
            continue
        
        line_id = (elem.page_number, normalize_y(elem.bbox) if elem.bbox and len(elem.bbox) >= 4 else 0)
        
        if current_line_id is None or line_id != current_line_id:
            # Новая строка
            if current_line:
                lines.append(current_line)
            current_line = [elem]
            current_line_id = line_id
        else:
            # Продолжение строки
            current_line.append(elem)
    
    if current_line:
        lines.append(current_line)
    
    # Группируем строки в абзацы
    # Сначала анализируем распределение vertical_gap для определения медианного gap
    # Используем РЕАЛЬНЫЕ координаты bbox, а не normalized_y
    vertical_gaps = []
    for i in range(1, len(lines)):
        if not lines[i] or not lines[i-1]:
            continue
        curr_line_spans = lines[i]
        prev_line_spans = lines[i-1]
        if (curr_line_spans and prev_line_spans and
            curr_line_spans[0].page_number == prev_line_spans[0].page_number):
            # Используем реальные координаты bbox для вычисления gap
            curr_bbox = curr_line_spans[0].bbox
            prev_bbox = prev_line_spans[0].bbox
            if (curr_bbox and len(curr_bbox) >= 4 and 
                prev_bbox and len(prev_bbox) >= 4):
                # Gap = расстояние от нижней границы предыдущей строки до верхней границы текущей
                gap = curr_bbox[1] - prev_bbox[3]  # y0_current - y1_prev
                if gap > 0 and gap < 100:  # Игнорируем отрицательные и очень большие gaps
                    vertical_gaps.append(gap)
    
    # Вычисляем медианный gap
    median_gap = statistics.median(vertical_gaps) if vertical_gaps else 15.0
    # Также вычисляем средний gap для более точной оценки
    avg_gap = statistics.mean(vertical_gaps) if vertical_gaps else 15.0
    
    paragraphs = []
    current_paragraph = []
    
    for line_idx, line in enumerate(lines):
        if not line:
            continue
        
        # Свойства строки
        line_spans = line
        line_font_sizes = [s.font_size for s in line_spans]
        line_avg_font_size = statistics.mean(line_font_sizes) if line_font_sizes else 12.0
        line_is_bold = all(s.is_bold for s in line_spans if s.type == "text")
        line_bbox = line_spans[0].bbox if line_spans[0].bbox and len(line_spans[0].bbox) >= 4 else None
        line_page = line_spans[0].page_number
        
        # Получаем текст строки для эвристик
        line_text = " ".join([s.text for s in line_spans if s.text]).strip()
        line_starts_with_capital = line_text and line_text[0].isupper() if line_text else False
        
        if not current_paragraph:
            # Первая строка - начинаем новый абзац
            current_paragraph = [line]
        else:
            # Проверяем, можно ли добавить строку в текущий абзац
            prev_line = current_paragraph[-1]
            prev_line_spans = prev_line
            prev_line_bbox = prev_line_spans[0].bbox if prev_line_spans[0].bbox and len(prev_line_spans[0].bbox) >= 4 else None
            prev_line_page = prev_line_spans[0].page_number
            prev_line_font_sizes = [s.font_size for s in prev_line_spans]
            prev_line_avg_font_size = statistics.mean(prev_line_font_sizes) if prev_line_font_sizes else 12.0
            prev_line_is_bold = all(s.is_bold for s in prev_line_spans if s.type == "text")
            
            # Получаем текст предыдущей строки для эвристик
            prev_line_text = " ".join([s.text for s in prev_line_spans if s.text]).strip()
            prev_line_ends_with_period = prev_line_text and (prev_line_text.endswith('.') or prev_line_text.endswith('!') or prev_line_text.endswith('?')) if prev_line_text else False
            
            # Проверяем условия группировки в абзац:
            same_page = line_page == prev_line_page
            
            # Используем РЕАЛЬНЫЕ координаты bbox для вычисления vertical_gap
            if line_bbox and prev_line_bbox:
                # Gap = расстояние от нижней границы предыдущей строки до верхней границы текущей
                vertical_gap = line_bbox[1] - prev_line_bbox[3]  # y0_current - y1_prev
            else:
                vertical_gap = 0
            
            font_size_diff = abs(line_avg_font_size - prev_line_avg_font_size)
            same_bold = line_is_bold == prev_line_is_bold
            
            # Критерий 1: Базовые условия (та же страница, близость, одинаковый стиль)
            # Уменьшаем порог vertical_gap для более строгой группировки
            basic_conditions_met = (
                same_page and 
                vertical_gap < 15 and  # Уменьшено с 20 до 15 для более строгой группировки
                font_size_diff < 2.0 and 
                same_bold
            )
            
            # Критерий 2: Проверка на существенный разрыв
            # Используем более строгий порог: median_gap * 1.3 вместо 1.5
            significant_gap = vertical_gap > max(median_gap * 1.3, avg_gap * 1.2) if vertical_gap > 0 else False
            
            # Критерий 3: Эвристика для начала нового абзаца
            # Строка начинается с заглавной + предыдущая заканчивается точкой + есть отступ
            heuristic_new_paragraph = (
                line_starts_with_capital and
                prev_line_ends_with_period and
                vertical_gap > 8  # Уменьшено с 10 до 8 для более чувствительной эвристики
            )
            
            # Критерий 4: Дополнительная эвристика - очень большой отступ всегда разрывает абзац
            very_large_gap = vertical_gap > 25  # Очень большой отступ (> 25px) всегда новый абзац
            
            # Решение: продолжать абзац только если:
            # - базовые условия выполнены
            # - И нет существенного разрыва
            # - И нет эвристического признака нового абзаца
            # - И нет очень большого отступа
            if (basic_conditions_met and 
                not significant_gap and 
                not heuristic_new_paragraph and
                not very_large_gap):
                # Продолжение абзаца
                current_paragraph.append(line)
            else:
                # Новый абзац
                paragraphs.append(_create_paragraph_dict(current_paragraph, len(current_paragraph)))
                current_paragraph = [line]
    
    if current_paragraph:
        paragraphs.append(_create_paragraph_dict(current_paragraph, len(current_paragraph)))
    
    # Изображения храним отдельно, не добавляем в paragraphs
    images = [e for e in sorted_elements if e.type == "image"]
    
    # Добавляем global_index каждому абзацу
    for idx, para in enumerate(paragraphs):
        para['global_index'] = idx
    
    # Сортируем абзацы по позиции
    paragraphs.sort(key=lambda p: (p['page_number'], p['bbox'][1] if p['bbox'] and len(p['bbox']) >= 4 else 0))
    
    # Возвращаем абзацы и изображения отдельно
    return paragraphs, images


def _create_paragraph_dict(lines: List[List[ParsedElement]], num_lines: int) -> Dict[str, Any]:
    """
    Создает словарь-абзац из списка строк.
    
    Args:
        lines: Список строк (каждая строка - список spans)
        num_lines: Количество строк в абзаце (на основе line_id, не len(spans))
    """
    all_spans = []
    for line in lines:
        all_spans.extend(line)
    
    if not all_spans:
        return {
            'type': 'text',
            'spans': [],
            'text': '',
            'avg_font_size': 12.0,
            'is_bold': False,
            'bbox': (0, 0, 0, 0),
            'page_number': 0,
            'is_header': False,
            'header_level': 0,
            'num_lines': 0,  # количество строк на основе line_id
            'global_index': -1  # будет установлен позже
        }
    
    # Объединяем текст
    paragraph_text = " ".join([s.text for s in all_spans if s.text])
    
    # Вычисляем средний размер шрифта
    font_sizes = [s.font_size for s in all_spans if s.type == "text"]
    avg_font_size = statistics.mean(font_sizes) if font_sizes else 12.0
    
    # Проверяем, все ли spans жирные
    is_bold = all(s.is_bold for s in all_spans if s.type == "text")
    
    # Вычисляем общий bbox
    bboxes = [s.bbox for s in all_spans if s.bbox and len(s.bbox) >= 4]
    if bboxes:
        x0 = min(b[0] for b in bboxes)
        y0 = min(b[1] for b in bboxes)
        x1 = max(b[2] for b in bboxes)
        y1 = max(b[3] for b in bboxes)
        bbox = (x0, y0, x1, y1)
    else:
        bbox = (0, 0, 0, 0)
    
    page_number = all_spans[0].page_number
    
    return {
        'type': 'text',
        'spans': all_spans,
        'text': paragraph_text,
        'avg_font_size': avg_font_size,
        'is_bold': is_bold,
        'bbox': bbox,
        'page_number': page_number,
        'is_header': False,  # Будет определено позже
        'header_level': 0,
        'num_lines': num_lines,  # количество строк на основе line_id
        'global_index': -1  # будет установлен позже
    }


def _identify_headers_from_paragraphs(
    paragraphs: List[Dict[str, Any]],
    header_threshold: float,
    median_font_size: float
) -> List[Dict[str, Any]]:
    """
    Определяет заголовки на уровне абзацев.
    
    Заголовок = абзац, где:
    - средний font_size > медианного (или >= header_threshold)
    - или все spans жирные
    - абзац короткий (1-2 строки)
    
    Returns:
        Список словарей: {'index': int, 'level': int, 'text': str, 'paragraph': dict}
    """
    headers = []
    
    for idx, para in enumerate(paragraphs):
        if para['type'] != 'text' or not para['text']:
            continue
        
        text = para['text'].strip()
        if not text:
            continue
        
        is_header = False
        level = 0
        
        # Критерий 1: Средний font_size >= header_threshold
        if para['avg_font_size'] >= header_threshold:
            # Используем num_lines на основе line_id, а не len(spans)
            num_lines = para.get('num_lines', 0)
            if num_lines <= 2 and len(text) <= 150:  # Короткий абзац (1-2 строки)
                is_header = True
                if para['avg_font_size'] >= header_threshold * 1.5:
                    level = 1
                else:
                    level = 2
        
        # Критерий 2: Все spans жирные + короткий абзац
        if not is_header and para['is_bold']:
            # Используем num_lines на основе line_id
            num_lines = para.get('num_lines', 0)
            if num_lines <= 2 and len(text) <= 150:
                is_header = True
                level = 1
        
        # Критерий 3: Короткий абзац + начинается с заглавной + без точки в конце
        if not is_header:
            if (len(text) <= 100 and 
                len(text) > 3 and
                text[0].isupper() and
                not text.endswith('.') and
                not text.endswith(',') and
                para['avg_font_size'] >= median_font_size * 0.9):
                # Проверяем вертикальный отступ от предыдущего абзаца
                if idx > 0:
                    prev_para = paragraphs[idx - 1]
                    if prev_para['type'] == 'text' and prev_para['bbox'] and para['bbox']:
                        if len(prev_para['bbox']) >= 4 and len(para['bbox']) >= 4:
                            vertical_gap = para['bbox'][1] - prev_para['bbox'][3]
                            if vertical_gap > 20:
                                is_header = True
                                level = 1
        
        if is_header:
            # Обрезаем текст заголовка
            header_text = text
            if '\n' in header_text:
                header_text = header_text.split('\n')[0].strip()
            elif len(header_text) > 100:
                header_text = header_text[:100].rsplit(' ', 1)[0].strip()
            
            # Помечаем абзац как заголовок
            para['is_header'] = True
            para['header_level'] = level
            
            # Используем global_index, а не локальный индекс страницы
            headers.append({
                'index': para.get('global_index', idx),  # Используем global_index
                'level': level,
                'text': header_text,
                'paragraph': para
            })
    
    return headers


def _extract_lecture_title_from_paragraphs(
    paragraphs: List[Dict[str, Any]],
    headers: List[Dict[str, Any]]
) -> str:
    """Извлекает заголовок лекции из первого заголовка уровня 1"""
    for header in headers:
        if header['level'] == 1:
            return header['text']
    
    if headers:
        return headers[0]['text']
    
    # Если нет заголовков, берем первый текстовый абзац
    for para in paragraphs:
        if para['type'] == 'text' and para['text']:
            text = para['text'].strip()
            if text and len(text) < 200:
                return text
    
    return "Лекция"


def _generate_description_from_paragraphs(
    paragraphs: List[Dict[str, Any]],
    headers: List[Dict[str, Any]]
) -> str:
    """Генерирует описание из первых 1-2 текстовых абзацев (не заголовков)"""
    description_parts = []
    header_indices = {h['index'] for h in headers}
    
    for i, para in enumerate(paragraphs):
        if para['type'] != 'text' or not para['text'] or i in header_indices:
            continue
        
        text = para['text'].strip()
        if not text or len(text) < 10:
            continue
        
        description_parts.append(text)
        combined = " ".join(description_parts)
        if len(description_parts) >= 2 or len(combined) > 500:
            break
    
    if description_parts:
        description = " ".join(description_parts)
        if len(description) > 500:
            description = description[:497] + "..."
        return description
    
    return ""


def _detect_language_from_paragraphs(paragraphs: List[Dict[str, Any]]) -> str:
    """Автоматически определяет язык текста"""
    all_text = []
    for para in paragraphs:
        if para['type'] == 'text' and para['text']:
            text = para['text'].strip()
            if text and len(text) > 3:
                all_text.append(text)
    
    if not all_text:
        return "ru"
    
    combined_text = " ".join(all_text[:10])
    cyrillic_count = sum(1 for char in combined_text if '\u0400' <= char <= '\u04FF')
    latin_count = sum(1 for char in combined_text if char.isalpha() and ord(char) < 128 and char.isascii())
    
    if cyrillic_count > latin_count * 0.3:
        return "ru"
    else:
        return "en"


def _extract_keywords_from_paragraphs(
    paragraphs: List[Dict[str, Any]],
    headers: List[Dict[str, Any]]
) -> List[str]:
    """Извлекает ключевые слова из заголовков и частых слов"""
    keywords = []
    
    # Добавляем заголовки как ключевые слова
    for header in headers:
        if header['level'] == 1:
            keywords.append(header['text'])
    
    return keywords[:10]  # Ограничиваем до 10


def _build_sections_from_paragraphs(
    paragraphs: List[Dict[str, Any]],
    headers: List[Dict[str, Any]],
    header_threshold: float,
    images: List[ParsedElement]
) -> List[LectureSection]:
    """
    Группирует абзацы по разделам и страницам.
    
    Каждый заголовок уровня 1 создает отдельную страницу.
    """
    sections = []
    
    if not headers:
        # Нет заголовков - одна секция, одна страница
        section = LectureSection(
            id=str(uuid.uuid4()),
            title="Содержание",
            order=1
        )
        page = _build_single_page_from_paragraphs(paragraphs, "Страница 1", 1, headers, images)
        section.add_page(page)
        sections.append(section)
        return sections
    
    # Создаем одну секцию "Содержание" и добавляем страницы для каждого заголовка уровня 1
    section = LectureSection(
        id=str(uuid.uuid4()),
        title="Содержание",
        order=1
    )
    
    # Находим заголовки уровня 1
    level_1_headers = [h for h in headers if h['level'] == 1]
    
    if not level_1_headers:
        # Нет заголовков уровня 1 - используем все заголовки
        level_1_headers = headers
    
    # Создаем страницу для каждого заголовка уровня 1
    page_counter = 1
    for header_idx, header in enumerate(level_1_headers):
        para_index = header['index']
        
        # Определяем конец страницы (начало следующего заголовка или конец списка)
        if header_idx + 1 < len(level_1_headers):
            next_para_index = level_1_headers[header_idx + 1]['index']
        else:
            next_para_index = len(paragraphs)
        
        # Абзацы текущей страницы (включая заголовок)
        page_paragraphs = paragraphs[para_index:next_para_index]
        
        if not page_paragraphs:
            continue
        
        # Заголовок страницы - текст заголовка
        page_title = header['text'].strip()[:100]
        
        # Создаем страницу
        # Используем global_index для определения заголовков
        page = _build_single_page_from_paragraphs(page_paragraphs, page_title, page_counter, headers, images)
        section.add_page(page)
        page_counter += 1
    
    sections.append(section)
    return sections


def _build_single_page_from_paragraphs(
    paragraphs: List[Dict[str, Any]],
    title: str,
    order: int,
    all_headers: List[Dict[str, Any]],
    all_images: List[ParsedElement]
) -> LecturePage:
    """
    Формирует одну страницу из абзацев.
    
    Исключает заголовки из content_blocks.
    Привязывает изображения к абзацам.
    """
    page = LecturePage(
        id=str(uuid.uuid4()),
        title=title,
        order=order
    )
    
    # Сначала строим список текстовых абзацев (исключая заголовки)
    text_paragraphs = []
    # Используем global_index для определения заголовков
    header_global_indices = {h['index'] for h in all_headers}
    
    for para in paragraphs:
        if para['type'] != 'text':
            continue
        
        # Исключаем заголовки из content_blocks, используя global_index
        global_idx = para.get('global_index', -1)
        is_header_para = para.get('is_header', False) or global_idx in header_global_indices
        
        if is_header_para:
            continue  # Пропускаем заголовки
        
        text_paragraphs.append(para)
    
    # Создаем TextBlock из каждого абзаца
    # TextBlock должен хранить ссылку на исходный абзац
    for para in text_paragraphs:
        text_block = TextBlock(
            content=para['text'],
            params={
                "font_size": para['avg_font_size'],
                "bold": para['is_bold'],
                "alignment": "left",
                "source_paragraph": para  # ссылка на исходный абзац
            }
        )
        page.add_block(text_block)
    
    # Привязываем изображения к абзацам и встраиваем inline
    # Фильтруем изображения, которые относятся к этой странице
    page_images = []
    for img in all_images:
        # Проверяем, относится ли изображение к этой странице
        if paragraphs:
            first_para_page = paragraphs[0].get('page_number', 0)
            last_para_page = paragraphs[-1].get('page_number', 0)
            if first_para_page <= img.page_number <= last_para_page:
                page_images.append(img)
    
    # Определяем высоту страницы для проверки размера изображений
    # Используем максимальную высоту из абзацев или стандартную высоту A4 (842px при 72 DPI)
    page_height = 842.0  # Стандартная высота A4
    if paragraphs:
        max_y = max(
            (p['bbox'][3] if p.get('bbox') and len(p.get('bbox', [])) >= 4 else 0)
            for p in paragraphs
        )
        if max_y > 0:
            page_height = max_y
    
    # Сортируем изображения по позиции Y для правильного порядка вставки
    page_images.sort(key=lambda img: img.bbox[1] if img.bbox and len(img.bbox) >= 4 else 0)
    
    for img in page_images:
        # Проверяем bbox изображения
        if not img.bbox or len(img.bbox) < 4:
            continue
        
        # Проверяем image_path: должен быть SCORM-safe относительным путём к файлу
        # Если путь пустой или blob URL, пропускаем (blob URL не могут быть обработаны в Python)
        if not img.image_path:
            logging.warning(f"⚠️ Пустой image_path для изображения (пропущено)")
            continue
        
        # Blob URL не могут быть обработаны в Python (специфичны для браузера)
        # Такие изображения должны быть обработаны на этапе парсинга
        if img.image_path.startswith("blob:"):
            logging.error(f"❌ Blob URL в lecture_builder: {img.image_path} (не может быть обработан, пропущено)")
            continue
        
        # Проверяем размер изображения относительно страницы
        img_height = img.bbox[3] - img.bbox[1]
        img_relative_height = (img_height / page_height) * 100 if page_height > 0 else 0
        
        # Критерий 4: Отдельную страницу создавать только для очень больших изображений
        # (>60-70% высоты страницы) и без близких текстовых элементов
        is_very_large = img_relative_height > 60
        
        if is_very_large:
            # Проверяем, есть ли близкие текстовые элементы
            has_nearby_text = False
            for para in text_paragraphs:
                if para.get('bbox') and len(para.get('bbox', [])) >= 4:
                    para_bbox = para['bbox']
                    # Проверяем перекрытие или близость по Y
                    img_center_y = (img.bbox[1] + img.bbox[3]) / 2
                    para_center_y = (para_bbox[1] + para_bbox[3]) / 2
                    distance = abs(img_center_y - para_center_y)
                    if distance < 100:  # Близко к тексту
                        has_nearby_text = True
                        break
            
            if not has_nearby_text:
                # Очень большое изображение без близкого текста - пропускаем (не встраиваем inline)
                # Можно создать отдельную страницу позже, если нужно
                continue
        
        # Определяем позицию изображения относительно текстовых блоков по Y
        img_y_top = img.bbox[1]
        img_y_bottom = img.bbox[3]
        
        # Находим абзац, к которому относится изображение
        # Если изображение ниже абзаца A и выше абзаца B, относим к абзацу A
        target_block_idx = None
        
        for i, block in enumerate(page.content_blocks):
            if not isinstance(block, TextBlock):
                continue
            
            source_para = block.params.get('source_paragraph')
            if not source_para or not source_para.get('bbox') or len(source_para.get('bbox', [])) < 4:
                continue
            
            para_bbox = source_para['bbox']
            para_y_bottom = para_bbox[3]
            
            # Проверяем, находится ли изображение ниже этого абзаца
            if img_y_top >= para_y_bottom:
                # Изображение ниже этого абзаца
                # Проверяем, нет ли следующего абзаца, который выше изображения
                next_para_found = False
                for j in range(i + 1, len(page.content_blocks)):
                    next_block = page.content_blocks[j]
                    if isinstance(next_block, TextBlock):
                        next_source_para = next_block.params.get('source_paragraph')
                        if next_source_para and next_source_para.get('bbox') and len(next_source_para.get('bbox', [])) >= 4:
                            next_para_bbox = next_source_para['bbox']
                            next_para_y_top = next_para_bbox[1]
                            # Если следующий абзац выше изображения, то изображение между ними
                            if next_para_y_top > img_y_bottom:
                                # Изображение между текущим и следующим абзацем
                                target_block_idx = i
                                break
                            else:
                                # Следующий абзац ниже изображения, продолжаем поиск
                                continue
                
                if not next_para_found:
                    # Нет следующего абзаца или он ниже изображения - относим к текущему
                    target_block_idx = i
                    break
        
        # Если не нашли позицию по Y, используем ближайший блок
        if target_block_idx is None:
            target_block_idx = _find_nearest_text_block_for_image(page, img, text_paragraphs)
        
        # Вставляем изображение inline между TextBlock'ами
        # Убеждаемся, что путь начинается с images/ (должен быть уже нормализован в _normalize_image_paths)
        image_path = img.image_path
        if not image_path.startswith("images/"):
            # Если путь не начинается с images/, нормализуем его
            image_filename = Path(image_path).name
            image_path = f"images/{image_filename}"
            logging.warning(f"⚠️ Путь изображения нормализован при создании ImageBlock: {img.image_path} -> {image_path}")
        
        if target_block_idx is not None:
            image_block = ImageBlock(
                content=image_path,  # Используем нормализованный путь из images/
                params={
                    "alt": "",
                    "width": img.bbox[2] - img.bbox[0],
                    "height": img.bbox[3] - img.bbox[1],
                }
            )
            page.content_blocks.insert(target_block_idx + 1, image_block)
        else:
            # Нет текста рядом - добавляем в конец
            image_block = ImageBlock(
                content=image_path,  # Используем нормализованный путь из images/
                params={
                    "alt": "",
                    "width": img.bbox[2] - img.bbox[0],
                    "height": img.bbox[3] - img.bbox[1],
                }
            )
            page.add_block(image_block)
    
    return page


def _find_nearest_text_block_for_image(
    page: LecturePage,
    image: ParsedElement,
    text_paragraphs: List[Dict[str, Any]]
) -> Optional[int]:
    """
    Находит ближайший TextBlock к изображению по bbox.
    
    Использует source_paragraph из TextBlock, а не индекс.
    
    Returns:
        Индекс ближайшего TextBlock или None
    """
    if not image.bbox or len(image.bbox) < 4:
        return None
    
    image_center_y = (image.bbox[1] + image.bbox[3]) / 2
    
    nearest_idx = None
    min_distance = float('inf')
    
    # Ищем TextBlock'и и используем source_paragraph для вычисления расстояния
    for i, block in enumerate(page.content_blocks):
        if not isinstance(block, TextBlock):
            continue
        
        # Получаем source_paragraph из params
        source_para = block.params.get('source_paragraph')
        if source_para and source_para.get('bbox') and len(source_para['bbox']) >= 4:
            para_center_y = (source_para['bbox'][1] + source_para['bbox'][3]) / 2
            distance = abs(para_center_y - image_center_y)
            
            if distance < min_distance:
                min_distance = distance
                nearest_idx = i
    
    # Если расстояние слишком большое (> 300px), считаем что текста рядом нет
    if min_distance > 300:
        return None
    
    return nearest_idx


def _build_lecture_from_images_only(elements: List[ParsedElement]) -> Lecture:
    """Создает лекцию только из изображений (если нет текста)"""
    lecture = Lecture(
        title="Лекция",
        description="",
        language="ru"
    )
    
    section = LectureSection(
        id=str(uuid.uuid4()),
        title="Содержание",
        order=1
    )
    
    page = LecturePage(
        id=str(uuid.uuid4()),
        title="Страница 1",
        order=1
    )
    
    # Размещаем изображения
    for elem in elements:
        if elem.type == "image":
            # Проверяем image_path: должен быть SCORM-safe относительным путём к файлу
            if not elem.image_path:
                logging.warning(f"⚠️ Пустой image_path для изображения (пропущено)")
                continue
            
            # Blob URL не могут быть обработаны в Python (специфичны для браузера)
            if elem.image_path.startswith("blob:"):
                logging.error(f"❌ Blob URL в lecture_builder: {elem.image_path} (не может быть обработан, пропущено)")
                continue
            
            # ImageBlock создается с относительным путём для SCORM-пакета
            # Путь должен быть относительным от корня пакета (например, "images/img_1.png")
            # Путь уже должен быть нормализован в _normalize_image_paths, но проверяем на всякий случай
            image_path = elem.image_path
            if not image_path or not image_path.startswith("images/"):
                # Если путь не начинается с images/, нормализуем его
                if image_path:
                    image_filename = Path(image_path).name
                    image_path = f"images/{image_filename}"
                else:
                    logging.warning(f"⚠️ Пустой image_path для изображения, пропущено")
                    continue
            
            image_block = ImageBlock(
                content=image_path,  # Используем нормализованный путь из images/
                params={"alt": ""}
            )
            page.add_block(image_block)
            logging.debug(f"📌 Добавлено изображение на страницу: {image_path}")
    
    section.add_page(page)
    lecture.add_section(section)
    
    return lecture

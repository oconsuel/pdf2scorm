#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Сборщик SCORM 2004 пакетов
Поддерживает два режима:
- page_based: старое поведение (из PDF-страниц)
- lecture_based: новая логика (из модели Lecture)
"""

import zipfile
import shutil
from pathlib import Path
from xml.etree import ElementTree as ET
from xml.dom import minidom
import sys
from typing import Literal, Optional
import uuid
import json
import logging

# Добавляем родительскую директорию в путь для импорта
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from models.lecture_model import (
    Lecture,
    LectureSection,
    LecturePage,
    TextBlock,
    ImageBlock,
    ListBlock,
    TableBlock,
)


class SCORMBuilder:
    """Сборщик SCORM 2004 пакетов"""
    
    def __init__(self):
        self.scorm_version = '2004'
    
    def build(self, processed_files: list, launch_file: str, config: dict, 
              output_dir: Path, course_title: str, mode: Literal["page_based", "lecture_based"] = "page_based") -> Path:
        """
        Собирает SCORM 2004 пакет
        
        Args:
            processed_files: Список обработанных файлов (для page_based режима)
            launch_file: Имя launch файла (для page_based режима)
            config: Конфигурация SCORM из фронтенда
            output_dir: Директория для выходного файла
            course_title: Название курса
            mode: Режим работы ("page_based" или "lecture_based")
        
        Returns:
            Путь к созданному ZIP файлу
        """
        if mode == "lecture_based":
            raise ValueError("Для lecture_based режима используйте build_from_lecture()")
        
        # Старое поведение (page_based)
        return self._build_page_based(processed_files, launch_file, config, output_dir, course_title)
    
    def build_from_lecture(self, lecture: Lecture, config: dict, output_dir: Path, parser_temp_dir: Optional[Path] = None) -> Path:
        """
        Собирает SCORM 2004 пакет из модели Lecture
        
        Args:
            lecture: Модель лекции
            config: Конфигурация SCORM из фронтенда
            output_dir: Директория для выходного файла
            parser_temp_dir: Временная директория парсера, где хранятся изображения
        
        Returns:
            Путь к созданному ZIP файлу
        """
        # Создаём временную директорию для сборки
        package_dir = output_dir / f'{lecture.title}_scorm_package'
        if package_dir.exists():
            shutil.rmtree(package_dir)
        package_dir.mkdir(parents=True, exist_ok=True)
        
        images_dir = package_dir / 'images'
        images_dir.mkdir(exist_ok=True)
        
        try:
            # Сначала обрабатываем изображения, чтобы обновить block.content,
            # а потом генерируем HTML с правильными путями
            all_pages = lecture.get_all_pages()
            
            # Копируем изображения из parser_temp_dir в структуру SCORM
            image_files = []
            processed_image_filenames = set()
            
            for page in all_pages:
                for block in page.content_blocks:
                    if isinstance(block, ImageBlock) and block.content:
                        image_path_str = block.content
                        source_image_path = None
                        
                        # Пробуем найти изображение в parser_temp_dir
                        if parser_temp_dir and parser_temp_dir.exists():
                            possible_path = parser_temp_dir / image_path_str
                            if possible_path.exists():
                                source_image_path = possible_path
                        
                        # Если не нашли в parser_temp_dir, пробуем другие варианты
                        if not source_image_path:
                            image_path = Path(image_path_str)
                            if image_path.is_absolute() and image_path.exists():
                                source_image_path = image_path
                            elif not image_path.is_absolute():
                                possible_path = output_dir / image_path_str
                                if possible_path.exists():
                                    source_image_path = possible_path
                        
                        # Проверяем, что файл существует
                        if not source_image_path or not source_image_path.exists():
                            logging.warning(f"Изображение не найдено: {image_path_str}")
                            continue
                        
                        # Копируем в структуру SCORM (images/)
                        image_filename = source_image_path.name
                        dest_image_path = images_dir / image_filename
                        
                        # Избегаем дублирования по имени файла
                        if image_filename not in processed_image_filenames:
                            shutil.copy2(source_image_path, dest_image_path)
                            processed_image_filenames.add(image_filename)
                            
                            # Обновляем путь в ImageBlock на относительный от package_dir
                            relative_image_path = f"images/{image_filename}"
                            block.content = relative_image_path
                            
                            # Добавляем в список для manifest
                            if relative_image_path not in [str(img['path']) for img in image_files]:
                                image_files.append({
                                    'path': Path(relative_image_path),
                                    'type': 'resource',
                                })
            
            # Теперь генерируем HTML страницы после обновления путей изображений
            page_files = []
            for idx, page in enumerate(all_pages, 1):
                html_content = self._render_page_html(page, all_pages, config)
                html_filename = f'page_{idx}.html'
                html_path = package_dir / html_filename
                
                # Сохраняем в SCORM пакет
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                
                page_files.append({
                    'path': html_path.relative_to(package_dir),
                    'type': 'sco',
                    'page': page,
                })
            
            # Создаём SCORM API wrapper
            scorm_api_content = self._create_scorm_api_wrapper()
            api_path = package_dir / 'SCORM_API_wrapper.js'
            with open(api_path, 'w', encoding='utf-8') as f:
                f.write(scorm_api_content)
            
            # Создаём manifest
            manifest = self._create_manifest_from_lecture(
                lecture=lecture,
                page_files=page_files,
                image_files=image_files,
                config=config
            )
            
            # Сохраняем manifest
            manifest_str = minidom.parseString(ET.tostring(manifest)).toprettyxml(
                indent="  ", encoding=None
            )
            manifest_path = package_dir / 'imsmanifest.xml'
            with open(manifest_path, 'w', encoding='utf-8') as f:
                f.write(manifest_str)
            
            # Создаём ZIP архив
            zip_path = output_dir / f'{lecture.title}_SCORM_2004.zip'
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Добавляем manifest
                zipf.write(manifest_path, 'imsmanifest.xml')
                
                # Добавляем SCORM API wrapper
                zipf.write(api_path, 'SCORM_API_wrapper.js')
                
                # Добавляем HTML страницы
                for page_file in page_files:
                    zipf.write(package_dir / page_file['path'], str(page_file['path']))
                
                # Добавляем изображения в ZIP архив
                for image_file in image_files:
                    img_file_path = package_dir / image_file['path']
                    if img_file_path.exists():
                        zipf.write(img_file_path, str(image_file['path']))
                    else:
                        logging.warning(f"Изображение не найдено для ZIP: {image_file['path']}")
            
            return zip_path
            
        finally:
            # Удаляем временную директорию
            if package_dir.exists():
                shutil.rmtree(package_dir, ignore_errors=True)
    
    def _build_page_based(self, processed_files: list, launch_file: str, config: dict, 
                          output_dir: Path, course_title: str) -> Path:
        """Старое поведение: сборка из обработанных файлов"""
        # Создаём временную директорию для сборки
        package_dir = output_dir / f'{course_title}_scorm_package'
        if package_dir.exists():
            shutil.rmtree(package_dir)
        package_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Копируем все обработанные файлы в пакет
            files_in_package = []
            for file_info in processed_files:
                source_path = file_info['path']
                if source_path.exists():
                    # Определяем относительный путь в пакете
                    if 'images' in str(source_path):
                        dest_path = package_dir / 'images' / source_path.name
                        dest_path.parent.mkdir(exist_ok=True)
                    elif 'media' in str(source_path):
                        dest_path = package_dir / 'media' / source_path.name
                        dest_path.parent.mkdir(exist_ok=True)
                    else:
                        dest_path = package_dir / source_path.name
                    
                    # Если это HTML файл с контентом, сохраняем обновлённый контент
                    if file_info.get('html_content'):
                        with open(dest_path, 'w', encoding='utf-8') as f:
                            f.write(file_info['html_content'])
                    else:
                        shutil.copy2(source_path, dest_path)
                    
                    files_in_package.append({
                        'path': dest_path.relative_to(package_dir),
                        'type': file_info.get('type', 'resource'),
                        'original_name': file_info.get('original_name', source_path.name),
                    })
            
            # Создаём SCORM API wrapper
            scorm_api_content = self._create_scorm_api_wrapper()
            api_path = package_dir / 'SCORM_API_wrapper.js'
            with open(api_path, 'w', encoding='utf-8') as f:
                f.write(scorm_api_content)
            
            # Создаём manifest
            manifest = self._create_manifest_2004(
                files_in_package=files_in_package,
                launch_file=launch_file,
                course_title=course_title,
                config=config
            )
            
            # Сохраняем manifest
            manifest_str = minidom.parseString(ET.tostring(manifest)).toprettyxml(
                indent="  ", encoding=None
            )
            manifest_path = package_dir / 'imsmanifest.xml'
            with open(manifest_path, 'w', encoding='utf-8') as f:
                f.write(manifest_str)
            
            # Создаём ZIP архив
            zip_path = output_dir / f'{course_title}_SCORM_2004.zip'
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Добавляем manifest
                zipf.write(manifest_path, 'imsmanifest.xml')
                
                # Добавляем SCORM API wrapper
                zipf.write(api_path, 'SCORM_API_wrapper.js')
                
                # Добавляем все файлы
                for file_info in files_in_package:
                    file_path = package_dir / file_info['path']
                    if file_path.exists():
                        zipf.write(file_path, str(file_info['path']))
            
            return zip_path
            
        finally:
            # Удаляем временную директорию
            if package_dir.exists():
                shutil.rmtree(package_dir, ignore_errors=True)
    
    def _render_page_html(self, page: LecturePage, all_pages: list, config: dict) -> str:
        """
        Рендерит HTML страницу из LecturePage и ContentBlock
        
        Args:
            page: Страница лекции
            all_pages: Все страницы лекции (для навигации)
            config: Конфигурация SCORM
        
        Returns:
            HTML содержимое страницы
        """
        # Определяем предыдущую и следующую страницы
        current_index = all_pages.index(page)
        prev_page = all_pages[current_index - 1] if current_index > 0 else None
        next_page = all_pages[current_index + 1] if current_index < len(all_pages) - 1 else None
        
        # Рендерим блоки контента
        content_html = ""
        for block in page.content_blocks:
            content_html += self._render_content_block(block)
        
        # Получаем настройки из config
        player_style = config.get('playerStyle', {})
        primary_color = player_style.get('primaryColor', '#0ea5e9')
        theme = player_style.get('theme', 'auto')
        
        # Генерируем JSON конфигурацию заранее
        config_json = self._generate_config_json(config)
        
        html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self._clean_html_from_text(page.title)}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f5f5f5;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        
        .header {{
            background: {primary_color};
            color: white;
            padding: 20px;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 24px;
            margin: 0;
        }}
        
        .content {{
            padding: 30px;
        }}
        
        .content-block {{
            margin-bottom: 20px;
        }}
        
        .text-block {{
            font-size: 16px;
            line-height: 1.8;
            margin-bottom: 1em;
            text-align: justify;
            white-space: pre-wrap;
            word-wrap: break-word;
        }}
        
        .text-block.bold {{
            font-weight: bold;
        }}
        
        .text-block strong {{
            font-weight: bold;
        }}
        
        .text-block em {{
            font-style: italic;
        }}
        
        .text-block h2 {{
            font-size: 24px;
            font-weight: bold;
            margin: 20px 0 15px 0;
            color: {primary_color};
            border-bottom: 2px solid {primary_color};
            padding-bottom: 5px;
        }}
        
        .text-block h3 {{
            font-size: 20px;
            font-weight: bold;
            margin: 15px 0 10px 0;
            color: {primary_color};
        }}
        
        .text-block img {{
            max-width: 100%;
            height: auto;
            display: block;
            margin: 15px auto;
            border-radius: 4px;
            vertical-align: middle;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        
        /* Стили для формул и математических выражений */
        .text-block .formula {{
            display: inline-block;
            margin: 5px 0;
            text-align: center;
        }}
        
        .image-block {{
            text-align: center;
            margin: 20px 0;
        }}
        
        .image-block img {{
            max-width: 100%;
            height: auto;
            border-radius: 4px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        
        .image-block .caption {{
            margin-top: 10px;
            font-style: italic;
            color: #666;
        }}
        
        .list-block {{
            margin: 20px 0;
            padding-left: 30px;
        }}
        
        .list-block ul, .list-block ol {{
            margin: 10px 0;
        }}
        
        .list-block li {{
            margin: 8px 0;
        }}
        
        .table-block {{
            margin: 20px 0;
            overflow-x: auto;
        }}
        
        .table-block table {{
            width: 100%;
            border-collapse: collapse;
            margin: 10px 0;
        }}
        
        .table-block th, .table-block td {{
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }}
        
        .table-block th {{
            background-color: {primary_color};
            color: white;
            font-weight: bold;
        }}
        
    </style>
    <script src="SCORM_API_wrapper.js"></script>
    <script>
        // Инжектируем SCORM конфигурацию
        var scormConfigStr = {json.dumps(config_json)};
        window.SCORM_CONFIG = JSON.parse(scormConfigStr);
        
        // Проверяем, что pipwerks загружен
        if (typeof pipwerks === 'undefined') {{
            console.error('SCORM API Wrapper не загружен!');
            // Создаем заглушку для предотвращения ошибок
            window.pipwerks = {{
                SCORM: {{
                    version: null,
                    API: {{ isPresent: false }},
                    init: function() {{ return false; }},
                    get: function() {{ return ''; }},
                    set: function() {{ return false; }},
                    save: function() {{ return false; }},
                    quit: function() {{ return false; }}
                }}
            }};
        }}
    </script>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{self._clean_html_from_text(page.title)}</h1>
        </div>
        
        <div class="content">
            {content_html}
        </div>
    </div>
    
    <script>
        // Проверяем доступность pipwerks перед использованием
        if (typeof pipwerks === 'undefined' || !pipwerks.SCORM) {{
            console.error('SCORM API недоступен');
            // Используем заглушку, если pipwerks не загружен
            var scorm = {{
                version: null,
                API: {{ isPresent: false }},
                init: function() {{ return false; }},
                get: function() {{ return ''; }},
                set: function() {{ return false; }},
                save: function() {{ return false; }},
                quit: function() {{ return false; }}
            }};
        }} else {{
            var scorm = pipwerks.SCORM;
        }}
        var pageNum = {current_index + 1};
        var totalPages = {len(all_pages)};
        var sessionStartTime = null;
        var initialized = false;
        var scormVersion = "2004";
        
        function getStatusField() {{
            return scormVersion === "2004" ? "cmi.completion_status" : "cmi.core.lesson_status";
        }}
        
        function getLocationField() {{
            return scormVersion === "2004" ? "cmi.location" : "cmi.core.lesson_location";
        }}
        
        function getSuspendDataField() {{
            return scormVersion === "2004" ? "cmi.suspend_data" : "cmi.suspend_data";
        }}
        
        function initializeSCORM() {{
            if (initialized) return;
            
            // Проверяем доступность SCORM API
            if (!scorm || !scorm.init) {{
                console.warn('SCORM API недоступен, работаем в режиме предпросмотра');
                initialized = false;
                return;
            }}
            
            scorm.version = scormVersion;
            var initResult = scorm.init();
            
            if (initResult) {{
                initialized = true;
                sessionStartTime = new Date().getTime();
                
                var currentStatus = scorm.get(getStatusField());
                if (!currentStatus || currentStatus === "" || currentStatus === "null") {{
                    scorm.set(getStatusField(), "unknown");
                }}
                
                if (!currentStatus || currentStatus === "" || currentStatus === "null" ||
                    currentStatus === "not attempted" || currentStatus === "unknown") {{
                    scorm.set(getStatusField(), "incomplete");
                }}
                
                loadProgress();
                saveProgress();
            }}
        }}
        
        function loadProgress() {{
            var rememberLastPage = true;
            if (window.SCORM_CONFIG && window.SCORM_CONFIG.progressCompletion) {{
                rememberLastPage = window.SCORM_CONFIG.progressCompletion.rememberLastPage;
            }}
            
            if (!rememberLastPage) {{
                return;
            }}
        }}
        
        function saveProgress() {{
            if (!scorm || !scorm.API || !scorm.API.isPresent || !initialized) return;
            
            try {{
                var progressData = {{
                    visitedPages: [],
                    lastPage: pageNum
                }};
                
                var suspendData = scorm.get(getSuspendDataField());
                if (suspendData && suspendData !== "" && suspendData !== "null") {{
                    try {{
                        var existingProgress = JSON.parse(suspendData);
                        if (existingProgress.visitedPages) {{
                            progressData.visitedPages = existingProgress.visitedPages;
                        }}
                    }} catch (e) {{
                        // Игнорируем ошибки парсинга
                    }}
                }}
                
                if (!progressData.visitedPages.includes(pageNum)) {{
                    progressData.visitedPages.push(pageNum);
                }}
                
                scorm.set(getLocationField(), String(pageNum));
                scorm.set(getSuspendDataField(), JSON.stringify(progressData));
                
                var visitedCount = progressData.visitedPages.length;
                var completionThreshold = (window.SCORM_CONFIG && window.SCORM_CONFIG.progressCompletion && window.SCORM_CONFIG.progressCompletion.completionThreshold) || 80;
                var progressMethod = (window.SCORM_CONFIG && window.SCORM_CONFIG.progressCompletion && window.SCORM_CONFIG.progressCompletion.progressMethod) || 'screens';
                var progress = 0;
                
                if (progressMethod === 'screens') {{
                    progress = (visitedCount / totalPages) * 100;
                }} else if (progressMethod === 'combined') {{
                    progress = (visitedCount / totalPages) * 50;
                }}
                
                var currentStatus = scorm.get(getStatusField());
                if (progress >= completionThreshold || visitedCount === totalPages) {{
                    scorm.set(getStatusField(), "completed");
                }} else if (currentStatus !== "completed" && visitedCount > 0) {{
                    scorm.set(getStatusField(), "incomplete");
                }}
                
                var currentTime = new Date().getTime();
                var sessionTime = Math.round((currentTime - sessionStartTime) / 1000);
                scorm.set("cmi.session_time", "PT" + sessionTime + "S");
                
                scorm.save();
            }} catch (e) {{
                // Игнорируем ошибки сохранения
            }}
        }}
        
        window.addEventListener('load', function() {{
            initializeSCORM();
            setTimeout(function() {{
                if (initialized) {{
                    saveProgress();
                }}
            }}, 500);
        }});
        
        window.addEventListener('beforeunload', function() {{
            if (initialized) {{
                saveProgress();
                scorm.quit();
            }}
        }});
    </script>
</body>
</html>"""
        
        return html
    
    def _render_content_block(self, block) -> str:
        """Рендерит ContentBlock в HTML с поддержкой форматирования"""
        if isinstance(block, TextBlock):
            style = ""
            if block.params.get('font_size'):
                style += f"font-size: {block.params['font_size']}px; "
            if block.params.get('bold'):
                style += "font-weight: bold; "
            if block.params.get('alignment'):
                style += f"text-align: {block.params['alignment']}; "
            
            class_name = "text-block"
            if block.params.get('bold'):
                class_name += " bold"
            
            # Проверяем, содержит ли контент HTML (изображения, форматирование)
            content = block.content
            
            # Если уже есть HTML теги (изображения, форматирование, переносы строк), используем их как есть
            if '<img' in content or '<strong' in content or '<em' in content or '<br>' in content:
                return f'<div class="content-block {class_name}" style="{style}">{content}</div>'
            
            # Иначе экранируем HTML и применяем форматирование
            import html
            escaped_content = html.escape(content)
            # Заменяем переносы строк на <br>
            escaped_content = escaped_content.replace('\n', '<br>')
            if block.params.get('bold'):
                escaped_content = f'<strong>{escaped_content}</strong>'
            
            return f'<div class="content-block {class_name}" style="{style}">{escaped_content}</div>'
        
        elif isinstance(block, ImageBlock):
            # Используем путь из block.content (уже обновлен на "images/filename.ext")
            image_path = block.content
            # Если путь не начинается с images/ и не абсолютный/HTTP, добавляем images/
            if not image_path.startswith('http') and not Path(image_path).is_absolute():
                if not image_path.startswith('images/'):
                    image_path = f"images/{Path(image_path).name}"
            
            alt = block.params.get('alt', '')
            caption = block.params.get('caption', '')
            
            html = f'<div class="content-block image-block">'
            html += f'<img src="{image_path}" alt="{alt}">'
            if caption:
                html += f'<div class="caption">{caption}</div>'
            html += '</div>'
            return html
        
        elif isinstance(block, ListBlock):
            tag = 'ol' if block.params.get('ordered', False) else 'ul'
            items_html = ''.join(f'<li>{item}</li>' for item in block.content)
            return f'<div class="content-block list-block"><{tag}>{items_html}</{tag}></div>'
        
        elif isinstance(block, TableBlock):
            rows = block.content
            if not rows:
                return ''
            
            html = '<div class="content-block table-block"><table>'
            
            # Заголовки
            if block.params.get('has_header_row') and block.params.get('headers'):
                html += '<thead><tr>'
                for header in block.params['headers']:
                    html += f'<th>{header}</th>'
                html += '</tr></thead>'
            
            # Строки
            html += '<tbody>'
            for row in rows:
                html += '<tr>'
                for cell in row:
                    html += f'<td>{cell}</td>'
                html += '</tr>'
            html += '</tbody></table></div>'
            
            return html
        
        return ''
    
    def _clean_html_from_text(self, text: str) -> str:
        """Удаляет HTML теги из текста, оставляя только чистый текст"""
        if not text:
            return ""
        import re
        # Удаляем все HTML теги
        clean_text = re.sub(r'<[^>]+>', '', text)
        # Декодируем HTML entities
        import html
        clean_text = html.unescape(clean_text)
        # Убираем лишние пробелы
        clean_text = ' '.join(clean_text.split())
        return clean_text
    
    def _generate_config_json(self, config: dict) -> str:
        """Генерирует безопасный JSON для JavaScript с правильным экранированием"""
        import json
        # Очищаем config от None значений и несериализуемых типов
        clean_config = {}
        for key, value in config.items():
            if value is None:
                continue
            if isinstance(value, dict):
                clean_config[key] = {k: v for k, v in value.items() if v is not None}
            else:
                clean_config[key] = value
        
        # Генерируем JSON
        json_str = json.dumps(clean_config, ensure_ascii=False)
        return json_str
    
    def _create_manifest_from_lecture(self, lecture: Lecture, page_files: list, 
                                     image_files: list, config: dict) -> ET.Element:
        """
        Создаёт SCORM 2004 manifest из модели Lecture
        
        Структура:
        - organization = лекция
        - item для разделов
        - item + resource для страниц
        """
        manifest = ET.Element('manifest')
        manifest.set('identifier', f"SCORM_{lecture.title.replace(' ', '_')}")
        manifest.set('version', '1')
        manifest.set('xmlns', 'http://www.imsglobal.org/xsd/imscp_v1p1')
        manifest.set('xmlns:adlcp', 'http://www.adlnet.org/xsd/adlcp_v1p3')
        manifest.set('xmlns:adlseq', 'http://www.adlnet.org/xsd/adlseq_v1p3')
        manifest.set('xmlns:adlnav', 'http://www.adlnet.org/xsd/adlnav_v1p3')
        manifest.set('xmlns:imsss', 'http://www.imsglobal.org/xsd/imsss')
        manifest.set('xmlns:xsi', 'http://www.w3.org/2001/XMLSchema-instance')
        manifest.set('xsi:schemaLocation', 
                    'http://www.imsglobal.org/xsd/imscp_v1p1 imscp_v1p1.xsd '
                    'http://www.adlnet.org/xsd/adlcp_v1p3 adlcp_v1p3.xsd '
                    'http://www.adlnet.org/xsd/adlseq_v1p3 adlseq_v1p3.xsd '
                    'http://www.adlnet.org/xsd/adlnav_v1p3 adlnav_v1p3.xsd '
                    'http://www.imsglobal.org/xsd/imsss imsss.xsd')
        
        # Metadata
        metadata = ET.SubElement(manifest, 'metadata')
        schema = ET.SubElement(metadata, 'schema')
        schema.text = 'ADL SCORM'
        schemaversion = ET.SubElement(metadata, 'schemaversion')
        schemaversion.text = '2004 4th Edition'
        
        # Organizations
        organizations = ET.SubElement(manifest, 'organizations')
        organizations.set('default', 'TOC1')
        organization = ET.SubElement(organizations, 'organization')
        organization.set('identifier', 'TOC1')
        title = ET.SubElement(organization, 'title')
        title.text = lecture.title
        
        # Resources
        resources = ET.SubElement(manifest, 'resources')
        
        # Создаём items для разделов и страниц
        all_pages = lecture.get_all_pages()
        page_counter = 0
        
        for section in lecture.sections:
            # Item для раздела
            section_item_id = f'SECTION_{section.id}'
            section_item = ET.SubElement(organization, 'item')
            section_item.set('identifier', section_item_id)
            section_title = ET.SubElement(section_item, 'title')
            section_title.text = section.title
            
            # Применяем настройки sequencing для раздела
            if config:
                self._apply_sequencing_config(section_item, config, section.order == 1)
            
            # Создаём items для страниц раздела
            for page in section.pages:
                page_counter += 1
                page_item_id = f'PAGE_{page.id}'
                resource_id = f'RES_PAGE_{page_counter}'
                
                # Item для страницы
                page_item = ET.SubElement(section_item, 'item')
                page_item.set('identifier', page_item_id)
                page_item.set('identifierref', resource_id)
                page_title = ET.SubElement(page_item, 'title')
                page_title.text = self._clean_html_from_text(page.title)
                
                # Resource для страницы
                page_file = next((pf for pf in page_files if pf['page'].id == page.id), None)
                if page_file:
                    resource = ET.SubElement(resources, 'resource')
                    resource.set('identifier', resource_id)
                    resource.set('type', 'webcontent')
                    resource.set('adlcp:scormType', 'sco')
                    resource.set('href', str(page_file['path']))
                    
                    # Файл страницы
                    file_elem = ET.SubElement(resource, 'file')
                    file_elem.set('href', str(page_file['path']))
                    
                    # SCORM API wrapper
                    file_scorm = ET.SubElement(resource, 'file')
                    file_scorm.set('href', 'SCORM_API_wrapper.js')
                    
                    # Добавляем изображения как ресурсы
                    for image_file in image_files:
                        file_img = ET.SubElement(resource, 'file')
                        file_img.set('href', str(image_file['path']))
        
        return manifest
    
    def _create_manifest_2004(self, files_in_package: list, launch_file: str,
                              course_title: str, config: dict) -> ET.Element:
        """Создаёт SCORM 2004 manifest (старое поведение для page_based режима)"""
        manifest = ET.Element('manifest')
        manifest.set('identifier', f"SCORM_{course_title.replace(' ', '_')}")
        manifest.set('version', '1')
        manifest.set('xmlns', 'http://www.imsglobal.org/xsd/imscp_v1p1')
        manifest.set('xmlns:adlcp', 'http://www.adlnet.org/xsd/adlcp_v1p3')
        manifest.set('xmlns:adlseq', 'http://www.adlnet.org/xsd/adlseq_v1p3')
        manifest.set('xmlns:adlnav', 'http://www.adlnet.org/xsd/adlnav_v1p3')
        manifest.set('xmlns:imsss', 'http://www.imsglobal.org/xsd/imsss')
        manifest.set('xmlns:xsi', 'http://www.w3.org/2001/XMLSchema-instance')
        manifest.set('xsi:schemaLocation', 
                    'http://www.imsglobal.org/xsd/imscp_v1p1 imscp_v1p1.xsd '
                    'http://www.adlnet.org/xsd/adlcp_v1p3 adlcp_v1p3.xsd '
                    'http://www.adlnet.org/xsd/adlseq_v1p3 adlseq_v1p3.xsd '
                    'http://www.adlnet.org/xsd/adlnav_v1p3 adlnav_v1p3.xsd '
                    'http://www.imsglobal.org/xsd/imsss imsss.xsd')
        
        # Metadata
        metadata = ET.SubElement(manifest, 'metadata')
        schema = ET.SubElement(metadata, 'schema')
        schema.text = 'ADL SCORM'
        schemaversion = ET.SubElement(metadata, 'schemaversion')
        schemaversion.text = '2004 4th Edition'
        
        # Organizations
        organizations = ET.SubElement(manifest, 'organizations')
        organizations.set('default', 'TOC1')
        organization = ET.SubElement(organizations, 'organization')
        organization.set('identifier', 'TOC1')
        title = ET.SubElement(organization, 'title')
        title.text = course_title
        
        # Resources
        resources = ET.SubElement(manifest, 'resources')
        
        # Группируем файлы по SCO
        sco_files = [f for f in files_in_package if f['type'] == 'sco']
        resource_files = [f for f in files_in_package if f['type'] == 'resource']
        
        # Если нет SCO файлов, создаём один из launch файла
        if not sco_files:
            launch_file_path = None
            for f in files_in_package:
                if launch_file in str(f['path']) or f['original_name'] == launch_file or f['path'].name == launch_file:
                    launch_file_path = f['path']
                    break
            
            if launch_file_path:
                sco_files = [{
                    'path': launch_file_path,
                    'original_name': launch_file_path.name,
                }]
            else:
                html_files = [f for f in files_in_package if str(f['path']).endswith('.html')]
                if html_files:
                    html_files.sort(key=lambda x: str(x['path']))
                    launch_file_path = html_files[0]['path']
                    sco_files = [{
                        'path': launch_file_path,
                        'original_name': launch_file_path.name,
                    }]
        
        # Сортируем SCO файлы по номеру страницы
        def get_page_number(file_path):
            import re
            path_str = str(file_path)
            match = re.search(r'page_(\d+)\.html', path_str)
            if match:
                return int(match.group(1))
            return float('inf')
        
        sco_files_sorted = sorted(sco_files, key=lambda x: get_page_number(x['path']))
        
        # Создаём items и resources для SCO
        for idx, sco_file in enumerate(sco_files_sorted, 1):
            item_id = f'ITEM_SCO_{idx}'
            resource_id = f'RES_SCO_{idx}'
            
            is_launch = (str(sco_file['path']) == launch_file or 
                        sco_file['path'].name == launch_file or
                        (idx == 1 and launch_file in str(sco_file['path'])))
            
            # Item
            item = ET.SubElement(organization, 'item')
            item.set('identifier', item_id)
            item.set('identifierref', resource_id)
            item_title = ET.SubElement(item, 'title')
            item_title.text = sco_file.get('original_name', str(sco_file['path']))
            
            # Применяем настройки sequencing
            if config:
                self._apply_sequencing_config(item, config, is_launch)
            
            # Resource
            resource = ET.SubElement(resources, 'resource')
            resource.set('identifier', resource_id)
            resource.set('type', 'webcontent')
            resource.set('adlcp:scormType', 'sco')
            resource.set('href', str(sco_file['path']))
            
            # Файлы ресурса
            file_elem = ET.SubElement(resource, 'file')
            file_elem.set('href', str(sco_file['path']))
            
            file_scorm = ET.SubElement(resource, 'file')
            file_scorm.set('href', 'SCORM_API_wrapper.js')
            
            for res_file in resource_files:
                file_res = ET.SubElement(resource, 'file')
                file_res.set('href', str(res_file['path']))
        
        return manifest
    
    def _apply_sequencing_config(self, item: ET.Element, config: dict, is_first: bool):
        """Применяет настройки sequencing и completion к item"""
        # Completion threshold
        if config.get('progressCompletion', {}).get('completionThreshold'):
            threshold = config.get('progressCompletion', {}).get('completionThreshold', 80)
            if threshold > 0:
                sequencing = item.find('adlseq:sequencing')
                if sequencing is None:
                    sequencing = ET.SubElement(item, 'adlseq:sequencing')
                
                rollup_rules = ET.SubElement(sequencing, 'adlseq:rollupRules')
                rollup_condition = ET.SubElement(rollup_rules, 'adlseq:rollupCondition')
                rollup_condition.set('condition', 'completed')
                
                objectives = ET.SubElement(sequencing, 'adlseq:objectives')
                primary_objective = ET.SubElement(objectives, 'adlseq:primaryObjective')
                primary_objective.set('satisfiedByMeasure', 'true')
                
                min_normalized_measure = ET.SubElement(primary_objective, 'adlseq:minNormalizedMeasure')
                min_normalized_measure.text = str(threshold / 100.0)
    
    def _create_scorm_api_wrapper(self) -> str:
        """Создаёт SCORM API wrapper"""
        return """/* SCORM API Wrapper - pipwerks SCORM wrapper for SCORM 1.2 and 2004 */
var pipwerks = {};
pipwerks.SCORM = {
    version: null,
    handleCompletionStatus: true,
    handleExitMode: true,
    API: { handle: null, isPresent: false },
    connection: { isActive: false },
    data: { completionStatus: null, exitStatus: null },
    debug: { isActive: false },
    
    init: function() {
        var API = this.getAPI();
        if (API) {
            this.API.handle = API.handle;
            this.API.isPresent = true;
            this.connection.isActive = true;
            this.data.completionStatus = this.get("cmi.core.lesson_status");
            this.data.exitStatus = this.get("cmi.core.exit");
            return true;
        }
        return false;
    },
    
    getAPI: function() {
        var API = null,
            findAttempts = 0,
            findAttemptLimit = 500;
        
        while ((!window.API && !window.API_1484_11) && (findAttempts < findAttemptLimit)) {
            if (window.parent && window.parent != window) {
                try {
                    findAttempts++;
                    if (window.parent.API) {
                        API = { handle: window.parent.API, version: "1.2" };
                    } else if (window.parent.API_1484_11) {
                        API = { handle: window.parent.API_1484_11, version: "2004" };
                    }
                } catch (e) {}
            }
            if (!API) {
                var scorm = window;
                while (scorm.parent && scorm.parent != scorm) {
                    try {
                        scorm = scorm.parent;
                        if (scorm.API) {
                            API = { handle: scorm.API, version: "1.2" };
                            break;
                        } else if (scorm.API_1484_11) {
                            API = { handle: scorm.API_1484_11, version: "2004" };
                            break;
                        }
                    } catch (e) {}
                }
            }
        }
        return API;
    },
    
    get: function(parameter) {
        var value = null;
        if (this.API.isPresent) {
            if (this.version === "2004") {
                value = this.API.handle.GetValue(parameter);
                if (this.API.handle.GetLastError() != 0) {
                    return null;
                }
            } else {
                value = this.API.handle.LMSGetValue(parameter);
                var errorCode = this.API.handle.LMSGetLastError();
                if (errorCode != 0) {
                    return null;
                }
            }
        }
        return String(value);
    },
    
    set: function(parameter, value) {
        if (this.API.isPresent) {
            if (this.version === "2004") {
                var result = this.API.handle.SetValue(parameter, value);
                if (result) {
                    if (this.API.handle.Commit("") != "true") {
                        return false;
                    }
                } else {
                    return false;
                }
            } else {
                var result = this.API.handle.LMSSetValue(parameter, value);
                if (result) {
                    if (this.API.handle.LMSCommit("") != "true") {
                        return false;
                    }
                } else {
                    return false;
                }
            }
            return true;
        }
        return false;
    },
    
    save: function() {
        return this.commit();
    },
    
    commit: function() {
        if (this.API.isPresent) {
            if (this.version === "2004") {
                return this.API.handle.Commit("");
            } else {
                return this.API.handle.LMSCommit("");
            }
        }
        return false;
    },
    
    quit: function() {
        if (this.API.isPresent) {
            if (this.version === "2004") {
                return this.API.handle.Terminate("");
            } else {
                return this.API.handle.LMSFinish("");
            }
        }
        return false;
    }
};

pipwerks.UTILS = {
    trace: function(msg) {
        // Отключено для production
    }
};"""

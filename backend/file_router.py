#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Роутер файлов - определяет тип файла и вызывает соответствующий конвертер
"""

from pathlib import Path
from typing import Dict, Optional, List, Any


class FileRouter:
    """Роутер для определения типа файла и вызова соответствующего конвертера"""
    
    def __init__(self):
        self.converters: Dict[str, Any] = {}
        self.file_type_map = {
            # Только PDF
            'pdf': 'pdf',
        }
    
    def register_converter(self, file_type: str, converter: Any):
        """Регистрирует конвертер для типа файла"""
        self.converters[file_type] = converter
    
    def get_converter(self, file_extension: str) -> Optional[Any]:
        """Получает конвертер для расширения файла"""
        file_type = self.file_type_map.get(file_extension.lower())
        if file_type:
            return self.converters.get(file_type)
        return None
    
    def get_file_type(self, file_path: Path) -> str:
        """Определяет тип файла по расширению"""
        ext = file_path.suffix[1:].lower()
        return self.file_type_map.get(ext, 'unknown')
    
    def process_files(self, files: List[Dict], config: Optional[Dict] = None) -> List[Dict]:
        """
        Обрабатывает список файлов, объединяя их в единое пространство
        
        Args:
            files: Список словарей с информацией о файлах
                  [{'path': Path, 'name': str, 'type': str, 'is_launch': bool}, ...]
            config: Конфигурация SCORM из фронтенда
        
        Returns:
            Список обработанных файлов, готовых для сборки SCORM
        """
        processed = []
        
        # Группируем файлы по типам
        files_by_type = {}
        for file_info in files:
            file_path = file_info['path']
            file_type = self.get_file_type(file_path)
            
            if file_type not in files_by_type:
                files_by_type[file_type] = []
            files_by_type[file_type].append(file_info)
        
        # Обрабатываем каждый тип файлов
        for file_type, type_files in files_by_type.items():
            converter = self.converters.get(file_type)
            
            if converter:
                # Если есть конвертер, обрабатываем через него
                for file_info in type_files:
                    try:
                        # Для PDF конвертера передаём selected_pages
                        if file_type == 'pdf' and hasattr(converter, 'convert'):
                            selected_pages = file_info.get('selected_pages')
                            converted = converter.convert(
                                file_info['path'],
                                file_info['path'].parent,
                                selected_pages=selected_pages
                            )
                        # Передаём config в конвертер, если он поддерживает это
                        elif hasattr(converter, 'convert_with_config'):
                            converted = converter.convert_with_config(
                                file_info['path'], 
                                file_info['path'].parent,
                                config
                            )
                        else:
                            converted = converter.convert(file_info['path'], file_info['path'].parent)
                            
                            # Применяем настройки к HTML контенту
                            if isinstance(converted, dict) and converted.get('html_content'):
                                # Обновляем HTML контент с настройками
                                updated_html = self._apply_config_to_html(
                                    converted['html_content'], config
                                )
                                # Сохраняем обновлённый HTML в файл
                                if converted.get('path'):
                                    with open(converted['path'], 'w', encoding='utf-8') as f:
                                        f.write(updated_html)
                                converted['html_content'] = updated_html
                            elif isinstance(converted, list):
                                for item in converted:
                                    if isinstance(item, dict) and item.get('html_content'):
                                        # Обновляем HTML контент с настройками
                                        updated_html = self._apply_config_to_html(
                                            item['html_content'], config
                                        )
                                        # Сохраняем обновлённый HTML в файл
                                        if item.get('path'):
                                            with open(item['path'], 'w', encoding='utf-8') as f:
                                                f.write(updated_html)
                                        item['html_content'] = updated_html
                        
                        if isinstance(converted, list):
                            processed.extend(converted)
                        else:
                            processed.append(converted)
                    except Exception as e:
                        # В случае ошибки просто добавляем файл как ресурс
                        processed.append({
                            'path': file_info['path'],
                            'type': 'resource',
                            'original_name': file_info['name'],
                        })
            else:
                # Если конвертера нет, просто добавляем файлы как ресурсы
                for file_info in type_files:
                    processed.append({
                        'path': file_info['path'],
                        'type': 'resource',
                        'original_name': file_info['name'],
                    })
        
        return processed
    
    def _apply_config_to_html(self, html_content: str, config: Optional[Dict]) -> str:
        """Применяет настройки SCORM к HTML контенту"""
        if not config:
            return html_content
        
        import json
        import re
        
        # Применяем настройки дизайна к CSS
        player_style = config.get('playerStyle', {})
        primary_color = player_style.get('primaryColor', '#4CAF50')
        accent_color = player_style.get('accentColor', '#8b5cf6')
        theme = player_style.get('theme', 'auto')
        high_contrast = player_style.get('highContrast', False)
        large_font = player_style.get('largeFont', False)
        transition_type = player_style.get('transitionType', 'fade')
        
        # Обновляем цвета в CSS
        html_content = re.sub(
            r'background-color:\s*#4CAF50',
            f'background-color: {primary_color}',
            html_content
        )
        html_content = re.sub(
            r'background-color:\s*#2c3e50',
            f'background-color: {"#1a1a1a" if theme == "dark" or (theme == "auto" and high_contrast) else "#2c3e50"}',
            html_content
        )
        
        # Добавляем стили для больших шрифтов
        if large_font:
            font_style = """
        body { font-size: 1.2em; }
        .header h1 { font-size: 26px; }
        .page-info { font-size: 16px; }
        """
            html_content = html_content.replace('</style>', font_style + '</style>')
        
        # Инжектируем конфигурацию в JavaScript
        config_data = {
            'progressCompletion': {
                'rememberLastPage': config.get('progressCompletion', {}).get('rememberLastPage', True),
                'saveOnEachTransition': config.get('progressCompletion', {}).get('saveOnEachTransition', True),
                'askOnReentry': config.get('progressCompletion', {}).get('askOnReentry', False),
                'progressMethod': config.get('progressCompletion', {}).get('progressMethod', 'screens'),
                'completionThreshold': config.get('progressCompletion', {}).get('completionThreshold', 80),
                'successCriterion': config.get('progressCompletion', {}).get('successCriterion', 'score')
            },
        }
        
        config_json = json.dumps(config_data, ensure_ascii=False)
        
        # Вставляем конфигурацию ПЕРЕД определением функций, чтобы они могли её использовать
        config_script = f"""
        <script>
        // SCORM Configuration from frontend - ДОЛЖНО БЫТЬ ПЕРЕД ВСЕМИ ФУНКЦИЯМИ
        window.SCORM_CONFIG = {config_json};
        </script>
        """
        
        # Вставляем скрипт с конфигурацией ПЕРЕД закрывающим тегом </head> или перед <script src="SCORM_API_wrapper.js">
        # Важно: конфигурация должна быть ПЕРЕД всеми скриптами, чтобы функции могли её использовать
        if '<script src="SCORM_API_wrapper.js">' in html_content:
            html_content = html_content.replace(
                '<script src="SCORM_API_wrapper.js">',
                config_script + '<script src="SCORM_API_wrapper.js">'
            )
        elif '<script' in html_content:
            # Вставляем перед первым скриптом
            import re
            html_content = re.sub(r'<script', config_script + '<script', html_content, count=1, flags=re.IGNORECASE)
        elif '</head>' in html_content:
            html_content = html_content.replace('</head>', config_script + '</head>')
        elif '<body>' in html_content:
            html_content = html_content.replace('<body>', config_script + '<body>')
        else:
            html_content = config_script + html_content
        
        # Проверяем, что конфигурация действительно вставлена
        if 'window.SCORM_CONFIG' not in html_content:
            # Если не вставлена, добавляем в начало body
            if '<body>' in html_content:
                html_content = html_content.replace('<body>', '<body>' + config_script)
            else:
                html_content = config_script + html_content
        
        return html_content


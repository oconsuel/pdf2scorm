#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Сборщик SCORM 2004 пакетов
Режим lecture_based: из модели Lecture
"""

import zipfile
import shutil
from pathlib import Path
from xml.etree import ElementTree as ET
from xml.dom import minidom
from typing import Optional
import logging

SCORM_LABELS = {
    'ru': {'page': 'Страница', 'content': 'Содержание'},
    'en': {'page': 'Page', 'content': 'Content'},
}


def _page_label(lang: str, num: int) -> str:
    labels = SCORM_LABELS.get(lang, SCORM_LABELS['ru'])
    return f"{labels['page']} {num}"


def _content_label(lang: str) -> str:
    return SCORM_LABELS.get(lang, SCORM_LABELS['ru'])['content']


from .models.lecture_model import (
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
            
            scorm_lang = config.get('language') or getattr(lecture, 'language', 'ru') or 'ru'
            page_files = []
            for idx, page in enumerate(all_pages, 1):
                html_content = self._render_page_html(page, all_pages, config, scorm_lang)
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
                config=config,
                scorm_lang=scorm_lang,
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
    
    def _render_page_html(self, page: LecturePage, all_pages: list, config: dict, scorm_lang: str = 'ru') -> str:
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
        
        page_title_text = _page_label(scorm_lang, current_index + 1)
        html = f"""<!DOCTYPE html>
<html lang="{scorm_lang}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{page_title_text}</title>
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
</head>
<body>
    <div class="container">
        <div class="content">
            {content_html}
        </div>
    </div>
    
    <script>
    (function() {{
        var scorm = (typeof pipwerks !== 'undefined' && pipwerks.SCORM) ? pipwerks.SCORM : null;
        if (!scorm) return;

        var done = false;
        var started = Date.now();

        function init() {{
            if (done) return;
            scorm.version = "2004";
            if (!scorm.init()) return;
            done = true;
            started = Date.now();

            scorm.set("cmi.completion_status", "completed");
            scorm.set("cmi.success_status", "passed");
            scorm.set("cmi.score.scaled", "1");
            scorm.set("cmi.score.raw", "100");
            scorm.set("cmi.score.min", "0");
            scorm.set("cmi.score.max", "100");
            scorm.set("cmi.progress_measure", "1");
            scorm.set("cmi.location", "{current_index + 1}");
            scorm.set("cmi.exit", "suspend");
            scorm.save();
        }}

        window.addEventListener("load", init);

        window.addEventListener("beforeunload", function() {{
            if (!done) return;
            try {{
                var t = Math.floor((Date.now() - started) / 1000);
                var h = Math.floor(t / 3600);
                var m = Math.floor((t % 3600) / 60);
                var s = t % 60;
                scorm.set("cmi.session_time", "PT" + h + "H" + m + "M" + s + "S");
                scorm.save();
            }} catch(e) {{}}
        }});
    }})();
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
    
    def _create_manifest_from_lecture(self, lecture: Lecture, page_files: list, 
                                     image_files: list, config: dict,
                                     scorm_lang: str = 'ru') -> ET.Element:
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
        
        org_seq = ET.SubElement(organization, 'imsss:sequencing')
        ctrl = ET.SubElement(org_seq, 'imsss:controlMode')
        ctrl.set('choice', 'true')
        ctrl.set('choiceExit', 'true')
        ctrl.set('flow', 'true')
        ctrl.set('forwardOnly', 'false')
        
        # Resources
        resources = ET.SubElement(manifest, 'resources')
        
        # Создаём items для разделов и страниц
        all_pages = lecture.get_all_pages()
        page_counter = 0
        
        for section in lecture.sections:
            section_item_id = f'SECTION_{section.id}'
            section_item = ET.SubElement(organization, 'item')
            section_item.set('identifier', section_item_id)
            section_title = ET.SubElement(section_item, 'title')
            section_title.text = section.title
            
            # Sequencing on section to allow choice/flow among its children
            sec_seq = ET.SubElement(section_item, 'imsss:sequencing')
            sec_ctrl = ET.SubElement(sec_seq, 'imsss:controlMode')
            sec_ctrl.set('choice', 'true')
            sec_ctrl.set('choiceExit', 'true')
            sec_ctrl.set('flow', 'true')
            sec_ctrl.set('forwardOnly', 'false')
            
            for page in section.pages:
                page_counter += 1
                page_item_id = f'PAGE_{page.id}'
                resource_id = f'RES_PAGE_{page_counter}'
                
                page_item = ET.SubElement(section_item, 'item')
                page_item.set('identifier', page_item_id)
                page_item.set('identifierref', resource_id)
                page_title = ET.SubElement(page_item, 'title')
                page_title.text = _page_label(scorm_lang, page_counter)
                
                item_seq = ET.SubElement(page_item, 'imsss:sequencing')
                dc = ET.SubElement(item_seq, 'imsss:deliveryControls')
                dc.set('completionSetByContent', 'true')
                dc.set('objectiveSetByContent', 'true')
                
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
    
    def _create_scorm_api_wrapper(self) -> str:
        """Создаёт SCORM API wrapper"""
        return r"""var pipwerks={};
pipwerks.SCORM={
    version:null,
    API:{handle:null,isPresent:false},
    connection:{isActive:false},

    init:function(){
        var a=this.getAPI();
        if(!a) return false;
        this.API.handle=a.handle;
        this.API.isPresent=true;
        var ok;
        if(this.version==="2004"){
            ok=this.API.handle.Initialize("");
        }else{
            ok=this.API.handle.LMSInitialize("");
        }
        if(ok==="true"||ok===true){
            this.connection.isActive=true;
            return true;
        }
        return false;
    },

    getAPI:function(){
        var w=window,a=null,n=0;
        while(!a&&n<500){
            try{
                if(w.API_1484_11) a={handle:w.API_1484_11,version:"2004"};
                else if(w.API) a={handle:w.API,version:"1.2"};
            }catch(e){}
            if(!a&&w.parent&&w.parent!==w){w=w.parent;n++;}
            else break;
        }
        if(!a){
            try{
                var op=window.opener;
                while(op&&!a&&n<500){
                    if(op.API_1484_11) a={handle:op.API_1484_11,version:"2004"};
                    else if(op.API) a={handle:op.API,version:"1.2"};
                    if(!a&&op.parent&&op.parent!==op){op=op.parent;n++;}
                    else break;
                }
            }catch(e){}
        }
        return a;
    },

    get:function(p){
        if(!this.connection.isActive) return "";
        try{
            if(this.version==="2004") return String(this.API.handle.GetValue(p));
            return String(this.API.handle.LMSGetValue(p));
        }catch(e){return "";}
    },

    set:function(p,v){
        if(!this.connection.isActive) return false;
        try{
            if(this.version==="2004") return this.API.handle.SetValue(p,String(v));
            return this.API.handle.LMSSetValue(p,String(v));
        }catch(e){return false;}
    },

    save:function(){
        if(!this.connection.isActive) return false;
        try{
            if(this.version==="2004") return this.API.handle.Commit("");
            return this.API.handle.LMSCommit("");
        }catch(e){return false;}
    },

    quit:function(){
        if(!this.connection.isActive) return false;
        this.connection.isActive=false;
        try{
            if(this.version==="2004") return this.API.handle.Terminate("");
            return this.API.handle.LMSFinish("");
        }catch(e){return false;}
    }
};
pipwerks.UTILS={trace:function(m){if(console&&console.log)console.log(m)}};"""

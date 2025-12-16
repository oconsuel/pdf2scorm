#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Сборщик SCORM 2004 пакетов
Создаёт imsmanifest.xml и собирает все файлы в ZIP
"""

import zipfile
import shutil
from pathlib import Path
from xml.etree import ElementTree as ET
from xml.dom import minidom
import sys

# Добавляем родительскую директорию в путь для импорта SCORM API wrapper
sys.path.insert(0, str(Path(__file__).parent.parent))


class SCORMBuilder:
    """Сборщик SCORM 2004 пакетов"""
    
    def __init__(self):
        self.scorm_version = '2004'
    
    def build(self, processed_files: list, launch_file: str, config: dict, 
              output_dir: Path, course_title: str) -> Path:
        """
        Собирает SCORM 2004 пакет из обработанных файлов
        
        Args:
            processed_files: Список обработанных файлов
            launch_file: Имя launch файла
            config: Конфигурация SCORM из фронтенда
            output_dir: Директория для выходного файла
            course_title: Название курса
        
        Returns:
            Путь к созданному ZIP файлу
        """
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
    
    def _create_manifest_2004(self, files_in_package: list, launch_file: str,
                              course_title: str, config: dict) -> ET.Element:
        """Создаёт SCORM 2004 manifest с учётом конфигурации"""
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
            # Ищем launch файл среди всех файлов
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
                # Пробуем найти первый HTML файл
                html_files = [f for f in files_in_package if str(f['path']).endswith('.html')]
                if html_files:
                    html_files.sort(key=lambda x: str(x['path']))
                    launch_file_path = html_files[0]['path']
                    sco_files = [{
                        'path': launch_file_path,
                        'original_name': launch_file_path.name,
                    }]
        
        # Сортируем SCO файлы по номеру страницы (числовая сортировка)
        def get_page_number(file_path):
            """Извлекает номер страницы из имени файла для числовой сортировки"""
            import re
            path_str = str(file_path)
            match = re.search(r'page_(\d+)\.html', path_str)
            if match:
                return int(match.group(1))
            # Если не найден номер, используем строковую сортировку
            return float('inf')
        
        sco_files_sorted = sorted(sco_files, key=lambda x: get_page_number(x['path']))
        
        # Создаём items и resources для SCO
        for idx, sco_file in enumerate(sco_files_sorted, 1):
            item_id = f'ITEM_SCO_{idx}'
            resource_id = f'RES_SCO_{idx}'
            
            # Проверяем, является ли это launch файлом
            is_launch = (str(sco_file['path']) == launch_file or 
                        sco_file['path'].name == launch_file or
                        (idx == 1 and launch_file in str(sco_file['path'])))
            
            
            # Item
            item = ET.SubElement(organization, 'item')
            item.set('identifier', item_id)
            item.set('identifierref', resource_id)
            item_title = ET.SubElement(item, 'title')
            item_title.text = sco_file.get('original_name', str(sco_file['path']))
            
            # Применяем настройки sequencing и completion из config
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
            
            # SCORM API wrapper
            file_scorm = ET.SubElement(resource, 'file')
            file_scorm.set('href', 'SCORM_API_wrapper.js')
            
            # Добавляем связанные ресурсы (все файлы в той же директории)
            for res_file in resource_files:
                file_res = ET.SubElement(resource, 'file')
                file_res.set('href', str(res_file['path']))
        
        return manifest
    
    def _apply_sequencing_config(self, item: ET.Element, config: dict, is_first: bool):
        """Применяет настройки sequencing и completion к item"""
        # Sequencing rules
        if config.get('navigation', {}).get('preventSkipUntilComplete', False):
            sequencing = ET.SubElement(item, 'adlseq:sequencing')
            
            # Control mode
            control_mode = ET.SubElement(sequencing, 'adlseq:controlMode')
            control_mode.set('choice', 'false')
            control_mode.set('choiceExit', 'false')
            control_mode.set('flow', 'true' if config.get('navigation', {}).get('navigationType') == 'linear' else 'false')
            control_mode.set('forwardOnly', 'true' if config.get('navigation', {}).get('preventSkipUntilComplete') else 'false')
        
        # Completion threshold
        if config.get('progressCompletion', {}).get('completionThreshold'):
            threshold = config.get('progressCompletion', {}).get('completionThreshold', 80)
            if threshold > 0:
                sequencing = item.find('adlseq:sequencing')
                if sequencing is None:
                    sequencing = ET.SubElement(item, 'adlseq:sequencing')
                
                # Rollup rules
                rollup_rules = ET.SubElement(sequencing, 'adlseq:rollupRules')
                rollup_condition = ET.SubElement(rollup_rules, 'adlseq:rollupCondition')
                rollup_condition.set('condition', 'completed')
                
                # Objective
                objectives = ET.SubElement(sequencing, 'adlseq:objectives')
                primary_objective = ET.SubElement(objectives, 'adlseq:primaryObjective')
                primary_objective.set('satisfiedByMeasure', 'true')
                
                min_normalized_measure = ET.SubElement(primary_objective, 'adlseq:minNormalizedMeasure')
                min_normalized_measure.text = str(threshold / 100.0)
    
    def _create_scorm_api_wrapper(self) -> str:
        """Создаёт SCORM API wrapper"""
        # Используем тот же wrapper, что и в оригинальном скрипте
        return """/* SCORM API Wrapper - pipwerks SCORM wrapper for SCORM 1.2 and 2004 */
var pipwerks = {};
pipwerks.SCORM = {
    version: null,
    handleCompletionStatus: true,
    handleExitMode: true,
    API: { handle: null, isPresent: false },
    connection: { isActive: false },
    data: { completionStatus: null, exitStatus: null },
    debug: { isActive: true },
    
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
            findAttemptLimit = 500,
            trace = pipwerks.UTILS.trace;
        
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
                    if (this.debug.isActive) {
                        console.log("SCORM.get failed: " + this.API.handle.GetErrorString(this.API.handle.GetLastError()));
                    }
                    return null;
                }
            } else {
                value = this.API.handle.LMSGetValue(parameter);
                var errorCode = this.API.handle.LMSGetLastError();
                if (errorCode != 0) {
                    if (this.debug.isActive) {
                        console.log("SCORM.get failed: " + this.API.handle.LMSGetErrorString(errorCode));
                    }
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
                        if (this.debug.isActive) {
                            console.log("SCORM.set failed to commit: " + this.API.handle.GetErrorString(this.API.handle.GetLastError()));
                        }
                        return false;
                    }
                } else {
                    if (this.debug.isActive) {
                        console.log("SCORM.set failed: " + this.API.handle.GetErrorString(this.API.handle.GetLastError()));
                    }
                    return false;
                }
            } else {
                var result = this.API.handle.LMSSetValue(parameter, value);
                if (result) {
                    if (this.API.handle.LMSCommit("") != "true") {
                        if (this.debug.isActive) {
                            console.log("SCORM.set failed to commit: " + this.API.handle.LMSGetErrorString(this.API.handle.LMSGetLastError()));
                        }
                        return false;
                    }
                } else {
                    if (this.debug.isActive) {
                        console.log("SCORM.set failed: " + this.API.handle.LMSGetErrorString(this.API.handle.LMSGetLastError()));
                    }
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
        if (console && console.log) {
            console.log(msg);
        }
    }
};"""


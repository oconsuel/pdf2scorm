#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для конвертации PDF файла в SCORM-пакет
Конвертирует PDF в SCORM 1.2 или SCORM 2004 формат
"""

import os
import sys
import zipfile
import shutil
from pathlib import Path
from datetime import datetime
from xml.etree import ElementTree as ET
from xml.dom import minidom

try:
    import fitz  # PyMuPDF
    PDF_TO_IMAGE = 'pymupdf'
except ImportError:
    try:
        from pdf2image import convert_from_path
        PDF_TO_IMAGE = 'pdf2image'
    except ImportError:
        PDF_TO_IMAGE = None


class PDFToSCORM:
    """Класс для конвертации PDF в SCORM-пакет"""
    
    def __init__(self, pdf_path, output_dir=None, scorm_version='1.2', title=None):
        """
        Инициализация конвертера
        
        Args:
            pdf_path: Путь к PDF файлу
            output_dir: Директория для выходного файла (по умолчанию - та же, что и PDF)
            scorm_version: Версия SCORM ('1.2' или '2004')
            title: Название курса (по умолчанию - имя PDF файла)
        """
        self.pdf_path = Path(pdf_path)
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF файл не найден: {pdf_path}")
        
        if output_dir is None:
            output_dir = self.pdf_path.parent
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.scorm_version = scorm_version
        self.title = title or self.pdf_path.stem
        
        # Создаем временную директорию для сборки пакета
        self.temp_dir = self.output_dir / f"{self.title}_scorm_temp"
        
    def convert_pdf_to_images(self):
        """Конвертирует страницы PDF в изображения"""
        if PDF_TO_IMAGE is None:
            raise ImportError(
                "Необходимо установить библиотеку для конвертации PDF в изображения:\n"
                "pip install PyMuPDF\n"
                "или\n"
                "pip install pdf2image\n"
                "(для pdf2image также требуется poppler: brew install poppler на macOS)"
            )
        
        image_paths = []
        images_dir = self.temp_dir / 'images'
        images_dir.mkdir(parents=True, exist_ok=True)
        
        if PDF_TO_IMAGE == 'pymupdf':
            # Используем PyMuPDF
            pdf_document = fitz.open(self.pdf_path)
            num_pages = len(pdf_document)
            
            for page_num in range(num_pages):
                page = pdf_document[page_num]
                # Увеличиваем разрешение для лучшего качества
                mat = fitz.Matrix(2.0, 2.0)  # 2x zoom для 144 DPI примерно
                pix = page.get_pixmap(matrix=mat)
                image_path = images_dir / f'page_{page_num + 1}.png'
                pix.save(image_path)
                image_paths.append(image_path)
            
            pdf_document.close()
            
        else:  # pdf2image
            # Используем pdf2image
            images = convert_from_path(str(self.pdf_path), dpi=200)
            
            for i, image in enumerate(images):
                image_path = images_dir / f'page_{i + 1}.png'
                image.save(image_path, 'PNG')
                image_paths.append(image_path)
        
        return image_paths
    
    def create_slide_html(self, page_num, total_pages, image_filename):
        """Создает отдельный HTML файл для одной страницы (SCO)"""
        # Определяем поля SCORM в зависимости от версии
        scorm_version_var = self.scorm_version
        html_content = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.title} - Страница {page_num}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        html, body {{
            height: 100%;
            overflow: hidden;
        }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #2c3e50;
            display: flex;
            flex-direction: column;
        }}
        .header {{
            background-color: #4CAF50;
            color: white;
            padding: 15px 30px;
            text-align: center;
            flex-shrink: 0;
            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
        }}
        .header h1 {{
            font-size: 22px;
            font-weight: 500;
        }}
        .slide-container {{
            flex: 1;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: auto;
            background-color: #34495e;
            padding: 15px;
            min-height: 0;
        }}
        .slide-content {{
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
            overflow: visible;
            display: flex;
            align-items: center;
            justify-content: center;
            animation: fadeIn 0.3s ease-in;
            width: auto;
            height: auto;
            max-width: 100%;
            max-height: 100%;
        }}
        @keyframes fadeIn {{
            from {{
                opacity: 0;
            }}
            to {{
                opacity: 1;
            }}
        }}
        .page-image {{
            max-width: calc(100vw - 50px);
            max-height: calc(100vh - 150px);
            width: auto;
            height: auto;
            display: block;
            object-fit: contain;
        }}
        @media (max-width: 768px) {{
            .slide-container {{
                padding: 10px;
            }}
            .page-image {{
                max-width: calc(100vw - 40px);
                max-height: calc(100vh - 120px);
            }}
        }}
        .page-info {{
            background-color: #2c3e50;
            color: white;
            padding: 10px 30px;
            text-align: center;
            font-size: 14px;
            flex-shrink: 0;
        }}
        @media (max-width: 768px) {{
            .header h1 {{
                font-size: 18px;
            }}
            .page-info {{
                font-size: 12px;
                padding: 8px 15px;
            }}
            .slide-container {{
                padding: 10px;
            }}
        }}
    </style>
    <script src="SCORM_API_wrapper.js"></script>
</head>
<body>
    <div class="header">
        <h1>{self.title}</h1>
    </div>
    <div class="slide-container">
        <div class="slide-content">
            <img src="images/{image_filename}" alt="Страница {page_num}" class="page-image" />
        </div>
    </div>
    <div class="page-info">
        Страница {page_num} из {total_pages}
    </div>
    
    <script>
        var scorm = pipwerks.SCORM;
        var pageNum = {page_num};
        var totalPages = {total_pages};
        var sessionStartTime = null;
        var initialized = false;
        var scormVersion = "{scorm_version_var}";
        
        // Определяем поля API в зависимости от версии SCORM
        function getStatusField() {{
            return scormVersion === "2004" ? "cmi.completion_status" : "cmi.core.lesson_status";
        }}
        function getLocationField() {{
            return scormVersion === "2004" ? "cmi.location" : "cmi.core.lesson_location";
        }}
        function getSessionTimeField() {{
            return scormVersion === "2004" ? "cmi.session_time" : "cmi.core.session_time";
        }}
        function getSuspendDataField() {{
            return scormVersion === "2004" ? "cmi.suspend_data" : "cmi.suspend_data";
        }}
        
        // Инициализация SCORM API
        function initializeSCORM() {{
            if (initialized) return;
            
            scorm.version = scormVersion;
            var initResult = scorm.init();
            
            if (initResult) {{
                initialized = true;
                sessionStartTime = new Date().getTime();
                
                // Получаем текущий статус
                var currentStatus = scorm.get(getStatusField());
                
                // Если статус не установлен, устанавливаем начальный статус
                if (!currentStatus || currentStatus === "" || currentStatus === "null") {{
                    if (scormVersion === "2004") {{
                        scorm.set(getStatusField(), "unknown");
                    }} else {{
                        scorm.set(getStatusField(), "not attempted");
                    }}
                }}
                
                // Если это первая загрузка, отмечаем как "incomplete" или "incomplete"
                if (!currentStatus || currentStatus === "" || currentStatus === "null" || 
                    currentStatus === "not attempted" || currentStatus === "unknown") {{
                    if (scormVersion === "2004") {{
                        scorm.set(getStatusField(), "incomplete");
                    }} else {{
                        scorm.set(getStatusField(), "incomplete");
                    }}
                }}
                
                // Загружаем сохраненный прогресс и возвращаемся к последней странице
                loadProgress();
                
                // Сохраняем прогресс сразу при загрузке
                saveProgress();
            }}
        }}
        
        // Загрузка прогресса
        function loadProgress() {{
            try {{
                // Проверяем настройки rememberLastPage
                var rememberLastPage = true;
                if (window.SCORM_CONFIG && window.SCORM_CONFIG.progressCompletion) {{
                    rememberLastPage = window.SCORM_CONFIG.progressCompletion.rememberLastPage;
                }}
                
                if (!rememberLastPage) {{
                    return; // Не загружаем прогресс, если настройка отключена
                }}
                
                // Пытаемся загрузить последнюю посещенную страницу из location
                var lastLocation = scorm.get(getLocationField());
                if (lastLocation && lastLocation !== "" && lastLocation !== "null") {{
                    var lastPage = parseInt(lastLocation);
                    if (!isNaN(lastPage) && lastPage > 0 && lastPage <= totalPages) {{
                        // Сохраняем информацию о последней странице для использования
                        window.lastVisitedPage = lastPage;
                    }}
                }}
                
                // Загружаем suspend_data для восстановления полного прогресса
                var suspendData = scorm.get(getSuspendDataField());
                if (suspendData && suspendData !== "" && suspendData !== "null") {{
                    try {{
                        var progressData = JSON.parse(suspendData);
                        window.progressData = progressData;
                        if (progressData.lastPage && progressData.lastPage > 0) {{
                            window.lastVisitedPage = progressData.lastPage;
                        }}
                    }} catch (e) {{
                        console.log("Ошибка парсинга suspend_data:", e);
                    }}
                }}
            }} catch (e) {{
                console.log("Не удалось загрузить прогресс:", e);
            }}
        }}
        
        // Сохранение прогресса
        function saveProgress() {{
            if (!scorm.API.isPresent || !initialized) return;
            
            // Проверяем настройку saveOnEachTransition
            var saveOnEachTransition = true;
            if (window.SCORM_CONFIG && window.SCORM_CONFIG.progressCompletion) {{
                saveOnEachTransition = window.SCORM_CONFIG.progressCompletion.saveOnEachTransition;
            }}
            
            // Если автосохранение отключено, сохраняем только при явном вызове
            if (!saveOnEachTransition && arguments.length === 0) {{
                return; // Пропускаем автоматическое сохранение
            }}
            
            try {{
                // Сохраняем номер текущей страницы в location
                // Это ключевое поле для возврата к последней странице
                // В SCORM 2004 location используется для восстановления позиции
                var locationValue = pageNum.toString();
                scorm.set(getLocationField(), locationValue);
                
                // Дополнительно сохраняем в формате, который Moodle может использовать
                // для определения последней посещенной страницы
                if (scormVersion === "2004") {{
                    // В SCORM 2004 также можно использовать cmi.progress_measure
                    var progressMeasure = pageNum / totalPages;
                    try {{
                        scorm.set("cmi.progress_measure", progressMeasure.toString());
                    }} catch (e) {{
                        // Если поле не поддерживается, игнорируем
                    }}
                }}
                
                // Получаем и обновляем suspend_data с информацией о прогрессе
                var suspendData = scorm.get(getSuspendDataField());
                var progressData = {{}};
                
                // Пытаемся загрузить существующие данные
                if (suspendData && suspendData !== "" && suspendData !== "null") {{
                    try {{
                        progressData = JSON.parse(suspendData);
                    }} catch (e) {{
                        progressData = {{ visitedPages: [], lastPage: 0 }};
                    }}
                }} else {{
                    progressData = {{ visitedPages: [], lastPage: 0 }};
                }}
                
                // Инициализируем массивы, если их нет
                if (!progressData.visitedPages) {{
                    progressData.visitedPages = [];
                }}
                
                // Отмечаем текущую страницу как посещенную
                if (progressData.visitedPages.indexOf(pageNum) === -1) {{
                    progressData.visitedPages.push(pageNum);
                }}
                
                // Сохраняем информацию о последней посещенной странице
                progressData.lastPage = pageNum;
                progressData.totalPages = totalPages;
                progressData.lastUpdate = new Date().getTime();
                
                // Сохраняем прогресс в suspend_data
                var progressJSON = JSON.stringify(progressData);
                var maxLength = scormVersion === "2004" ? 64000 : 4096;
                if (progressJSON.length < (maxLength - 100)) {{
                    scorm.set(getSuspendDataField(), progressJSON);
                }}
                
                // Определяем общий прогресс по всем страницам
                var visitedCount = progressData.visitedPages.length;
                
                // Вычисляем прогресс с учётом настроек
                var progress = visitedCount / totalPages;
                var completionThreshold = 1.0; // По умолчанию 100%
                
                if (window.SCORM_CONFIG && window.SCORM_CONFIG.progressCompletion) {{
                    completionThreshold = window.SCORM_CONFIG.progressCompletion.completionThreshold / 100.0;
                    var progressMethod = window.SCORM_CONFIG.progressCompletion.progressMethod;
                    
                    if (progressMethod === 'tasks') {{
                        // Для задач пока используем базовый прогресс
                        progress = visitedCount / totalPages;
                    }} else if (progressMethod === 'combined') {{
                        // Комбинированный: 50% экраны + 50% задачи
                        progress = (visitedCount / totalPages) * 0.5;
                    }}
                }}
                
                // Обновляем статус прохождения с учётом threshold
                var currentStatus = scorm.get(getStatusField());
                
                if (progress >= completionThreshold || visitedCount === totalPages) {{
                    if (scormVersion === "2004") {{
                        scorm.set(getStatusField(), "completed");
                    }} else {{
                        scorm.set(getStatusField(), "completed");
                    }}
                }} else if (currentStatus !== "completed" && visitedCount > 0) {{
                    if (scormVersion === "2004") {{
                        scorm.set(getStatusField(), "incomplete");
                    }} else {{
                        scorm.set(getStatusField(), "incomplete");
                    }}
                }}
                
                // Сохраняем время сессии
                if (sessionStartTime) {{
                    var timeSpent = Math.floor((new Date().getTime() - sessionStartTime) / 1000);
                    if (timeSpent > 0) {{
                        var hours = Math.floor(timeSpent / 3600);
                        var minutes = Math.floor((timeSpent % 3600) / 60);
                        var seconds = timeSpent % 60;
                        var formattedTime = "PT" + hours + "H" + minutes + "M" + seconds + "S";
                        scorm.set(getSessionTimeField(), formattedTime);
                    }}
                }}
                
                // Сохраняем все изменения
                var saveResult = scorm.save();
                if (!saveResult) {{
                    console.log("Предупреждение: не удалось сохранить данные SCORM");
                }}
            }} catch (e) {{
                console.log("Ошибка сохранения SCORM:", e);
            }}
        }}
        
        // Инициализация при загрузке
        window.addEventListener('load', function() {{
            initializeSCORM();
            // Сохраняем прогресс сразу после инициализации
            setTimeout(function() {{
                if (initialized) {{
                    saveProgress();
                }}
            }}, 500);
        }});
        
        // Автосохранение каждые 3 секунды для надежности (если включено)
        window.saveInterval = null;
        if (window.SCORM_CONFIG && window.SCORM_CONFIG.progressCompletion && window.SCORM_CONFIG.progressCompletion.saveOnEachTransition) {{
            window.saveInterval = setInterval(function() {{
                if (initialized) {{
                    saveProgress();
                }}
            }}, 3000);
        }} else {{
            // Если автосохранение отключено, сохраняем только при явных событиях
            window.saveInterval = setInterval(function() {{
                if (initialized) {{
                    // Сохраняем только при явном вызове
                }}
            }}, 30000); // Увеличиваем интервал до 30 секунд
        }}
        
        // Сохранение при закрытии/переходе
        window.addEventListener('beforeunload', function() {{
            if (initialized) {{
                saveProgress();
                scorm.save();
                scorm.quit();
            }}
        }});
        
        // Сохранение при потере фокуса (переключение вкладок)
        document.addEventListener('visibilitychange', function() {{
            if (document.hidden && initialized) {{
                saveProgress();
            }}
        }});
        
        // Сохранение при уходе со страницы
        window.addEventListener('pagehide', function() {{
            if (initialized) {{
                saveProgress();
                scorm.save();
            }}
        }});
    </script>
</body>
</html>
"""
        return html_content
    
    def create_index_html(self, total_pages):
        """Создает индексный HTML файл для SCORM 2004, который перенаправляет на последнюю посещенную страницу"""
        scorm_version_var = self.scorm_version
        html_content = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>{self.title}</title>
    <script src="SCORM_API_wrapper.js"></script>
</head>
<body>
    <p>Загрузка курса...</p>
    <script>
        var scorm = pipwerks.SCORM;
        var scormVersion = "{scorm_version_var}";
        var totalPages = {total_pages};
        
        scorm.version = scormVersion;
        var initResult = scorm.init();
        
        if (initResult) {{
            // Пытаемся найти последнюю посещенную страницу
            var lastPage = 1;
            var locationField = scormVersion === "2004" ? "cmi.location" : "cmi.core.lesson_location";
            
            // Проверяем все SCO, чтобы найти последнюю посещенную
            for (var page = totalPages; page >= 1; page--) {{
                try {{
                    // В SCORM мы не можем напрямую получить данные других SCO
                    // Но Moodle сохраняет location для каждого SCO
                    // Мы попробуем использовать общий механизм через suspend_data
                }} catch (e) {{
                    console.log("Ошибка при проверке страницы " + page);
                }}
            }}
            
            // По умолчанию переходим на первую страницу
            // Moodle сам будет управлять навигацией через manifest
            window.location.href = "page_1.html";
        }} else {{
            // Если SCORM API недоступен, переходим на первую страницу
            window.location.href = "page_1.html";
        }}
    </script>
</body>
</html>
"""
        return html_content
    
    def create_scorm_api_wrapper(self):
        """Создает SCORM API wrapper JavaScript файл"""
        return """/* SCORM API Wrapper - pipwerks SCORM wrapper for SCORM 1.2 */
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
    
    def create_manifest(self, image_paths):
        """Создает SCORM manifest файл (imsmanifest.xml)"""
        if self.scorm_version == '2004':
            return self._create_manifest_2004(image_paths)
        else:
            return self._create_manifest_12(image_paths)
    
    def _create_manifest_12(self, image_paths):
        """Создает SCORM 1.2 manifest, где каждая страница - отдельный SCO"""
        manifest = ET.Element('manifest')
        manifest.set('identifier', f"SCORM_{self.title.replace(' ', '_')}")
        manifest.set('version', '1.1')
        manifest.set('xmlns', 'http://www.imsproject.org/xsd/imscp_rootv1p1p2')
        manifest.set('xmlns:adlcp', 'http://www.adlnet.org/xsd/adlcp_rootv1p2')
        manifest.set('xmlns:xsi', 'http://www.w3.org/2001/XMLSchema-instance')
        manifest.set('xsi:schemaLocation', 
                    'http://www.imsproject.org/xsd/imscp_rootv1p1p2 imscp_rootv1p1p2.xsd '
                    'http://www.imsglobal.org/xsd/imsmd_rootv1p2p1 imsmd_rootv1p2p1.xsd '
                    'http://www.adlnet.org/xsd/adlcp_rootv1p2 adlcp_rootv1p2.xsd')
        
        # Metadata
        metadata = ET.SubElement(manifest, 'metadata')
        schema = ET.SubElement(metadata, 'schema')
        schema.text = 'ADL SCORM'
        schemaversion = ET.SubElement(metadata, 'schemaversion')
        schemaversion.text = '1.2'
        
        # Organizations
        organizations = ET.SubElement(manifest, 'organizations')
        organizations.set('default', 'TOC1')
        organization = ET.SubElement(organizations, 'organization')
        organization.set('identifier', 'TOC1')
        title = ET.SubElement(organization, 'title')
        title.text = self.title
        
        # Resources
        resources = ET.SubElement(manifest, 'resources')
        
        # Создаем отдельный item и resource для каждой страницы
        for i, image_path in enumerate(image_paths, 1):
            page_num = i
            image_filename = image_path.name
            
            # Item для страницы
            item = ET.SubElement(organization, 'item')
            item.set('identifier', f'ITEM_PAGE_{page_num}')
            item.set('identifierref', f'RES_PAGE_{page_num}')
            item_title = ET.SubElement(item, 'title')
            item_title.text = f'{self.title} - Страница {page_num}'
            
            # Resource для страницы
            resource = ET.SubElement(resources, 'resource')
            resource.set('identifier', f'RES_PAGE_{page_num}')
            resource.set('type', 'webcontent')
            resource.set('adlcp:scormtype', 'sco')
            resource.set('href', f'page_{page_num}.html')
            
            # Файлы для ресурса
            file_page = ET.SubElement(resource, 'file')
            file_page.set('href', f'page_{page_num}.html')
            
            file_scorm = ET.SubElement(resource, 'file')
            file_scorm.set('href', 'SCORM_API_wrapper.js')
            
            file_image = ET.SubElement(resource, 'file')
            file_image.set('href', f"images/{image_filename}")
        
        return manifest
    
    def _create_manifest_2004(self, image_paths):
        """Создает SCORM 2004 manifest, где каждая страница - отдельный SCO"""
        manifest = ET.Element('manifest')
        manifest.set('identifier', f"SCORM_{self.title.replace(' ', '_')}")
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
        title.text = self.title
        
        # Resources
        resources = ET.SubElement(manifest, 'resources')
        
        # Создаем отдельный item и resource для каждой страницы
        for i, image_path in enumerate(image_paths, 1):
            page_num = i
            image_filename = image_path.name
            
            # Item для страницы
            item = ET.SubElement(organization, 'item')
            item.set('identifier', f'ITEM_PAGE_{page_num}')
            item.set('identifierref', f'RES_PAGE_{page_num}')
            item_title = ET.SubElement(item, 'title')
            item_title.text = f'{self.title} - Страница {page_num}'
            
            # Resource для страницы
            resource = ET.SubElement(resources, 'resource')
            resource.set('identifier', f'RES_PAGE_{page_num}')
            resource.set('type', 'webcontent')
            resource.set('adlcp:scormType', 'sco')
            resource.set('href', f'page_{page_num}.html')
            
            # Файлы для ресурса
            file_page = ET.SubElement(resource, 'file')
            file_page.set('href', f'page_{page_num}.html')
            
            file_scorm = ET.SubElement(resource, 'file')
            file_scorm.set('href', 'SCORM_API_wrapper.js')
            
            file_image = ET.SubElement(resource, 'file')
            file_image.set('href', f"images/{image_filename}")
        
        return manifest
    
    def convert(self):
        """Основной метод конвертации"""
        print(f"Начало конвертации PDF в SCORM {self.scorm_version}...")
        
        # Создаем временную директорию
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Конвертируем страницы PDF в изображения
            print("Конвертация страниц PDF в изображения...")
            image_paths = self.convert_pdf_to_images()
            total_pages = len(image_paths)
            print(f"Конвертировано {total_pages} страниц в изображения")
            
            # Создаем отдельный HTML файл для каждой страницы
            print("Создание HTML файлов для каждой страницы...")
            html_files = []
            for i, image_path in enumerate(image_paths, 1):
                html_content = self.create_slide_html(i, total_pages, image_path.name)
                html_filename = f'page_{i}.html'
                html_path = self.temp_dir / html_filename
                
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                html_files.append(html_path)
                print(f"  Создан {html_filename}")
            
            # Создаем SCORM API wrapper
            print("Создание SCORM API wrapper...")
            scorm_api = self.create_scorm_api_wrapper()
            api_path = self.temp_dir / 'SCORM_API_wrapper.js'
            with open(api_path, 'w', encoding='utf-8') as f:
                f.write(scorm_api)
            
            # Создаем manifest
            print("Создание manifest файла...")
            manifest = self.create_manifest(image_paths)
            manifest_str = minidom.parseString(ET.tostring(manifest)).toprettyxml(indent="  ", encoding=None)
            manifest_path = self.temp_dir / 'imsmanifest.xml'
            with open(manifest_path, 'w', encoding='utf-8') as f:
                f.write(manifest_str)
            
            # Создаем ZIP архив
            print("Создание ZIP архива...")
            zip_path = self.output_dir / f"{self.title}_SCORM_{self.scorm_version}.zip"
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Добавляем основные файлы
                zipf.write(manifest_path, 'imsmanifest.xml')
                zipf.write(api_path, 'SCORM_API_wrapper.js')
                
                # Добавляем все HTML файлы страниц
                for html_file in html_files:
                    zipf.write(html_file, html_file.name)
                
                # Добавляем все изображения
                for image_path in image_paths:
                    zipf.write(image_path, f"images/{image_path.name}")
            
            print(f"SCORM-пакет успешно создан: {zip_path}")
            
        finally:
            # Удаляем временную директорию
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
        
        return zip_path


def main():
    """Основная функция для запуска из командной строки"""
    if len(sys.argv) < 2:
        print("Использование: python pdf_to_scorm.py <путь_к_pdf> [версия_scorm] [название]")
        print("  версия_scorm: 1.2 (по умолчанию) или 2004")
        print("  название: название курса (по умолчанию - имя файла)")
        print("\nПример:")
        print("  python pdf_to_scorm.py document.pdf")
        print("  python pdf_to_scorm.py document.pdf 2004 'Мой курс'")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    scorm_version = sys.argv[2] if len(sys.argv) > 2 else '1.2'
    title = sys.argv[3] if len(sys.argv) > 3 else None
    
    if scorm_version not in ['1.2', '2004']:
        print(f"Неверная версия SCORM: {scorm_version}. Используйте '1.2' или '2004'")
        sys.exit(1)
    
    try:
        converter = PDFToSCORM(pdf_path, scorm_version=scorm_version, title=title)
        output_file = converter.convert()
        print(f"\n✓ Конвертация завершена успешно!")
        print(f"  Выходной файл: {output_file}")
    except Exception as e:
        print(f"\n✗ Ошибка: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()


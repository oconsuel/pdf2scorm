#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flask API для конвертации файлов в SCORM 2004 пакеты
"""

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import tempfile
import zipfile
from pathlib import Path
import json

from file_router import FileRouter
from converters.pdf_converter import PDFConverter
from scorm_builder import SCORMBuilder

app = Flask(__name__)
# Настраиваем CORS для работы с фронтендом
# Разрешаем все запросы с localhost (для разработки)
CORS(app, origins=["http://localhost:5173", "http://127.0.0.1:5173"], supports_credentials=True)

# Настройки
UPLOAD_FOLDER = tempfile.gettempdir()
ALLOWED_EXTENSIONS = {'pdf'}  # Только PDF файлы

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB

# Инициализация роутера и конвертеров
file_router = FileRouter()
file_router.register_converter('pdf', PDFConverter())  # Только PDF конвертер

scorm_builder = SCORMBuilder()


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/api/health', methods=['GET', 'OPTIONS'])
def health():
    """Проверка работоспособности API"""
    if request.method == 'OPTIONS':
        # Обработка preflight запроса
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        return response
    
    response = jsonify({'status': 'ok', 'message': 'API is running'})
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response


@app.route('/api/convert', methods=['POST'])
def convert_to_scorm():
    """Конвертация файлов в SCORM 2004 пакет"""
    try:
        # Проверяем наличие файлов
        if 'files' not in request.files:
            return jsonify({'error': 'No files provided'}), 400
        
        files = request.files.getlist('files')
        if not files or files[0].filename == '':
            return jsonify({'error': 'No files selected'}), 400
        
        # Получаем конфигурацию SCORM
        config_json = request.form.get('config')
        if not config_json:
            return jsonify({'error': 'No SCORM config provided'}), 400
        
        config = json.loads(config_json)
        
        # Получаем метаданные файлов
        files_metadata_json = request.form.get('files_metadata')
        files_metadata = json.loads(files_metadata_json) if files_metadata_json else []
        
        # Сохраняем файлы во временную директорию
        temp_dir = Path(tempfile.mkdtemp())
        uploaded_files = []
        
        for file in files:
            if file and allowed_file(file.filename):
                file_path = temp_dir / file.filename
                file.save(str(file_path))
                
                # Находим метаданные для этого файла
                metadata = next(
                    (m for m in files_metadata if m.get('name') == file.filename),
                    {}
                )
                
                selected_pages = metadata.get('selectedPages')
                if selected_pages is not None:
                    app.logger.info(f"File {file.filename}: selectedPages = {selected_pages}")
                
                uploaded_files.append({
                    'path': file_path,
                    'name': file.filename,
                    'type': metadata.get('type', 'resource'),
                    'is_launch': metadata.get('isLaunchFile', False),
                    'selected_pages': selected_pages,  # Для PDF: выбранные страницы
                })
        
        if not uploaded_files:
            return jsonify({'error': 'No valid files uploaded'}), 400
        
        # Определяем launch файл из исходных файлов
        launch_file_original = next((f for f in uploaded_files if f['is_launch']), uploaded_files[0])
        
        # Обрабатываем файлы через роутер с конфигурацией
        processed_files = file_router.process_files(uploaded_files, config)
        
        if not processed_files:
            return jsonify({'error': 'No files were processed'}), 400
        
        # Определяем launch файл из обработанных файлов
        # Если это PDF, то launch файл должен быть первым HTML файлом (page_1.html)
        # Иначе ищем launch файл среди обработанных
        launch_file_name = None
        if launch_file_original['name'].lower().endswith('.pdf'):
            # Для PDF ищем первый HTML файл
            pdf_html_files = [f for f in processed_files if f.get('type') == 'sco' and str(f['path']).endswith('.html')]
            if pdf_html_files:
                # Сортируем по имени файла, чтобы получить page_1.html
                pdf_html_files.sort(key=lambda x: str(x['path']))
                launch_file_name = pdf_html_files[0]['path'].name
                app.logger.info(f"PDF launch file determined: {launch_file_name}")
        else:
            # Для других файлов используем оригинальное имя
            launch_file_name = launch_file_original['name']
        
        # Если не нашли launch файл, используем первый SCO файл
        if not launch_file_name:
            sco_files = [f for f in processed_files if f.get('type') == 'sco']
            if sco_files:
                launch_file_name = sco_files[0]['path'].name
            else:
                launch_file_name = launch_file_original['name']
        
        # Собираем SCORM пакет
        course_title = config.get('title') or launch_file_original['name'].rsplit('.', 1)[0] or 'SCORM Course'
        scorm_package_path = scorm_builder.build(
            processed_files=processed_files,
            launch_file=launch_file_name,
            config=config,
            output_dir=temp_dir,
            course_title=course_title
        )
        
        # Отправляем ZIP файл
        return send_file(
            scorm_package_path,
            as_attachment=True,
            download_name=f'{course_title}_SCORM_2004.zip',
            mimetype='application/zip'
        )
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        app.logger.error(f"Error: {error_trace}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5001, host='0.0.0.0')


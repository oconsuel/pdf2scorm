#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flask API для конвертации файлов в SCORM 2004 пакеты
"""

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import tempfile
import shutil
from pathlib import Path
import json

from simple_converter import SimpleConverter
from lecture import PDFParser, build_lecture, SCORMBuilder

app = Flask(__name__)
CORS(app, origins=[
    "http://localhost:5173", "http://127.0.0.1:5173",
    "http://localhost:5174", "http://127.0.0.1:5174",
], supports_credentials=True)

UPLOAD_FOLDER = tempfile.gettempdir()
ALLOWED_EXTENSIONS = {'pdf'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500 MB

scorm_builder = SCORMBuilder()
simple_converter = SimpleConverter()


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/api/health', methods=['GET', 'OPTIONS'])
def health():
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        return response
    response = jsonify({'status': 'ok', 'message': 'API is running'})
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response


# -----------------------------------------------------------------
# Simple converter — instant PDF → SCORM, no settings
# -----------------------------------------------------------------

@app.route('/api/convert-simple', methods=['POST'])
def convert_simple():
    """Мгновенная конвертация PDF → SCORM без параметров"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']
        if not file or file.filename == '' or not allowed_file(file.filename):
            return jsonify({'error': 'Invalid or missing PDF file'}), 400

        temp_dir = Path(tempfile.mkdtemp())
        pdf_path = temp_dir / file.filename
        file.save(str(pdf_path))

        title = pdf_path.stem
        zip_path = simple_converter.convert(pdf_path, temp_dir, title=title)

        return send_file(
            zip_path,
            as_attachment=True,
            download_name=f'{title}_SCORM.zip',
            mimetype='application/zip',
        )
    except Exception as e:
        import traceback
        app.logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


# -----------------------------------------------------------------
# Lecture constructor — PDF parsed into structured lecture pages
# -----------------------------------------------------------------

@app.route('/api/convert', methods=['POST'])
def convert_to_scorm():
    """Конвертация PDF в SCORM через конструктор лекций"""
    try:
        if 'files' not in request.files:
            return jsonify({'error': 'No files provided'}), 400

        files = request.files.getlist('files')
        if not files or files[0].filename == '':
            return jsonify({'error': 'No files selected'}), 400

        config_json = request.form.get('config')
        if not config_json:
            return jsonify({'error': 'No SCORM config provided'}), 400
        config = json.loads(config_json)

        files_metadata_json = request.form.get('files_metadata')
        files_metadata = json.loads(files_metadata_json) if files_metadata_json else []

        temp_dir = Path(tempfile.mkdtemp())
        uploaded_files = []

        for file in files:
            if file and allowed_file(file.filename):
                file_path = temp_dir / file.filename
                file.save(str(file_path))

                metadata = next(
                    (m for m in files_metadata if m.get('name') == file.filename),
                    {}
                )
                uploaded_files.append({
                    'path': file_path,
                    'name': file.filename,
                    'type': metadata.get('type', 'resource'),
                    'is_launch': metadata.get('isLaunchFile', False),
                    'selected_pages': metadata.get('selectedPages'),
                })

        if not uploaded_files:
            return jsonify({'error': 'No valid files uploaded'}), 400

        # Parse PDFs → build Lecture → generate SCORM
        all_parsed_elements = []
        parser_temp_dir = None

        for file_info in uploaded_files:
            if file_info['name'].lower().endswith('.pdf'):
                parser = PDFParser(file_info['path'])
                try:
                    parsed_elements = parser.parse(file_info.get('selected_pages'))
                    all_parsed_elements.extend(parsed_elements)
                    parser_temp_dir = parser.temp_dir
                except Exception:
                    pass

        if not all_parsed_elements:
            return jsonify({'error': 'No elements extracted from PDF'}), 400

        lecture = build_lecture(all_parsed_elements, output_images_dir=None)

        if config.get('title'):
            lecture.title = config['title']

        scorm_package_path = scorm_builder.build_from_lecture(
            lecture=lecture,
            config=config,
            output_dir=temp_dir,
            parser_temp_dir=parser_temp_dir,
        )

        if parser_temp_dir and parser_temp_dir.exists():
            shutil.rmtree(parser_temp_dir, ignore_errors=True)

        course_title = lecture.title

        return send_file(
            scorm_package_path,
            as_attachment=True,
            download_name=f'{course_title}_SCORM_2004.zip',
            mimetype='application/zip',
        )

    except Exception as e:
        import traceback
        app.logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5001, host='0.0.0.0')

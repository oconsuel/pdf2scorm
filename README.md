# PDF to SCORM 2004 Converter - Web Interface

Современное веб-приложение для конвертации PDF документов в SCORM 2004 пакеты.

## Технологии

### Frontend
- **React 18** + **TypeScript**
- **Vite** - сборщик
- **Tailwind CSS** - стилизация
- **Lucide React** - иконки
- **JSZip** - работа с ZIP архивами

### Backend
- **Flask** - веб-фреймворк
- **Flask-CORS** - поддержка CORS
- **PyMuPDF (fitz)** - обработка PDF и извлечение текста/изображений
- **Pillow** - обработка изображений
- **pytesseract** + **Tesseract OCR** (опционально) - распознавание текста из изображений (fallback)
- **opencv-python** - предобработка изображений для OCR
- **numpy** - численные операции

## Установка

### Требования
- **Node.js** 18+ и npm
- **Python** 3.8+
- **pip** для установки Python зависимостей

### Frontend

```bash
npm install
```

### Backend

```bash
cd backend
pip install -r requirements.txt
```

#### Опционально: Установка Tesseract OCR

Для улучшенного извлечения текста из изображений и формул рекомендуется установить Tesseract OCR:

**macOS:**
```bash
# Если установлен Homebrew:
brew install tesseract tesseract-lang

# Если Homebrew не установлен, установите его сначала:
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
# Затем установите Tesseract:
brew install tesseract tesseract-lang
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr tesseract-ocr-rus tesseract-ocr-eng
```

**Windows:**
1. Скачайте установщик с [GitHub](https://github.com/UB-Mannheim/tesseract/wiki)
2. Установите Tesseract
3. Добавьте путь к Tesseract в переменную окружения PATH

**Примечание:** Приложение будет работать и без Tesseract, но качество извлечения текста из изображений будет ниже.

## Запуск

### 1. Запустите Backend (в отдельном терминале)

```bash
cd backend
python app.py
```

Backend будет доступен на `http://localhost:5001`

### 2. Запустите Frontend (в другом терминале)

```bash
npm run dev
```

Приложение будет доступно по адресу `http://localhost:5173`

**⚠️ Важно:** Backend должен быть запущен перед использованием приложения!

## Сборка

```bash
npm run build
```

Собранные файлы будут в директории `dist/`

## Функциональность

### 1. Загрузка PDF файлов
- Drag & Drop интерфейс
- Поддержка множественной загрузки
- Поддерживаемый формат: **PDF (.pdf)**
- Выбор страниц для включения в SCORM пакет
- Автоматическое открытие предпросмотра после загрузки
- Управление файлами: удаление, установка Launch file

### 2. Настройки SCORM 2004

#### Прогресс и завершение
- Запоминание последней страницы
- Автосохранение при каждом переходе
- Методы подсчёта прогресса (по экранам, по задачам, комбинированный)
- Порог завершения курса
- Критерии успешности

#### Предпочтения обучающегося
- Настройки громкости, языка, скорости
- Субтитры
- Запоминание предпочтений

#### Стиль плеера и UX
- Темы интерфейса (light, dark, auto)
- Цветовая схема (основной цвет, акцентный цвет)
- Высокий контраст
- Крупный шрифт
- Типы переходов между страницами

### 3. Дополнительные возможности

- **Live Preview** - предпросмотр текущих настроек
- **Package Preview** - предпросмотр сгенерированного пакета
- **SCORM Player** - встроенный проигрыватель для тестирования пакета
- **Тёмная/светлая тема** - переключение с плавной анимацией
- **Адаптивный дизайн** - поддержка desktop, tablet, mobile
- **Доступность** - ARIA-атрибуты, клавиатурная навигация

## Структура проекта

```
pdf2scorm/
├── src/                    # Frontend (React + TypeScript)
│   ├── components/         # React компоненты
│   │   ├── settings/       # Компоненты вкладок настроек
│   │   │   ├── ProgressCompletionTab.tsx
│   │   │   ├── LearnerPreferencesTab.tsx
│   │   │   └── PlayerStyleTab.tsx
│   │   ├── Header.tsx      # Верхняя панель
│   │   ├── Footer.tsx       # Нижняя панель
│   │   ├── FileUpload.tsx  # Компонент загрузки файлов
│   │   ├── PdfPreviewModal.tsx # Предпросмотр PDF с выбором страниц
│   │   ├── SettingsPanel.tsx # Панель настроек
│   │   ├── PackagePreviewModal.tsx # Модальное окно превью пакета
│   │   ├── ScormPlayer.tsx # SCORM проигрыватель
│   │   └── HelpModal.tsx   # Модальное окно помощи
│   ├── utils/              # Утилиты
│   │   ├── configPresets.ts # Конфигурация по умолчанию
│   │   ├── fileUtils.ts    # Утилиты для работы с файлами
│   │   └── scormGenerator.ts # Генератор SCORM пакетов
│   ├── types.ts            # TypeScript типы
│   ├── App.tsx             # Главный компонент
│   └── main.tsx            # Точка входа
├── backend/                # Backend (Flask)
│   ├── app.py              # Flask API сервер
│   ├── file_router.py      # Роутер для определения типа файла
│   ├── scorm_builder.py    # Сборщик SCORM 2004 пакетов
│   ├── converters/         # Конвертеры файлов
│   │   ├── pdf_parser.py   # Парсер PDF (извлечение элементов)
│   │   └── pdf_converter.py # Конвертер PDF (legacy, для page_based режима)
│   ├── builders/            # Построители структуры
│   │   └── lecture_builder.py # Построитель модели лекции
│   └── models/              # Модели данных
│       └── lecture_model.py # Модели Lecture, LectureSection, LecturePage, ContentBlock
├── pdf_to_scorm.py         # Оригинальный скрипт конвертации PDF (legacy)
├── requirements_scorm.txt  # Зависимости для pdf_to_scorm.py
├── TROUBLESHOOTING.md      # Решение проблем
└── README.md               # Этот файл
```

## Backend API

Backend реализован на Flask и предоставляет REST API для конвертации файлов в SCORM 2004 пакеты.

### Endpoints

- `GET /api/health` - проверка работоспособности API
- `POST /api/convert` - конвертация файлов в SCORM пакет

### Поддерживаемые форматы:
- **PDF** - конвертируется в SCORM 2004 пакет
  - Поддержка выбора страниц для включения в пакет
  - Два режима конвертации:
    - **lecture_based** (по умолчанию): интеллектуальное извлечение структуры лекции с заголовками, абзацами и изображениями
    - **page_based**: каждая страница PDF становится отдельным SCO (Shareable Content Object)
  - Автоматическая генерация навигации между страницами
  - Сохранение изображений из PDF в структуру SCORM пакета

## Решение проблем

Подробные инструкции по решению проблем см. в файле [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

## Архитектура

Приложение использует модульную архитектуру:

1. **PDF Parser** (`backend/converters/pdf_parser.py`): Извлекает атомарные элементы (текстовые spans и изображения) из PDF
2. **Lecture Builder** (`backend/builders/lecture_builder.py`): Группирует элементы в абзацы, определяет заголовки и формирует структуру лекции
3. **SCORM Builder** (`backend/scorm_builder.py`): Генерирует SCORM 2004 пакет из модели лекции

### Модель данных

- `ParsedElement`: Атомарный элемент из PDF (текстовый span или изображение)
- `Lecture`: Модель лекции с метаданными (title, description, language, keywords)
- `LectureSection`: Раздел лекции
- `LecturePage`: Страница лекции с контентными блоками
- `ContentBlock`: Блок контента (TextBlock, ImageBlock, ListBlock, TableBlock)

## Примечания

- Все настройки соответствуют стандарту SCORM 2004 4th Edition
- По умолчанию используется режим `lecture_based` для интеллектуального извлечения структуры
- Режим `page_based` доступен для обратной совместимости
- SCORM пакеты генерируются с полной поддержкой всех настроек из интерфейса
- Изображения автоматически сохраняются в папку `images/` в корне проекта

## Лицензия

MIT

# PDF to SCORM 2004 Converter

[![Author](https://img.shields.io/badge/author-@oconsuel-blue)](https://github.com/oconsuel)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)

Веб-приложение для конвертации PDF документов в SCORM 2004 пакеты. Два режима работы: мгновенная конвертация и конструктор лекций с интеллектуальным извлечением структуры.

## Технологии

### Frontend

![React](https://img.shields.io/badge/React_18-61DAFB?logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?logo=typescript&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-646CFF?logo=vite&logoColor=white)
![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-06B6D4?logo=tailwindcss&logoColor=white)

### Backend

![Python](https://img.shields.io/badge/Python_3.8+-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-000000?logo=flask&logoColor=white)
![PyMuPDF](https://img.shields.io/badge/PyMuPDF-009688)
![unstructured](https://img.shields.io/badge/unstructured-010101)

### Стандарты

![SCORM](https://img.shields.io/badge/SCORM_2004_4th_Edition-FF6F00)

## Быстрый старт

### Требования

- **Node.js** 18+ и npm
- **Python** 3.8+

### Установка

```bash
# Frontend
cd frontend
npm install

# Backend
cd backend
pip install -r requirements.txt
```

### Запуск

```bash
# Терминал 1 — Backend
cd backend
python app.py
# → http://localhost:5001

# Терминал 2 — Frontend
cd frontend
npm run dev
# → http://localhost:5173
```

### Сборка

```bash
cd frontend
npm run build
# Собранные файлы → frontend/dist/
```

## Функциональность

### Быстрая конвертация

Drag & Drop PDF файла на главной странице — мгновенная конвертация в SCORM 2004 без настроек. Каждая страница PDF становится отдельным SCO.

- **PyMuPDF** — рендеринг страниц PDF в изображения
- **SCORM 2004** — автоматическая генерация `imsmanifest.xml` с правилами секвенирования
- Автоматическое выставление статуса `completed` и баллов при просмотре каждой страницы

### Конструктор лекций

Загрузка PDF с выбором страниц → интеллектуальное извлечение структуры → предпросмотр → генерация SCORM.

- **PyMuPDF** — извлечение текстовых spans и изображений из PDF
- **unstructured** — извлечение структурированных элементов (Title, NarrativeText, ListItem, Caption)
- **Lecture Builder** — нормализация заголовков, построение разделов, привязка изображений, LLM-сегментация в слайды
- **SCORM Builder** — генерация HTML-страниц и SCORM 2004 пакета из модели лекции
- Выбор конкретных страниц PDF для включения в пакет
- Предпросмотр загруженных PDF

### Настройки SCORM 2004

| Категория | Возможности |
|-----------|------------|
| Прогресс и завершение | Запоминание последней страницы, автосохранение, методы подсчёта прогресса, порог завершения |
| Предпочтения обучающегося | Громкость, язык, скорость, субтитры |
| Стиль плеера | Темы (light / dark / auto), цветовая схема, высокий контраст, крупный шрифт |

### Интерфейс

- **React 18** + **TypeScript** — компонентная архитектура с типизацией
- **Tailwind CSS** — адаптивный дизайн (desktop, tablet, mobile)
- **Lucide React** — иконки
- **JSZip** — клиентская работа с ZIP-архивами
- Live Preview, Package Preview, встроенный SCORM Player
- Тёмная/светлая тема, ARIA-атрибуты, клавиатурная навигация

## Структура проекта

```
pdf2scorm/
├── frontend/                       # Frontend (React + TypeScript + Vite)
│   ├── index.html                  # Точка входа Vite
│   ├── package.json                # npm зависимости
│   ├── vite.config.ts              # Конфигурация Vite
│   ├── tsconfig.json               # Конфигурация TypeScript
│   ├── tailwind.config.js          # Конфигурация Tailwind CSS
│   ├── postcss.config.js           # Конфигурация PostCSS
│   └── src/
│       ├── App.tsx                 # Главный компонент + роутинг
│       ├── main.tsx                # Точка входа
│       ├── types.ts                # TypeScript типы
│       ├── components/
│       │   ├── LandingPage.tsx     # Главная: drag & drop + конструктор
│       │   ├── Header.tsx
│       │   ├── Footer.tsx
│       │   ├── FileUpload.tsx      # Загрузка файлов
│       │   ├── PdfPreviewModal.tsx # Предпросмотр PDF
│       │   ├── SettingsPanel.tsx   # Панель настроек SCORM
│       │   ├── LivePreview.tsx     # Предпросмотр в реальном времени
│       │   ├── PackagePreviewModal.tsx
│       │   ├── ScormPlayer.tsx     # Встроенный SCORM-плеер
│       │   ├── HelpModal.tsx
│       │   └── settings/           # Вкладки настроек
│       ├── utils/
│       │   ├── scormGenerator.ts   # Генератор SCORM пакетов
│       │   ├── configPresets.ts    # Конфигурация по умолчанию
│       │   └── fileUtils.ts
│       └── styles/
│           └── index.css
├── backend/                        # Backend (Flask + Python)
│   ├── app.py                      # Flask API сервер
│   ├── requirements.txt            # Python зависимости
│   ├── simple_converter/           # Быстрая конвертация PDF → SCORM
│   │   └── converter.py
│   └── lecture/                    # Конструктор лекций
│       ├── stage1_pdf_parser/      # Layout parsing (DocumentBlock)
│       ├── stage2_layout/          # unstructured, нормализация заголовков, section_builder
│       ├── stage3_images/          # Привязка изображений к тексту
│       ├── stage4_llm/             # LLM-клиент (OpenAI API)
│       ├── stage5_semantics/       # LLM-сегментация (GPT-4o)
│       ├── stage6_slides/          # Построение слайдов (эвристики)
│       ├── lecture_builder.py      # Оркестратор пайплайна
│       ├── scorm_builder.py        # Сборщик SCORM из модели лекции
│       ├── pipeline_csv.py         # Экспорт этапов в CSV
│       └── models/
│           └── lecture_model.py    # Модели данных
├── API.md                          # Документация API
├── LICENSE                         # MIT лицензия
├── TROUBLESHOOTING.md              # Решение проблем
└── README.md
```

## Архитектура

### Быстрая конвертация

```
PDF → PyMuPDF (рендер страниц) → изображения → SCORM ZIP
```

| Модуль | Путь | Описание |
|--------|------|----------|
| SimpleConverter | `backend/simple_converter/converter.py` | PDF → изображения → SCORM без семантического анализа |

### Конструктор лекций

```
PDF → Layout Parsing → DocumentBlock[] 
  → unstructured (layout_extractor) → ParagraphBlock[]
  → header_normalizer → section_builder → DocumentSection[]
  → Image Linking → segment_by_llm / SlideBuilder → Section[] 
  → sections_to_lecture() → Lecture → SCORM ZIP
```

| Слой | Модуль | Путь | Описание |
|------|--------|------|----------|
| 1. Layout Parsing | LayoutParser | `stage1_pdf_parser/parser.py` | DocumentBlock (строки, изображения) через PyMuPDF |
| 2. Layout Extraction | extract_layout | `stage2_layout/layout_extractor.py` | unstructured: Title, NarrativeText, ListItem, Caption |
| 2. Header Normalizer | normalize_headers | `stage2_layout/header_normalizer.py` | Продвижение/понижение заголовков |
| 2. Section Builder | build_sections | `stage2_layout/section_builder.py` | ParagraphBlock[] → DocumentSection[] |
| 3. Image Linking | ImageLinker | `stage3_images/image_linker.py` | Связывает изображения с абзацами |
| 4–5. LLM + Semantics | segment_by_llm | `stage4_llm/`, `stage5_semantics/` | GPT-4o сегментация |
| 6. Slide Builder | SlideBuilder | `stage6_slides/slide_builder.py` | Эвристики (H1=раздел, H2=слайд), fallback |
| Оркестратор | build_lecture | `backend/lecture/lecture_builder.py` | Собирает пайплайн |
| SCORM | SCORMBuilder | `backend/lecture/scorm_builder.py` | HTML и SCORM 2004 пакет |
| LLM | segment_by_llm | `backend/lecture/semantics/` | GPT-4o; при отсутствии OPENAI_API_KEY — fallback на эвристики |
| Модели | — | `backend/lecture/models/lecture_model.py` | DocumentBlock, ParagraphBlock, DocumentSection, Section, Slide, Lecture |

### Модель данных

- **Pipeline:** `DocumentBlock` → `ParagraphBlock` → `DocumentSection` → `LinkedImage` → `Slide` → `Section`
- **SCORM:** `Lecture` → `LectureSection` → `LecturePage` → `ContentBlock` (Text / Image)
- Адаптер `sections_to_lecture()` преобразует Section[] в Lecture

## API

Документация API вынесена в отдельный файл: **[API.md](API.md)**

## Лицензия

[MIT](LICENSE)

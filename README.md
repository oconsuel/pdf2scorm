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
- **Lecture Builder** — группировка элементов в абзацы, определение заголовков, формирование разделов и страниц
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
│       ├── pdf_parser/             # Layout parsing (DocumentBlock)
│       ├── layout/                 # Нормализация блоков, детекция заголовков
│       ├── images/                 # Привязка изображений к тексту
│       ├── slides/                 # Построение слайдов (эвристики)
│       ├── semantics/              # LLM-сегментация (GPT-4o, агрегация, постобработка)
│       ├── llm/                    # LLM-клиент (OpenAI API)
│       ├── lecture_builder.py      # Оркестратор пайплайна
│       ├── scorm_builder.py        # Сборщик SCORM из модели лекции
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
PDF → Layout Parsing → DocumentBlock[] → Block Normalization → ParagraphBlock[] 
  → Header Detection → Image Linking → Slide Builder (heuristic) → Section[] 
  → sections_to_lecture() → Lecture → SCORM ZIP
```

| Слой | Модуль | Путь | Описание |
|------|--------|------|----------|
| Layout Parsing | LayoutParser | `backend/lecture/pdf_parser/parser.py` | Извлекает DocumentBlock (строки, изображения) через PyMuPDF |
| Normalization | BlockNormalizer | `backend/lecture/layout/block_normalizer.py` | Объединяет строки в абзацы, определяет H1/H2/H3 |
| Image Linking | ImageLinker | `backend/lecture/images/image_linker.py` | Связывает изображения с подписями или ближайшими абзацами |
| Slide Builder | SlideBuilder | `backend/lecture/slides/slide_builder.py` | Строит слайды по эвристикам (H1=раздел, H2=слайд) |
| Оркестратор | build_lecture | `backend/lecture/lecture_builder.py` | Собирает пайплайн, возвращает Lecture |
| Генерация | SCORMBuilder | `backend/lecture/scorm_builder.py` | Рендерит HTML и собирает SCORM 2004 пакет |
| LLM (опционально) | segment_by_llm | `backend/lecture/semantics/` | GPT-4o для семантической сегментации; при отсутствии `OPENAI_API_KEY` — fallback на эвристики |
| Модели | DocumentBlock, ParagraphBlock, Slide... | `backend/lecture/models/lecture_model.py` | Pipeline-модели + Lecture/LecturePage для SCORM |

### Модель данных

- **Pipeline:** `DocumentBlock` → `ParagraphBlock` → `LinkedImage` → `Slide` → `Section`
- **SCORM (legacy):** `Lecture` → `LectureSection` → `LecturePage` → `ContentBlock` (Text / Image)
- Адаптер `sections_to_lecture()` преобразует Section[] в Lecture

## API

Документация API вынесена в отдельный файл: **[API.md](API.md)**

## Лицензия

[MIT](LICENSE)

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
npm run dev
# → http://localhost:5173
```

### Сборка

```bash
npm run build
# Собранные файлы → dist/
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
├── index.html                  # Точка входа Vite
├── package.json                # npm зависимости
├── vite.config.ts              # Конфигурация Vite
├── tsconfig.json               # Конфигурация TypeScript
├── tailwind.config.js          # Конфигурация Tailwind CSS
├── postcss.config.js           # Конфигурация PostCSS
├── src/                        # Frontend (React + TypeScript)
│   ├── App.tsx                 # Главный компонент + роутинг
│   ├── main.tsx                # Точка входа
│   ├── types.ts                # TypeScript типы
│   ├── components/
│   │   ├── LandingPage.tsx     # Главная: drag & drop + конструктор
│   │   ├── Header.tsx
│   │   ├── Footer.tsx
│   │   ├── FileUpload.tsx      # Загрузка файлов
│   │   ├── PdfPreviewModal.tsx # Предпросмотр PDF
│   │   ├── SettingsPanel.tsx   # Панель настроек SCORM
│   │   ├── LivePreview.tsx     # Предпросмотр в реальном времени
│   │   ├── PackagePreviewModal.tsx
│   │   ├── ScormPlayer.tsx     # Встроенный SCORM-плеер
│   │   ├── HelpModal.tsx
│   │   └── settings/           # Вкладки настроек
│   ├── utils/
│   │   ├── scormGenerator.ts   # Генератор SCORM пакетов
│   │   ├── configPresets.ts    # Конфигурация по умолчанию
│   │   └── fileUtils.ts
│   └── styles/
│       └── index.css
├── backend/                    # Backend (Flask + Python)
│   ├── app.py                  # Flask API сервер
│   ├── pdf_parser.py           # Парсер PDF (PyMuPDF)
│   ├── lecture_builder.py      # Построитель структуры лекции
│   ├── scorm_builder.py        # Сборщик SCORM из модели лекции
│   ├── simple_converter.py     # Быстрая конвертация PDF → SCORM
│   └── models/
│       └── lecture_model.py    # Модели данных
└── API.md                      # Документация API
```

## Архитектура

```
PDF → PDFParser → [ParsedElement...] → LectureBuilder → Lecture → SCORMBuilder → SCORM ZIP
```

| Слой | Модуль | Описание |
|------|--------|----------|
| Парсинг | `pdf_parser.py` | Извлекает атомарные элементы (текст, изображения) из PDF через PyMuPDF |
| Структурирование | `lecture_builder.py` | Группирует элементы в абзацы, определяет заголовки, формирует разделы |
| Генерация | `scorm_builder.py` | Рендерит HTML-страницы и собирает SCORM 2004 пакет |
| Быстрая конвертация | `simple_converter.py` | PDF → изображения → SCORM без семантического анализа |

### Модель данных

- `ParsedElement` — атомарный элемент из PDF (текстовый span или изображение)
- `Lecture` → `LectureSection` → `LecturePage` → `ContentBlock` (Text / Image / List / Table)

## API

Документация API вынесена в отдельный файл: **[API.md](API.md)**

## Решение проблем

См. **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)**

## Лицензия

[MIT](LICENSE)

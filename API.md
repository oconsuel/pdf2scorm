# API Reference

Backend работает на Flask и предоставляет REST API для конвертации PDF в SCORM 2004.

**Base URL:** `http://localhost:5001`

---

## `GET /api/health`

Проверка работоспособности API.

**Response:**

```json
{ "status": "ok", "message": "API is running" }
```

---

## `POST /api/convert-simple`

Мгновенная конвертация PDF в SCORM 2004 без параметров. Каждая страница PDF становится отдельным SCO с полным баллом.

**Request:** `multipart/form-data`

| Поле   | Тип  | Описание       |
|--------|------|----------------|
| `file` | File | PDF файл (.pdf) |

**Response:** ZIP-архив SCORM 2004 пакета (`application/zip`).

**Пример (curl):**

```bash
curl -X POST http://localhost:5001/api/convert-simple \
  -F "file=@lecture.pdf" \
  --output lecture_SCORM.zip
```

---

## `POST /api/convert`

Конвертация PDF через конструктор лекций — интеллектуальное извлечение структуры с разбивкой на разделы и страницы.

**Request:** `multipart/form-data`

| Поле             | Тип    | Описание                                  |
|------------------|--------|-------------------------------------------|
| `files`          | File[] | PDF файлы                                 |
| `config`         | string | JSON с настройками SCORM                  |
| `files_metadata` | string | JSON с метаданными файлов (опционально)   |

**config — пример:**

```json
{
  "title": "Моя лекция",
  "scormVersion": "2004"
}
```

**files_metadata — пример:**

```json
[
  {
    "name": "lecture.pdf",
    "type": "resource",
    "isLaunchFile": true,
    "selectedPages": [1, 2, 3, 5, 8]
  }
]
```

**Response:** ZIP-архив SCORM 2004 пакета (`application/zip`).

**Пример (curl):**

```bash
curl -X POST http://localhost:5001/api/convert \
  -F "files=@lecture.pdf" \
  -F 'config={"title":"Моя лекция"}' \
  --output lecture_SCORM_2004.zip
```

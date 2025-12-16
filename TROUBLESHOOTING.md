# Решение проблем

## Ошибка "Failed to fetch"

Эта ошибка означает, что фронтенд не может подключиться к backend серверу.

**Решение:**

1. Убедитесь, что backend запущен:
   ```bash
   cd backend
   python app.py
   ```

2. Проверьте, что сервер запустился:
   - Backend должен быть доступен на `http://localhost:5001`
   - Проверьте в браузере: `http://localhost:5001/api/health`
   - Должен вернуться JSON: `{"status": "ok", "message": "API is running"}`

3. Установите зависимости backend:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

4. Проверьте порты:
   - Frontend должен работать на `http://localhost:5173`
   - Backend должен работать на `http://localhost:5001`

## Ошибка "Module not found"

Если видите ошибки типа `ModuleNotFoundError`:

1. Убедитесь, что вы в директории `backend`
2. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```

## Ошибка "Python not found"

1. Установите Python 3.8 или выше
2. Проверьте установку:
   ```bash
   python --version
   # или
   python3 --version
   ```

## CORS ошибки

Если видите CORS ошибки в консоли браузера:

1. Убедитесь, что в `backend/app.py` есть:
   ```python
   from flask_cors import CORS
   CORS(app, resources={r"/api/*": {"origins": "*"}})
   ```

2. Перезапустите backend сервер

## Файлы не загружаются

1. Проверьте размер файлов (максимум 100MB)
2. Убедитесь, что файл имеет расширение `.pdf`
3. Проверьте консоль браузера на ошибки


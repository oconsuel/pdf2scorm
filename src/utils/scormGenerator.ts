import { SCORMConfig, UploadedFile } from '../types';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5001';

export async function generateScormPackage(
  files: UploadedFile[],
  config: SCORMConfig,
  mode: 'page_based' | 'lecture_based' = 'lecture_based'
): Promise<Blob> {
  // Проверяем доступность API перед отправкой
  try {
    const healthCheck = await fetch(`${API_URL}/api/health`, {
      method: 'GET',
      signal: AbortSignal.timeout(3000), // 3 секунды таймаут
    });
    
    if (!healthCheck.ok) {
      throw new Error(`Backend недоступен. Убедитесь, что сервер запущен на ${API_URL}`);
    }
  } catch (error: any) {
    if (error.name === 'AbortError' || error.name === 'TypeError') {
      throw new Error(
        `Не удалось подключиться к backend серверу.\n\n` +
        `Убедитесь, что:\n` +
        `1. Backend запущен: cd backend && python app.py\n` +
        `2. Сервер доступен по адресу: ${API_URL}\n` +
        `3. Установлены все зависимости: pip install -r backend/requirements.txt`
      );
    }
    throw error;
  }
  
  // Создаём FormData для отправки файлов и конфигурации
  const formData = new FormData();
  
  // Добавляем файлы
  files.forEach((file) => {
    formData.append('files', file.file);
  });
  
  // Добавляем конфигурацию SCORM
  formData.append('config', JSON.stringify(config));
  
  // Добавляем режим работы
  formData.append('mode', mode);
  
  // Добавляем метаданные файлов
  const filesMetadata = files.map(f => ({
    name: f.file.name,
    type: f.type,
    isLaunchFile: f.isLaunchFile,
    selectedPages: f.selectedPages, // Для PDF: выбранные страницы
  }));
  
  // Логируем для отладки
  const pdfFiles = files.filter(f => f.file.name.toLowerCase().endsWith('.pdf'));
  pdfFiles.forEach(f => {
  });
  
  formData.append('files_metadata', JSON.stringify(filesMetadata));
  
  // Отправляем запрос на сервер
  try {
    const response = await fetch(`${API_URL}/api/convert`, {
      method: 'POST',
      body: formData,
    });
    
    if (!response.ok) {
      let errorMessage = `HTTP ошибка: ${response.status}`;
      try {
        const errorData = await response.json();
        errorMessage = errorData.error || errorMessage;
      } catch {
        // Если не удалось распарсить JSON, используем статус
      }
      throw new Error(errorMessage);
    }
    
    // Получаем ZIP файл
    const blob = await response.blob();
    return blob;
  } catch (error: any) {
    if (error.message.includes('Failed to fetch') || error.name === 'TypeError') {
      throw new Error(
        `Не удалось подключиться к backend серверу.\n\n` +
        `Убедитесь, что:\n` +
        `1. Backend запущен: cd backend && python app.py\n` +
        `2. Сервер доступен по адресу: ${API_URL}\n` +
        `3. Установлены все зависимости: pip install -r backend/requirements.txt`
      );
    }
    throw error;
  }
}

export function validateConfig(config: SCORMConfig, files: UploadedFile[]): {
  valid: boolean;
  errors: string[];
} {
  const errors: string[] = [];
  
  if (files.length === 0) {
    errors.push('Необходимо загрузить хотя бы один файл');
  }
  
  const hasLaunchFile = files.some(f => f.isLaunchFile);
  if (!hasLaunchFile) {
    errors.push('Необходимо указать файл запуска (Launch file)');
  }
  
  if (config.progressCompletion.completionThreshold < 0 ||
      config.progressCompletion.completionThreshold > 100) {
    errors.push('Порог завершения должен быть от 0 до 100%');
  }
  
  return {
    valid: errors.length === 0,
    errors,
  };
}

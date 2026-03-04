import { UploadedFile } from '../types';

export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

export function getFileIcon(type: string): string {
  return '📕'; // Только PDF
}

export function validateFile(file: File): { valid: boolean; error?: string } {
  const isPdf = file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf');
  
  if (!isPdf) {
    return {
      valid: false,
      error: `Неподдерживаемый формат файла: ${file.name}. Разрешены только PDF файлы (.pdf)`,
    };
  }
  
  const maxSize = 100 * 1024 * 1024; // 100MB
  if (file.size > maxSize) {
    return {
      valid: false,
      error: `Файл слишком большой: ${file.name}. Максимальный размер: 100MB`,
    };
  }
  
  return { valid: true };
}

export function createFileId(): string {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}


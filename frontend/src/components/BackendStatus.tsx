import { useState, useEffect } from 'react';
import { CheckCircle, XCircle, Loader } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5001';

export function BackendStatus() {
  const [status, setStatus] = useState<'checking' | 'connected' | 'disconnected'>('checking');

  useEffect(() => {
    const checkBackend = async () => {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 3000);
        
        const response = await fetch(`${API_URL}/api/health`, {
          method: 'GET',
          signal: controller.signal,
          mode: 'cors',
          cache: 'no-cache',
        });
        
        clearTimeout(timeoutId);
        
        if (response.ok) {
          setStatus('connected');
        } else {
          setStatus('disconnected');
        }
      } catch (error: any) {
        if (error.name !== 'AbortError') {
          // Ошибка подключения
        }
        setStatus('disconnected');
      }
    };

    // Проверяем сразу при монтировании
    checkBackend();
    // Затем каждые 5 секунд
    const interval = setInterval(checkBackend, 5000);

    return () => clearInterval(interval);
  }, []);

  if (status === 'checking') {
    return (
      <div className="flex items-center space-x-2 px-3 py-1.5 bg-yellow-100 dark:bg-yellow-900/30 rounded-lg">
        <Loader className="w-4 h-4 text-yellow-600 dark:text-yellow-400 animate-spin" />
        <span className="text-xs text-yellow-700 dark:text-yellow-300">Проверка подключения...</span>
      </div>
    );
  }

  if (status === 'connected') {
    return (
      <div className="flex items-center space-x-2 px-3 py-1.5 bg-green-100 dark:bg-green-900/30 rounded-lg">
        <CheckCircle className="w-4 h-4 text-green-600 dark:text-green-400" />
        <span className="text-xs text-green-700 dark:text-green-300">Backend подключён</span>
      </div>
    );
  }

  return (
    <div className="flex items-center space-x-2 px-3 py-1.5 bg-red-100 dark:bg-red-900/30 rounded-lg">
      <XCircle className="w-4 h-4 text-red-600 dark:text-red-400" />
      <span className="text-xs text-red-700 dark:text-red-300">Backend не подключён</span>
    </div>
  );
}


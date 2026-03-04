import { SCORMConfig } from '../types';

interface LivePreviewProps {
  config: SCORMConfig;
}

export function LivePreview({ config }: LivePreviewProps) {
  const getProgressMethodLabel = (method: string) => {
    const labels: Record<string, string> = {
      screens: 'экраны',
      tasks: 'задания',
      combined: 'комбинированно',
    };
    return labels[method] || method;
  };

  return (
    <div className="p-4 bg-gray-50 dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700">
      <h4 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">
        Предпросмотр настроек
      </h4>
      <div className="flex flex-wrap gap-2">
        <span className="px-3 py-1 bg-primary-100 dark:bg-primary-900 text-primary-700 dark:text-primary-300 rounded-lg text-xs font-medium">
          Завершение: {config.progressCompletion.completionThreshold}%{' '}
          {getProgressMethodLabel(config.progressCompletion.progressMethod)}
        </span>
        <span className="px-3 py-1 bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 rounded-lg text-xs font-medium">
          Язык: {config.learnerPreferences.defaultLanguage}
        </span>
        <span className="px-3 py-1 bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300 rounded-lg text-xs font-medium">
          Тема: {config.playerStyle.theme}
        </span>
      </div>
    </div>
  );
}


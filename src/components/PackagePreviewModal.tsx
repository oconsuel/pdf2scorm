import { X, Download, FileText, Settings, CheckCircle, ArrowRight } from 'lucide-react';
import { SCORMConfig, UploadedFile } from '../types';

interface PackagePreviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  onDownload: () => void;
  onPlay: () => void;
  packageBlob: Blob | null;
  config: SCORMConfig;
  files: UploadedFile[];
}

export function PackagePreviewModal({
  isOpen,
  onClose,
  onDownload,
  onPlay,
  packageBlob,
  config,
  files,
}: PackagePreviewModalProps) {
  if (!isOpen) return null;

  const packageSize = packageBlob ? (packageBlob.size / 1024 / 1024).toFixed(2) : '0';
  const courseTitle = config.title || files[0]?.file.name.replace(/\.[^/.]+$/, '') || 'SCORM Курс';
  
  const getProgressMethodLabel = (method: string) => {
    const labels: Record<string, string> = {
      screens: 'экраны',
      tasks: 'задания',
      combined: 'комбинированно',
    };
    return labels[method] || method;
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black bg-opacity-50 backdrop-blur-sm animate-fadeIn">
      <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl max-w-3xl w-full max-h-[90vh] overflow-hidden flex flex-col animate-slideUp">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-green-100 dark:bg-green-900 rounded-lg">
              <CheckCircle className="w-6 h-6 text-green-600 dark:text-green-400" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-gray-900 dark:text-white">
                SCORM пакет готов
              </h2>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Превью созданного пакета
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors cursor-pointer"
            aria-label="Закрыть"
          >
            <X className="w-5 h-5 text-gray-500 dark:text-gray-400" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Основная информация */}
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center space-x-2">
              <FileText className="w-5 h-5" />
              <span>Информация о пакете</span>
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
                <div className="text-sm text-gray-500 dark:text-gray-400 mb-1">Название курса</div>
                <div className="text-base font-medium text-gray-900 dark:text-white">{courseTitle}</div>
              </div>
              <div className="p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
                <div className="text-sm text-gray-500 dark:text-gray-400 mb-1">Размер пакета</div>
                <div className="text-base font-medium text-gray-900 dark:text-white">{packageSize} МБ</div>
              </div>
              <div className="p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
                <div className="text-sm text-gray-500 dark:text-gray-400 mb-1">Количество файлов</div>
                <div className="text-base font-medium text-gray-900 dark:text-white">{files.length}</div>
              </div>
              <div className="p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
                <div className="text-sm text-gray-500 dark:text-gray-400 mb-1">Версия SCORM</div>
                <div className="text-base font-medium text-gray-900 dark:text-white">2004 4th Edition</div>
              </div>
            </div>
          </div>

          {/* Настройки */}
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center space-x-2">
              <Settings className="w-5 h-5" />
              <span>Применённые настройки</span>
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Progress & Completion */}
              <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
                <div className="text-sm font-semibold text-blue-900 dark:text-blue-300 mb-2">
                  Прогресс и завершение
                </div>
                <div className="space-y-1 text-sm text-blue-700 dark:text-blue-400">
                  <div>• Запоминание страницы: {config.progressCompletion.rememberLastPage ? 'Да' : 'Нет'}</div>
                  <div>• Автосохранение: {config.progressCompletion.saveOnEachTransition ? 'Да' : 'Нет'}</div>
                  <div>• Метод: {getProgressMethodLabel(config.progressCompletion.progressMethod)}</div>
                  <div>• Порог завершения: {config.progressCompletion.completionThreshold}%</div>
                </div>
              </div>

              {/* Learner Preferences */}
              <div className="p-4 bg-purple-50 dark:bg-purple-900/20 rounded-lg border border-purple-200 dark:border-purple-800">
                <div className="text-sm font-semibold text-purple-900 dark:text-purple-300 mb-2">
                  Предпочтения обучающегося
                </div>
                <div className="space-y-1 text-sm text-purple-700 dark:text-purple-400">
                  <div>• Язык: {config.learnerPreferences.defaultLanguage}</div>
                  <div>• Громкость: {config.learnerPreferences.defaultVolume}%</div>
                  <div>• Скорость: {config.learnerPreferences.deliverySpeed}%</div>
                  <div>• Субтитры: {config.learnerPreferences.alwaysSubtitles ? 'Включены' : 'Выключены'}</div>
                </div>
              </div>

              {/* Player Style */}
              <div className="p-4 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-800">
                <div className="text-sm font-semibold text-green-900 dark:text-green-300 mb-2">
                  Стиль плеера
                </div>
                <div className="space-y-1 text-sm text-green-700 dark:text-green-400">
                  <div>• Тема: {config.playerStyle.theme}</div>
                  <div>• Основной цвет: {config.playerStyle.primaryColor}</div>
                  <div>• Высокий контраст: {config.playerStyle.highContrast ? 'Да' : 'Нет'}</div>
                  <div>• Крупный шрифт: {config.playerStyle.largeFont ? 'Да' : 'Нет'}</div>
                </div>
              </div>
            </div>
          </div>

          {/* Файлы */}
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Загруженные файлы</h3>
            <div className="max-h-40 overflow-y-auto space-y-2">
              {files.map((file) => (
                <div
                  key={file.id}
                  className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700 rounded-lg"
                >
                  <div className="flex items-center space-x-3">
                    <div className="p-2 bg-primary-100 dark:bg-primary-900 rounded">
                      <FileText className="w-4 h-4 text-primary-600 dark:text-primary-400" />
                    </div>
                    <div>
                      <div className="text-sm font-medium text-gray-900 dark:text-white">
                        {file.file.name}
                      </div>
                      <div className="text-xs text-gray-500 dark:text-gray-400">
                        {(file.size / 1024).toFixed(2)} КБ • {file.type === 'sco' ? 'SCO' : 'Ресурс'}
                        {file.isLaunchFile && ' • Launch файл'}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-6 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors cursor-pointer"
          >
            Закрыть
          </button>
          
          <div className="flex items-center space-x-3">
            <button
              onClick={onDownload}
              className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors cursor-pointer flex items-center space-x-2"
            >
              <Download className="w-4 h-4" />
              <span>Скачать</span>
            </button>
            <button
              onClick={() => {
                onPlay();
                onClose();
              }}
              className="px-6 py-2 text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 rounded-lg transition-colors cursor-pointer flex items-center space-x-2"
            >
              <span>Далее</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}


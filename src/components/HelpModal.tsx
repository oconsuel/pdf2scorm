import { X } from 'lucide-react';

interface HelpModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function HelpModal({ isOpen, onClose }: HelpModalProps) {
  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 animate-fade-in"
      onClick={onClose}
    >
      <div
        className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto animate-slide-up"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="sticky top-0 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-6 py-4 flex items-center justify-between">
          <h2 className="text-xl font-bold text-gray-900 dark:text-white">
            Справка по SCORM 2004 Converter
          </h2>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
            aria-label="Close"
          >
            <X className="w-5 h-5 text-gray-600 dark:text-gray-300" />
          </button>
        </div>

        <div className="p-6 space-y-6">
          <section>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
              Загрузка PDF файлов
            </h3>
            <p className="text-sm text-gray-700 dark:text-gray-300">
              Перетащите PDF файлы в область загрузки или нажмите для выбора. Поддерживается
              только формат PDF (.pdf). После загрузки вы сможете выбрать страницы для включения
              в SCORM пакет. Первый загруженный файл автоматически становится Launch file
              (файлом запуска).
            </p>
          </section>

          <section>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
              Настройки SCORM
            </h3>
            <p className="text-sm text-gray-700 dark:text-gray-300 mb-2">
              Интерфейс разделён на 3 вкладки с настройками:
            </p>
            <ul className="list-disc list-inside text-sm text-gray-700 dark:text-gray-300 space-y-1 ml-4">
              <li>
                <strong>Прогресс и завершение</strong> - настройки отслеживания прогресса
                и завершения курса
              </li>
              <li>
                <strong>Предпочтения обучающегося</strong> - настройки языка, громкости,
                скорости воспроизведения и субтитров
              </li>
              <li>
                <strong>Стиль плеера и UX</strong> - настройки темы, цветов, шрифтов
                и пользовательского опыта
              </li>
            </ul>
          </section>

          <section>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
              Генерация пакета
            </h3>
            <p className="text-sm text-gray-700 dark:text-gray-300">
              После настройки всех параметров нажмите "Generate SCORM package". Система
              проверит обязательные поля и создаст ZIP-архив с корректно сформированным
              imsmanifest.xml и всеми необходимыми файлами.
            </p>
          </section>

          <section>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
              SCORM 2004
            </h3>
            <p className="text-sm text-gray-700 dark:text-gray-300">
              Все настройки соответствуют стандарту SCORM 2004 4th Edition. Подсказки
              рядом с настройками указывают, какие SCORM-поля они затрагивают (например,
              cmi.location, cmi.completion_status, cmi.success_status).
            </p>
          </section>
        </div>
      </div>
    </div>
  );
}


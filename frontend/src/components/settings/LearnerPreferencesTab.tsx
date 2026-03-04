import { LearnerPreferencesConfig } from '../../types';
import { InfoTooltip } from '../InfoTooltip';

interface LearnerPreferencesTabProps {
  config: LearnerPreferencesConfig;
  onChange: (updates: Partial<LearnerPreferencesConfig>) => void;
}

export function LearnerPreferencesTab({
  config,
  onChange,
}: LearnerPreferencesTabProps) {
  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Настройки предпочтений обучающегося
        </h3>
      </div>

      {/* Default Volume */}
      <div className="card">
        <div className="flex items-center space-x-2 mb-2">
          <label className="block text-sm font-medium text-gray-900 dark:text-white">
            Громкость по умолчанию: {config.defaultVolume}%
          </label>
          <InfoTooltip
            content={`Устанавливает начальный уровень громкости для аудио- и видео-материалов курса.\n\nТекущее значение: ${config.defaultVolume}%\n\n• 0% - без звука\n• 25-50% - тихий уровень\n• 75% - стандартный уровень\n• 100% - максимальная громкость`}
          />
        </div>
        <input
          type="range"
          min="0"
          max="100"
          value={config.defaultVolume}
          onChange={(e) =>
            onChange({ defaultVolume: parseInt(e.target.value) })
          }
          className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer dark:bg-gray-700"
        />
      </div>

      {/* Default Language */}
      <div className="card">
        <label className="block text-sm font-medium text-gray-900 dark:text-white mb-2">
          Язык по умолчанию
        </label>
        <select
          value={config.defaultLanguage}
          onChange={(e) => onChange({ defaultLanguage: e.target.value })}
          className="input-field"
        >
          <option value="ru">Русский</option>
          <option value="en">English</option>
          <option value="de">Deutsch</option>
          <option value="fr">Français</option>
          <option value="es">Español</option>
        </select>
      </div>

      {/* Delivery Speed */}
      <div className="card">
        <label className="block text-sm font-medium text-gray-900 dark:text-white mb-2">
          Скорость подачи материала (delivery speed): {config.deliverySpeed}%
        </label>
        <input
          type="range"
          min="0"
          max="100"
          value={config.deliverySpeed}
          onChange={(e) =>
            onChange({ deliverySpeed: parseInt(e.target.value) })
          }
          className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer dark:bg-gray-700"
        />
      </div>

      {/* Always Subtitles */}
      <div className="card">
        <div className="flex items-center justify-between">
          <label className="text-sm font-medium text-gray-900 dark:text-white">
            Всегда включать субтитры
          </label>
          <label className="relative inline-flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={config.alwaysSubtitles}
              onChange={(e) => onChange({ alwaysSubtitles: e.target.checked })}
              className="sr-only peer"
            />
            <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 dark:peer-focus:ring-primary-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-primary-600"></div>
          </label>
        </div>
      </div>

      {/* Remember Preferences */}
      <div className="card">
        <div className="flex items-center justify-between">
          <label className="text-sm font-medium text-gray-900 dark:text-white">
            Запоминать мои настройки для будущих запусков
          </label>
          <label className="relative inline-flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={config.rememberPreferences}
              onChange={(e) =>
                onChange({ rememberPreferences: e.target.checked })
              }
              className="sr-only peer"
            />
            <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 dark:peer-focus:ring-primary-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-primary-600"></div>
          </label>
        </div>
      </div>
    </div>
  );
}


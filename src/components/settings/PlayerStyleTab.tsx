import { PlayerStyleConfig } from '../../types';

interface PlayerStyleTabProps {
  config: PlayerStyleConfig;
  onChange: (updates: Partial<PlayerStyleConfig>) => void;
}

export function PlayerStyleTab({ config, onChange }: PlayerStyleTabProps) {
  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Настройки стиля плеера и UX
        </h3>
      </div>

      {/* Theme */}
      <div className="card">
        <label className="block text-sm font-medium text-gray-900 dark:text-white mb-2">
          Тема интерфейса
        </label>
        <select
          value={config.theme}
          onChange={(e) => onChange({ theme: e.target.value as any })}
          className="input-field"
        >
          <option value="light">Светлая</option>
          <option value="dark">Тёмная</option>
          <option value="auto">Авто (системная)</option>
        </select>
      </div>

      {/* Colors */}
      <div className="card">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-900 dark:text-white mb-2">
              Основной цвет
            </label>
            <input
              type="color"
              value={config.primaryColor}
              onChange={(e) => onChange({ primaryColor: e.target.value })}
              className="w-full h-10 rounded-lg cursor-pointer"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-900 dark:text-white mb-2">
              Акцентный цвет
            </label>
            <input
              type="color"
              value={config.accentColor}
              onChange={(e) => onChange({ accentColor: e.target.value })}
              className="w-full h-10 rounded-lg cursor-pointer"
            />
          </div>
        </div>
      </div>

      {/* TOC Layout */}
      <div className="card">
        <label className="block text-sm font-medium text-gray-900 dark:text-white mb-2">
          Layout оглавления
        </label>
        <select
          value={config.tocLayout}
          onChange={(e) => onChange({ tocLayout: e.target.value as any })}
          className="input-field"
        >
          <option value="sidebar">Слева (sidebar)</option>
          <option value="tabs">Сверху (tabs)</option>
          <option value="overlay">Скрываемое меню (overlay для мобильных)</option>
        </select>
      </div>

      {/* Progress Indicator */}
      <div className="card">
        <label className="block text-sm font-medium text-gray-900 dark:text-white mb-2">
          Выбор прогресс-индикатора
        </label>
        <select
          value={config.progressIndicator}
          onChange={(e) => onChange({ progressIndicator: e.target.value as any })}
          className="input-field"
        >
          <option value="linear">Линейная полоса прогресса</option>
          <option value="steps">Шаги (кружки)</option>
          <option value="percentage">Только процент</option>
        </select>
      </div>

      {/* Accessibility */}
      <div className="card">
        <h4 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">
          Доступность
        </h4>
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <label className="text-sm font-medium text-gray-900 dark:text-white">
              Режим высокой контрастности
            </label>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={config.highContrast}
                onChange={(e) => onChange({ highContrast: e.target.checked })}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 dark:peer-focus:ring-primary-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-primary-600"></div>
            </label>
          </div>
          <div className="flex items-center justify-between">
            <label className="text-sm font-medium text-gray-900 dark:text-white">
              Увеличенный размер шрифта
            </label>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={config.largeFont}
                onChange={(e) => onChange({ largeFont: e.target.checked })}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 dark:peer-focus:ring-primary-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-primary-600"></div>
            </label>
          </div>
        </div>
      </div>

      {/* Animations */}
      <div className="card">
        <h4 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">
          Анимации
        </h4>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-900 dark:text-white mb-2">
              Тип анимаций переходов экрана
            </label>
            <select
              value={config.transitionType}
              onChange={(e) => onChange({ transitionType: e.target.value as any })}
              className="input-field"
            >
              <option value="none">Нет</option>
              <option value="fade">Плавное</option>
              <option value="slide">Скольжение</option>
            </select>
          </div>
          <div className="flex items-center justify-between">
            <label className="text-sm font-medium text-gray-900 dark:text-white">
              Уменьшить анимации (для чувствительных пользователей)
            </label>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={config.reduceAnimations}
                onChange={(e) => onChange({ reduceAnimations: e.target.checked })}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 dark:peer-focus:ring-primary-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-primary-600"></div>
            </label>
          </div>
        </div>
      </div>
    </div>
  );
}


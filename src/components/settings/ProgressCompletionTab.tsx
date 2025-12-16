import { ProgressCompletionConfig } from '../../types';
import { InfoTooltip } from '../InfoTooltip';

interface ProgressCompletionTabProps {
  config: ProgressCompletionConfig;
  onChange: (updates: Partial<ProgressCompletionConfig>) => void;
}

export function ProgressCompletionTab({
  config,
  onChange,
}: ProgressCompletionTabProps) {
  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Настройки прогресса и завершения
        </h3>
      </div>

      {/* Remember Last Page */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-2">
            <label className="text-sm font-medium text-gray-900 dark:text-white">
              Запоминать последнюю страницу и состояние курса
            </label>
            <InfoTooltip
              content="При включении система будет сохранять позицию обучающегося в курсе и все данные о прогрессе. При повторном входе курс откроется на последней посещённой странице.\n\nВлияет на SCORM-поля:\n• cmi.location - сохраняет номер последней страницы\n• cmi.suspend_data - хранит данные о прогрессе\n• cmi.progress_measure - отслеживает процент выполнения"
            />
          </div>
          <label className="relative inline-flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={config.rememberLastPage}
              onChange={(e) => onChange({ rememberLastPage: e.target.checked })}
              className="sr-only peer"
            />
            <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 dark:peer-focus:ring-primary-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-primary-600"></div>
          </label>
        </div>

        {config.rememberLastPage && (
          <div className="space-y-3 mt-4 pl-4 border-l-2 border-primary-500">
            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={config.saveOnEachTransition}
                onChange={(e) => onChange({ saveOnEachTransition: e.target.checked })}
                className="w-4 h-4 text-primary-600 rounded focus:ring-primary-500"
              />
              <span className="text-sm text-gray-700 dark:text-gray-300">
                Сохранять состояние при каждом переходе экрана
              </span>
              <InfoTooltip
                content="Автоматически сохраняет прогресс при каждом переходе между страницами курса. Обеспечивает максимальную надёжность сохранения данных, но может увеличить нагрузку на систему."
              />
            </label>
            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={config.askOnReentry}
                onChange={(e) => onChange({ askOnReentry: e.target.checked })}
                className="w-4 h-4 text-primary-600 rounded focus:ring-primary-500"
              />
              <span className="text-sm text-gray-700 dark:text-gray-300">
                Спрашивать пользователя при повторном входе: продолжить или начать заново
              </span>
              <InfoTooltip
                content="При повторном входе в курс обучающемуся будет предложено выбрать: продолжить с места остановки или начать курс заново. Это полезно для случаев, когда нужно пройти курс с нуля."
              />
            </label>
          </div>
        )}
      </div>

      {/* Progress Method */}
      <div className="card">
        <div className="flex items-center space-x-2 mb-2">
          <label className="block text-sm font-medium text-gray-900 dark:text-white">
            Как считать прогресс?
          </label>
          <InfoTooltip
            content="Определяет метод расчёта прогресса прохождения курса:\n\n• По количеству просмотренных экранов - прогресс = (просмотренные страницы / всего страниц) × 100%\n• По завершённым заданиям - прогресс считается только при выполнении заданий\n• Комбинированно - учитываются и просмотренные страницы, и выполненные задания\n\nВлияет на SCORM-поле: cmi.progress_measure (0.0 - 1.0)"
          />
        </div>
        <select
          value={config.progressMethod}
          onChange={(e) =>
            onChange({ progressMethod: e.target.value as any })
          }
          className="input-field"
        >
          <option value="screens">По количеству просмотренных экранов</option>
          <option value="tasks">По завершённым заданиям</option>
          <option value="combined">Комбинированно</option>
        </select>
      </div>

      {/* Completion Threshold */}
      <div className="card">
        <div className="flex items-center space-x-2 mb-2">
          <label className="block text-sm font-medium text-gray-900 dark:text-white">
            Процент, при котором считать курс завершённым: {config.completionThreshold}%
          </label>
          <InfoTooltip
            content={`Устанавливает минимальный процент выполнения курса, при достижении которого курс считается завершённым.\n\nТекущее значение: ${config.completionThreshold}%\n\n• 0% - курс завершён сразу при открытии\n• 50% - нужно пройти половину курса\n• 80% - стандартное значение, нужно пройти большую часть\n• 100% - необходимо пройти весь курс полностью\n\nВлияет на SCORM-поле: cmi.completion_status (incomplete/completed)`}
          />
        </div>
        <input
          type="range"
          min="0"
          max="100"
          value={config.completionThreshold}
          onChange={(e) =>
            onChange({ completionThreshold: parseInt(e.target.value) })
          }
          className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer dark:bg-gray-700"
        />
      </div>

      {/* Success Criterion */}
      <div className="card">
        <div className="flex items-center space-x-2 mb-3">
          <label className="block text-sm font-medium text-gray-900 dark:text-white">
            Критерий успешности
          </label>
          <InfoTooltip
            content="Определяет, как система будет определять, успешно ли пройден курс:\n\n• По итоговому баллу - курс считается пройденным, если итоговый балл достиг проходного значения\n• По набору обязательных задач - необходимо выполнить все обязательные задания\n• Не оценивать - система не будет определять успешность (success_status останется unknown)\n\nВлияет на SCORM-поле: cmi.success_status (passed/failed/unknown)"
          />
        </div>
        <div className="space-y-2">
          <label className="flex items-center space-x-2">
            <input
              type="radio"
              name="successCriterion"
              value="score"
              checked={config.successCriterion === 'score'}
              onChange={() => onChange({ successCriterion: 'score' })}
              className="w-4 h-4 text-primary-600 focus:ring-primary-500"
            />
            <span className="text-sm text-gray-700 dark:text-gray-300">
              По итоговому баллу
            </span>
          </label>
          <label className="flex items-center space-x-2">
            <input
              type="radio"
              name="successCriterion"
              value="tasks"
              checked={config.successCriterion === 'tasks'}
              onChange={() => onChange({ successCriterion: 'tasks' })}
              className="w-4 h-4 text-primary-600 focus:ring-primary-500"
            />
            <span className="text-sm text-gray-700 dark:text-gray-300">
              По набору обязательных задач
            </span>
          </label>
          <label className="flex items-center space-x-2">
            <input
              type="radio"
              name="successCriterion"
              value="none"
              checked={config.successCriterion === 'none'}
              onChange={() => onChange({ successCriterion: 'none' })}
              className="w-4 h-4 text-primary-600 focus:ring-primary-500"
            />
            <span className="text-sm text-gray-700 dark:text-gray-300">
              Не оценивать
            </span>
          </label>
        </div>
      </div>
    </div>
  );
}

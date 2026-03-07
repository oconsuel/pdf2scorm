import { SCORMConfig, Lang } from '../types';
import { t } from '../i18n/translations';

interface LivePreviewProps {
  lang: Lang;
  config: SCORMConfig;
}

export function LivePreview({ lang, config }: LivePreviewProps) {
  const progressMethodLabels: Record<string, string> = {
    screens: t(lang, 'screens'),
    tasks: t(lang, 'tasks'),
    combined: t(lang, 'combined'),
  };
  const getProgressMethodLabel = (method: string) => progressMethodLabels[method] || method;

  return (
    <div className="p-4 bg-gray-50 dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700">
      <h4 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">
        {t(lang, 'previewSettings')}
      </h4>
      <div className="flex flex-wrap gap-2">
        <span className="px-3 py-1 bg-primary-100 dark:bg-primary-900 text-primary-700 dark:text-primary-300 rounded-lg text-xs font-medium">
          {t(lang, 'completion')}: {config.progressCompletion.completionThreshold}%{' '}
          {getProgressMethodLabel(config.progressCompletion.progressMethod)}
        </span>
        <span className="px-3 py-1 bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 rounded-lg text-xs font-medium">
          {t(lang, 'language')}: {config.learnerPreferences.defaultLanguage}
        </span>
        <span className="px-3 py-1 bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300 rounded-lg text-xs font-medium">
          {t(lang, 'theme')}: {config.playerStyle.theme}
        </span>
      </div>
    </div>
  );
}


import { Lang } from '../types';
import { t } from '../i18n/translations';

interface WelcomeBlockProps {
  lang: Lang;
}

export function WelcomeBlock({ lang }: WelcomeBlockProps) {
  return (
    <div className="text-center space-y-3 max-w-2xl mx-auto">
      <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white">
        {t(lang, 'welcomeTitle')}
      </h1>
      <p className="text-base sm:text-lg text-gray-600 dark:text-gray-400 leading-relaxed">
        {t(lang, 'welcomeDesc')}
      </p>
    </div>
  );
}

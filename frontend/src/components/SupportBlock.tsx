import { Star } from 'lucide-react';
import { Lang } from '../types';
import { t } from '../i18n/translations';
import { GITHUB_REPO_URL } from '../config';

interface SupportBlockProps {
  lang: Lang;
}

export function SupportBlock({ lang }: SupportBlockProps) {
  return (
    <div className="w-full max-w-7xl mx-auto px-8 sm:px-12 pt-32 pb-6 sm:pb-8">
      <div className="flex flex-col sm:flex-row items-center gap-4 sm:gap-6">
        <div className="flex-shrink-0 w-12 h-12 rounded-xl bg-primary-500/20 dark:bg-primary-500/30 flex items-center justify-center">
          <Star className="w-6 h-6 text-primary-600 dark:text-primary-400" />
        </div>
        <div className="flex-1 text-center sm:text-left">
          <h3 className="font-semibold text-gray-900 dark:text-white">{t(lang, 'supportTitle')}</h3>
          <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">{t(lang, 'supportText')}</p>
        </div>
        <div className="flex-shrink-0">
          <a
            href={GITHUB_REPO_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-gray-900 dark:bg-gray-100 text-white dark:text-gray-900 text-sm font-medium hover:opacity-90 transition-opacity"
          >
            <Star className="w-4 h-4" />
            {t(lang, 'starOnGitHub')}
          </a>
        </div>
      </div>
    </div>
  );
}

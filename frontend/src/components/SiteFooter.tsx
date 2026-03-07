import { Mail, Github } from 'lucide-react';
import { Lang } from '../types';
import { t } from '../i18n/translations';
import { GITHUB_REPO_URL, CONTACT_EMAIL } from '../config';

interface SiteFooterProps {
  lang: Lang;
}

export function SiteFooter({ lang }: SiteFooterProps) {
  return (
    <footer className="mt-auto border-t border-gray-200 dark:border-gray-700 bg-white/50 dark:bg-gray-800/50 backdrop-blur-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 sm:py-8">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 sm:gap-6 text-sm text-gray-600 dark:text-gray-400">
          <p className="text-center sm:text-left whitespace-nowrap">{t(lang, 'projectDesc')}</p>
          <div className="flex flex-wrap items-center justify-center gap-4 sm:gap-6">
            <a
              href={`mailto:${CONTACT_EMAIL}`}
              className="flex items-center gap-2 hover:text-primary-600 dark:hover:text-primary-400 transition-colors"
            >
              <Mail className="w-4 h-4" />
              {CONTACT_EMAIL}
            </a>
            <a
              href={GITHUB_REPO_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 hover:text-primary-600 dark:hover:text-primary-400 transition-colors"
            >
              <Github className="w-4 h-4" />
              {t(lang, 'githubRepo')}
            </a>
          </div>
        </div>
      </div>
    </footer>
  );
}

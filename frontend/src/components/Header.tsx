import { Moon, Sun, HelpCircle } from 'lucide-react';
import { Theme, Lang } from '../types';
import { BackendStatus } from './BackendStatus';
import { t } from '../i18n/translations';

interface HeaderProps {
  theme: Theme;
  lang: Lang;
  onThemeChange: (theme: Theme) => void;
  onLangChange: (lang: Lang) => void;
  onHelpClick: () => void;
}

export function Header({ theme, lang, onThemeChange, onLangChange, onHelpClick }: HeaderProps) {
  return (
    <header className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center space-x-3">
            <div className="flex items-center justify-center w-10 h-10 bg-primary-600 rounded-xl">
              <span className="text-white font-bold text-lg">P</span>
            </div>
            <div>
              <h1 className="text-lg sm:text-xl font-bold text-gray-900 dark:text-white">
                {t(lang, 'appName')}
              </h1>
              <p className="hidden sm:block text-xs text-gray-500 dark:text-gray-400">
                {t(lang, 'appSubtitle')}
              </p>
            </div>
          </div>
          
          <div className="flex items-center space-x-3">
            <button
              onClick={() => onLangChange(lang === 'ru' ? 'en' : 'ru')}
              className="px-2 py-1 text-sm font-medium rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 transition-colors"
              title={lang === 'ru' ? 'Switch to English' : 'Переключить на русский'}
              aria-label={lang === 'ru' ? 'Switch to English' : 'Переключить на русский'}
            >
              {lang === 'ru' ? 'EN' : 'RU'}
            </button>
            <BackendStatus />
            
            <button
              onClick={() => onThemeChange(theme === 'dark' ? 'light' : 'dark')}
              className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors cursor-pointer"
              aria-label={t(lang, 'toggleTheme')}
            >
              {theme === 'dark' ? (
                <Sun className="w-5 h-5 text-gray-600 dark:text-gray-300" />
              ) : (
                <Moon className="w-5 h-5 text-gray-600 dark:text-gray-300" />
              )}
            </button>
            
            <button
              onClick={onHelpClick}
              className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors cursor-pointer"
              aria-label={t(lang, 'help')}
            >
              <HelpCircle className="w-5 h-5 text-gray-600 dark:text-gray-300" />
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}


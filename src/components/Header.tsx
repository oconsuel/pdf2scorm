import { Moon, Sun, HelpCircle } from 'lucide-react';
import { Theme } from '../types';
import { BackendStatus } from './BackendStatus';

interface HeaderProps {
  theme: Theme;
  onThemeChange: (theme: Theme) => void;
  onHelpClick: () => void;
}

export function Header({ theme, onThemeChange, onHelpClick }: HeaderProps) {
  return (
    <header className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center space-x-3">
            <div className="flex items-center justify-center w-10 h-10 bg-primary-600 rounded-xl">
              <span className="text-white font-bold text-lg">S</span>
            </div>
            <div>
              <h1 className="text-lg sm:text-xl font-bold text-gray-900 dark:text-white">
                SCORM 2004 Converter
              </h1>
              <p className="hidden sm:block text-xs text-gray-500 dark:text-gray-400">
                Настройка и генерация SCORM 2004 пакетов
              </p>
            </div>
          </div>
          
          <div className="flex items-center space-x-3">
            <BackendStatus />
            
            <button
              onClick={() => onThemeChange(theme === 'dark' ? 'light' : 'dark')}
              className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors cursor-pointer"
              aria-label="Переключить тему"
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
              aria-label="Помощь"
            >
              <HelpCircle className="w-5 h-5 text-gray-600 dark:text-gray-300" />
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}


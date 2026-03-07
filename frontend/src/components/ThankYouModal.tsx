import { Star } from 'lucide-react';
import { Lang } from '../types';
import { t } from '../i18n/translations';
import { GITHUB_REPO_URL } from '../config';

interface ThankYouModalProps {
  lang: Lang;
  isOpen: boolean;
  onClose: () => void;
}

export function ThankYouModal({ lang, isOpen, onClose }: ThankYouModalProps) {
  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="thank-you-title"
    >
      <div
        className="absolute inset-0 bg-black/40 dark:bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />
      <div className="relative w-full max-w-md rounded-2xl bg-white/95 dark:bg-gray-800/95 backdrop-blur-md shadow-2xl border border-gray-200/80 dark:border-gray-600/80 p-6 sm:p-8 animate-fadeIn">
        <div className="flex flex-col items-center text-center space-y-4">
          <div className="w-14 h-14 rounded-full bg-primary-500/20 dark:bg-primary-500/30 flex items-center justify-center">
            <Star className="w-7 h-7 text-primary-600 dark:text-primary-400" />
          </div>
          <h2 id="thank-you-title" className="text-xl font-bold text-gray-900 dark:text-white">
            {t(lang, 'thankYouTitle')}
          </h2>
          <p className="text-gray-600 dark:text-gray-400 text-sm leading-relaxed">
            {t(lang, 'thankYouText')}
          </p>
          <a
            href={GITHUB_REPO_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gray-900 dark:bg-gray-100 text-white dark:text-gray-900 text-sm font-medium hover:opacity-90 transition-opacity"
          >
            <Star className="w-4 h-4" />
            {t(lang, 'starOnGitHub')}
          </a>
          <button
            onClick={onClose}
            className="text-sm text-primary-600 dark:text-primary-400 hover:underline"
          >
            {t(lang, 'gotIt')}
          </button>
        </div>
      </div>
    </div>
  );
}

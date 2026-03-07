import { useState, useEffect, useRef, DragEvent, useCallback } from 'react';
import { Upload, Check, Loader2, ArrowRight } from 'lucide-react';
import { Lang } from '../types';
import { t } from '../i18n/translations';
import { SupportBlock } from './SupportBlock';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5001';

const TYPE_MS = 70;
const DELETE_MS = 35;
const PAUSE_MS = 2200;
const GAP_MS = 400;

type ConvertState = 'idle' | 'converting' | 'done';

interface LandingPageProps {
  lang: Lang;
  onNavigateToConstructor: () => void;
  onConvertSuccess?: () => void;
}

const TYPEWRITER_WORDS: Record<Lang, string[]> = {
  ru: ['лекцию', 'практическое занятие', 'мультимедийные материалы'],
  en: ['lecture', 'workshop', 'multimedia materials'],
};

export function LandingPage({ lang, onNavigateToConstructor, onConvertSuccess }: LandingPageProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [convertState, setConvertState] = useState<ConvertState>('idle');
  const [fileName, setFileName] = useState('');

  // Typewriter state
  const [wordIdx, setWordIdx] = useState(0);
  const [charIdx, setCharIdx] = useState(0);
  const [deleting, setDeleting] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const words = TYPEWRITER_WORDS[lang];
  useEffect(() => {
    const word = words[wordIdx];
    let timer: ReturnType<typeof setTimeout>;

    if (!deleting) {
      if (charIdx < word.length) {
        timer = setTimeout(() => setCharIdx((c) => c + 1), TYPE_MS);
      } else {
        timer = setTimeout(() => setDeleting(true), PAUSE_MS);
      }
    } else {
      if (charIdx > 0) {
        timer = setTimeout(() => setCharIdx((c) => c - 1), DELETE_MS);
      } else {
        timer = setTimeout(() => {
          setDeleting(false);
          setWordIdx((i) => (i + 1) % words.length);
        }, GAP_MS);
      }
    }

    return () => clearTimeout(timer);
  }, [charIdx, deleting, wordIdx, words, lang]);

  const visibleText = words[wordIdx].slice(0, charIdx);

  // ── Drag & drop ────────────────────────────────────────────────
  const onDragOver = useCallback((e: DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const onDragLeave = useCallback((e: DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const onDrop = useCallback(
    (e: DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      const file = e.dataTransfer.files[0];
      if (file && file.name.toLowerCase().endsWith('.pdf')) {
        handleConvert(file);
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  );

  const onFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleConvert(file);
    e.target.value = '';
  };

  // ── Convert ────────────────────────────────────────────────────
  const handleConvert = async (file: File) => {
    setConvertState('converting');
    setFileName(file.name.replace(/\.pdf$/i, ''));

    try {
      const fd = new FormData();
      fd.append('file', file);

      const res = await fetch(`${API_URL}/api/convert-simple`, {
        method: 'POST',
        body: fd,
      });

      if (!res.ok) {
        const data = await res.json().catch(() => null);
        throw new Error(data?.error || `Ошибка ${res.status}`);
      }

      const blob = await res.blob();
      setConvertState('done');
      onConvertSuccess?.();

      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${file.name.replace(/\.pdf$/i, '')}_SCORM.zip`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err: any) {
      setConvertState('idle');
      alert(err?.message || 'Ошибка конвертации');
    }
  };

  // ── Render ─────────────────────────────────────────────────────
  return (
    <div className="flex-1 flex flex-col items-center justify-center px-4 sm:px-6 py-10 sm:py-20">
      <div className="w-full max-w-2xl space-y-10">
        {/* ─── Quick-convert drop zone ─── */}
        <div
          onDragOver={onDragOver}
          onDragLeave={onDragLeave}
          onDrop={onDrop}
          onClick={() => convertState === 'idle' && fileInputRef.current?.click()}
          className={`
            relative rounded-3xl p-10 sm:p-16 text-center
            transition-all duration-500 ease-out
            ${convertState !== 'idle' ? 'pointer-events-none' : 'cursor-pointer'}
            ${
              isDragging
                ? 'border-2 border-primary-500 bg-primary-50/60 dark:bg-primary-900/20 scale-[1.02] shadow-2xl shadow-primary-500/10'
                : convertState === 'done'
                ? 'border-2 border-green-400 bg-green-50/40 dark:bg-green-900/15'
                : 'border-2 border-dashed border-gray-300 dark:border-gray-600 hover:border-primary-400 hover:bg-gray-50/60 dark:hover:bg-gray-800/40 hover:shadow-xl'
            }
          `}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf"
            className="hidden"
            onChange={onFileSelect}
          />

          {convertState === 'idle' && (
            <div className="flex flex-col items-center space-y-5 animate-fadeIn">
              <div
                className={`
                  w-20 h-20 rounded-2xl flex items-center justify-center
                  transition-all duration-500
                  ${isDragging ? 'bg-primary-500 rotate-6 scale-110' : 'bg-gray-100 dark:bg-gray-700/80'}
                `}
              >
                <Upload
                  className={`w-10 h-10 transition-colors duration-300 ${
                    isDragging ? 'text-white' : 'text-gray-400 dark:text-gray-500'
                  }`}
                />
              </div>
              <div>
                <p className="text-xl font-semibold text-gray-900 dark:text-white">
                  {t(lang, 'dragPdf')}
                </p>
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
                  {t(lang, 'instantConvert')}
                </p>
              </div>
            </div>
          )}

          {convertState === 'converting' && (
            <div className="flex flex-col items-center space-y-5 animate-fadeIn">
              <Loader2 className="w-14 h-14 text-primary-500 animate-spin" />
              <p className="text-lg text-gray-700 dark:text-gray-300">
                {t(lang, 'converting')}{' '}
                <span className="font-semibold text-gray-900 dark:text-white">{fileName}</span>…
              </p>
            </div>
          )}

          {convertState === 'done' && (
            <div className="flex flex-col items-center space-y-5 animate-fadeIn pointer-events-auto">
              <div className="w-16 h-16 rounded-full bg-green-500 flex items-center justify-center shadow-lg shadow-green-500/30">
                <Check className="w-8 h-8 text-white" />
              </div>
              <div>
                <p className="text-lg font-medium text-gray-900 dark:text-white">
                  {t(lang, 'done')}
                </p>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setConvertState('idle');
                  }}
                  className="mt-2 text-sm text-primary-600 dark:text-primary-400 hover:underline cursor-pointer"
                >
                  {t(lang, 'convertMore')}
                </button>
              </div>
            </div>
          )}
        </div>

        {/* ─── Divider ─── */}
        <div className="flex items-center gap-4">
          <div className="flex-1 h-px bg-gradient-to-r from-transparent via-gray-300 dark:via-gray-600 to-transparent" />
          <span className="text-sm font-medium text-gray-400 dark:text-gray-500 uppercase tracking-widest select-none">
            {t(lang, 'or')}
          </span>
          <div className="flex-1 h-px bg-gradient-to-r from-transparent via-gray-300 dark:via-gray-600 to-transparent" />
        </div>

        {/* ─── Constructor card ─── */}
        <div
          onClick={onNavigateToConstructor}
          className="
            group relative overflow-hidden
            bg-white dark:bg-gray-800 rounded-3xl
            shadow-lg hover:shadow-2xl
            border border-gray-200 dark:border-gray-700
            p-8 sm:p-10 cursor-pointer
            transition-all duration-300 hover:scale-[1.01]
          "
        >
          <div className="text-center space-y-1">
            <p className="text-xl sm:text-2xl leading-relaxed text-gray-600 dark:text-gray-300">
              {t(lang, 'formLecture')}
            </p>
            <p className="text-2xl sm:text-3xl font-bold leading-snug min-h-[2.4em] flex items-center justify-center">
              <span className="text-primary-600 dark:text-primary-400">
                {visibleText}
              </span>
              <span className="inline-block w-[3px] h-[1.1em] bg-primary-500 dark:bg-primary-400 ml-0.5 rounded-full animate-blink" />
            </p>
            <p className="text-xl sm:text-2xl leading-relaxed text-gray-600 dark:text-gray-300">
              {t(lang, 'inScorm')}
            </p>
          </div>

          <div className="flex items-center justify-center mt-6 text-primary-600 dark:text-primary-400 opacity-70 group-hover:opacity-100 transition-all duration-300">
            <span className="text-sm font-medium mr-2">{t(lang, 'goToConstructor')}</span>
            <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform duration-300" />
          </div>
        </div>
      </div>
      <SupportBlock lang={lang} />
    </div>
  );
}

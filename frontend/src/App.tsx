import { useState, useEffect } from 'react';
import { ArrowLeft } from 'lucide-react';
import { Header } from './components/Header';
import { Footer } from './components/Footer';
import { FileUpload } from './components/FileUpload';
import { SettingsPanel } from './components/SettingsPanel';
import { HelpModal } from './components/HelpModal';
import { PackagePreviewModal } from './components/PackagePreviewModal';
import { ScormPlayer } from './components/ScormPlayer';
import { LandingPage } from './components/LandingPage';
import { SiteFooter } from './components/SiteFooter';
import { ThankYouModal } from './components/ThankYouModal';
import { UploadedFile, SCORMConfig, Theme, Lang } from './types';
import { t } from './i18n/translations';
import { defaultConfig } from './utils/configPresets';
import { validateConfig, generateScormPackage } from './utils/scormGenerator';

type View = 'landing' | 'constructor';

function App() {
  const [view, setView] = useState<View>('landing');
  const [theme, setTheme] = useState<Theme>('light');
  const [lang, setLang] = useState<Lang>('ru');
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [config, setConfig] = useState<SCORMConfig>(defaultConfig);
  const [showHelp, setShowHelp] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [hasPackage, setHasPackage] = useState(false);
  const [lastPackage, setLastPackage] = useState<Blob | null>(null);
  const [showPreview, setShowPreview] = useState(false);
  const [showThankYou, setShowThankYou] = useState(false);
  const [showPlayer, setShowPlayer] = useState(false);

  useEffect(() => {
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [theme]);

  const validation = validateConfig(config, files, lang);
  const status = validation.valid
    ? t(lang, 'readyToGenerate')
    : `${t(lang, 'missingFields')}: ${validation.errors.length}`;

  const handleGenerate = async () => {
    if (!validation.valid) {
      alert(`Ошибки:\n${validation.errors.join('\n')}`);
      return;
    }

    setIsGenerating(true);
    try {
      const launchFile = files.find((f) => f.isLaunchFile) || files[0];
      const configWithTitle = {
        ...config,
        title: config.title || launchFile.file.name.replace(/\.[^/.]+$/, ''),
        language: lang,
      };

      const packageBlob = await generateScormPackage(files, configWithTitle);
      setLastPackage(packageBlob);
      setHasPackage(true);
      setShowPreview(true);
      setShowThankYou(true);
    } catch (error: any) {
      const msg = error?.message || 'Ошибка при генерации пакета';

      if (msg.includes('Failed to fetch') || msg.includes('подключиться')) {
        alert(
          `Ошибка подключения к backend серверу\n\n` +
            `Убедитесь, что:\n` +
            `1. Backend запущен: cd backend && python app.py\n` +
            `2. Сервер доступен на http://localhost:5001\n` +
            `3. Установлены зависимости: pip install -r backend/requirements.txt`,
        );
      } else {
        alert(`Ошибка: ${msg}`);
      }
    } finally {
      setIsGenerating(false);
    }
  };

  const handleDownload = () => {
    if (lastPackage) {
      const url = URL.createObjectURL(lastPackage);
      const a = document.createElement('a');
      a.href = url;
      a.download = `scorm-package-${Date.now()}.zip`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }
  };

  // ── Landing page ──────────────────────────────────────────────
  if (view === 'landing') {
    return (
      <div className="min-h-screen flex flex-col bg-gray-50 dark:bg-gray-900 transition-colors duration-200">
        <Header
          theme={theme}
          lang={lang}
          onThemeChange={setTheme}
          onLangChange={setLang}
          onHelpClick={() => setShowHelp(true)}
        />
        <LandingPage
          lang={lang}
          onNavigateToConstructor={() => setView('constructor')}
          onConvertSuccess={() => setShowThankYou(true)}
        />
        <SiteFooter lang={lang} />
        <ThankYouModal
          lang={lang}
          isOpen={showThankYou}
          onClose={() => setShowThankYou(false)}
        />
        <HelpModal isOpen={showHelp} onClose={() => setShowHelp(false)} />
      </div>
    );
  }

  // ── Constructor view ──────────────────────────────────────────
  return (
    <div className="min-h-screen flex flex-col bg-gray-50 dark:bg-gray-900 transition-colors duration-200">
      <Header
        theme={theme}
        lang={lang}
        onThemeChange={setTheme}
        onLangChange={setLang}
        onHelpClick={() => setShowHelp(true)}
      />

      <main className="flex-1 flex flex-col min-h-0">
        <div className="flex-1 grid grid-cols-1 lg:grid-cols-2 gap-6 p-4 sm:p-6 max-w-7xl mx-auto w-full overflow-hidden">
          {/* Left — File Upload */}
          <div className="flex flex-col min-h-0">
            <div className="mb-4 flex items-center gap-3">
              <button
                onClick={() => setView('landing')}
                className="p-2 -ml-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors cursor-pointer"
                title={t(lang, 'back')}
              >
                <ArrowLeft className="w-5 h-5 text-gray-600 dark:text-gray-300" />
              </button>
              <h2 className="text-lg sm:text-xl font-bold text-gray-900 dark:text-white">
                {t(lang, 'courseArea')}
              </h2>
            </div>
            <div className="flex-1 overflow-y-auto">
              <FileUpload files={files} onFilesChange={setFiles} />
            </div>
          </div>

          {/* Right — Settings */}
          <div className="flex flex-col min-h-0 lg:border-l lg:border-gray-200 lg:dark:border-gray-700 lg:pl-6 pt-6 lg:pt-0 border-t border-gray-200 dark:border-gray-700">
            <div className="mb-4">
              <h2 className="text-lg sm:text-xl font-bold text-gray-900 dark:text-white">
                {t(lang, 'settingsPanel')}
              </h2>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                {t(lang, 'settingsHint')}
              </p>
            </div>
            <div className="flex-1 overflow-hidden">
              <SettingsPanel lang={lang} config={config} onConfigChange={setConfig} />
            </div>
          </div>
        </div>
      </main>

      <Footer
        lang={lang}
        status={status}
        canGenerate={validation.valid}
        hasPackage={hasPackage}
        onGenerate={handleGenerate}
        onDownload={handleDownload}
        isGenerating={isGenerating}
      />

      <SiteFooter lang={lang} />

      <HelpModal isOpen={showHelp} onClose={() => setShowHelp(false)} />

      <ThankYouModal
        lang={lang}
        isOpen={showThankYou}
        onClose={() => setShowThankYou(false)}
      />

      <PackagePreviewModal
        lang={lang}
        isOpen={showPreview}
        onClose={() => setShowPreview(false)}
        onDownload={handleDownload}
        onPlay={() => setShowPlayer(true)}
        packageBlob={lastPackage}
        config={{
          ...config,
          title:
            config.title ||
            (files.find((f) => f.isLaunchFile) || files[0])?.file.name.replace(
              /\.[^/.]+$/,
              '',
            ) ||
            t(lang, 'scormCourse'),
        }}
        files={files}
      />

      {lastPackage && showPlayer && (
        <ScormPlayer
          lang={lang}
          packageBlob={lastPackage}
          config={config}
          onClose={() => setShowPlayer(false)}
        />
      )}
    </div>
  );
}

export default App;

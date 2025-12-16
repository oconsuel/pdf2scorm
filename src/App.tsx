import { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { Footer } from './components/Footer';
import { FileUpload } from './components/FileUpload';
import { SettingsPanel } from './components/SettingsPanel';
import { HelpModal } from './components/HelpModal';
import { PackagePreviewModal } from './components/PackagePreviewModal';
import { ScormPlayer } from './components/ScormPlayer';
import { UploadedFile, SCORMConfig, Theme, ConversionMode } from './types';
import { defaultConfig } from './utils/configPresets';
import { validateConfig, generateScormPackage } from './utils/scormGenerator';

function App() {
  const [theme, setTheme] = useState<Theme>('light');
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [config, setConfig] = useState<SCORMConfig>(defaultConfig);
  const [showHelp, setShowHelp] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [hasPackage, setHasPackage] = useState(false);
  const [lastPackage, setLastPackage] = useState<Blob | null>(null);
  const [showPreview, setShowPreview] = useState(false);
  const [showPlayer, setShowPlayer] = useState(false);
  const [conversionMode, setConversionMode] = useState<ConversionMode>('lecture_based');

  useEffect(() => {
    // Применяем тему
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [theme]);

  const validation = validateConfig(config, files);
  const status = validation.valid
    ? 'Готово к генерации'
    : `Отсутствуют обязательные поля: ${validation.errors.length}`;

  const handleGenerate = async () => {
    if (!validation.valid) {
      alert(`Ошибки:\n${validation.errors.join('\n')}`);
      return;
    }

    setIsGenerating(true);
    try {
      // Автоматически определяем title из launch файла, если не указан
      const launchFile = files.find(f => f.isLaunchFile) || files[0];
      const configWithTitle = {
        ...config,
        title: config.title || launchFile.file.name.replace(/\.[^/.]+$/, ''),
      };
      
      // Используем выбранный режим
      const packageBlob = await generateScormPackage(files, configWithTitle, conversionMode);
      setLastPackage(packageBlob);
      setHasPackage(true);
      setShowPreview(true); // Показываем превью после успешной генерации
    } catch (error: any) {
      const errorMessage = error?.message || 'Ошибка при генерации пакета';
      
      // Показываем более понятное сообщение об ошибке
      if (errorMessage.includes('Failed to fetch') || errorMessage.includes('подключиться')) {
        alert(
          `Ошибка подключения к backend серверу\n\n` +
          `Убедитесь, что:\n` +
          `1. Backend запущен (откройте новый терминал):\n` +
          `   cd backend\n` +
          `   python app.py\n\n` +
          `2. Сервер доступен на http://localhost:5001\n\n` +
          `3. Установлены зависимости:\n` +
          `   pip install -r backend/requirements.txt`
        );
      } else {
        alert(`Ошибка: ${errorMessage}`);
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

  return (
    <div className="min-h-screen flex flex-col bg-gray-50 dark:bg-gray-900 transition-colors duration-200">
      <Header
        theme={theme}
        onThemeChange={setTheme}
        onHelpClick={() => setShowHelp(true)}
      />

      <main className="flex-1 flex flex-col min-h-0">
        <div className="flex-1 grid grid-cols-1 lg:grid-cols-2 gap-6 p-4 sm:p-6 max-w-7xl mx-auto w-full overflow-hidden">
          {/* Left Column - File Upload */}
          <div className="flex flex-col min-h-0">
            <div className="mb-4">
              <h2 className="text-lg sm:text-xl font-bold text-gray-900 dark:text-white">
                Рабочая область курса
              </h2>
            </div>
            <div className="flex-1 overflow-y-auto">
              <FileUpload
                files={files}
                onFilesChange={setFiles}
              />
            </div>
          </div>

          {/* Right Column - Settings */}
          <div className="flex flex-col min-h-0 lg:border-l lg:border-gray-200 lg:dark:border-gray-700 lg:pl-6 pt-6 lg:pt-0 border-t border-gray-200 dark:border-gray-700">
            <div className="mb-4">
              <div className="flex items-center justify-between">
                <h2 className="text-lg sm:text-xl font-bold text-gray-900 dark:text-white">
                  Панель настроек SCORM
                </h2>
                {/* Переключатель режима */}
                <div className="flex items-center space-x-2">
                  <span className="text-xs text-gray-500 dark:text-gray-400">Режим:</span>
                  <select
                    value={conversionMode}
                    onChange={(e) => setConversionMode(e.target.value as ConversionMode)}
                    className="text-xs px-2 py-1 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded text-gray-900 dark:text-white cursor-pointer"
                  >
                    <option value="lecture_based">Лекция</option>
                    <option value="page_based">Страницы</option>
                  </select>
                </div>
              </div>
              {conversionMode === 'lecture_based' && (
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  Режим "Лекция": PDF разбивается на логические страницы с автоматическим определением структуры
                </p>
              )}
              {conversionMode === 'page_based' && (
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  Режим "Страницы": каждая страница PDF становится отдельной страницей SCORM
                </p>
              )}
            </div>
            <div className="flex-1 overflow-hidden">
              <SettingsPanel config={config} onConfigChange={setConfig} />
            </div>
          </div>
        </div>
      </main>

      <Footer
        status={status}
        canGenerate={validation.valid}
        hasPackage={hasPackage}
        onGenerate={handleGenerate}
        onDownload={handleDownload}
        isGenerating={isGenerating}
      />

      <HelpModal isOpen={showHelp} onClose={() => setShowHelp(false)} />
      
      <PackagePreviewModal
        isOpen={showPreview}
        onClose={() => setShowPreview(false)}
        onDownload={handleDownload}
        onPlay={() => setShowPlayer(true)}
        packageBlob={lastPackage}
        config={{
          ...config,
          title: config.title || (files.find(f => f.isLaunchFile) || files[0])?.file.name.replace(/\.[^/.]+$/, '') || 'SCORM Курс',
        }}
        files={files}
      />
      
      {lastPackage && showPlayer && (
        <ScormPlayer
          packageBlob={lastPackage}
          config={config}
          onClose={() => setShowPlayer(false)}
        />
      )}
    </div>
  );
}

export default App;


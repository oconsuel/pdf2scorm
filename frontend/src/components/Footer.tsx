import { Download, Package } from 'lucide-react';

interface FooterProps {
  status: string;
  canGenerate: boolean;
  hasPackage: boolean;
  onGenerate: () => void;
  onDownload: () => void;
  isGenerating: boolean;
}

export function Footer({
  status,
  canGenerate,
  hasPackage,
  onGenerate,
  onDownload,
  isGenerating,
}: FooterProps) {
  return (
    <footer className="bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 shadow-lg">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 py-3 sm:py-0 sm:h-16">
          <div className="flex items-center space-x-2">
            <div
              className={`w-2 h-2 rounded-full ${
                canGenerate ? 'bg-green-500' : 'bg-yellow-500'
              } animate-pulse`}
            />
            <span className="text-xs sm:text-sm text-gray-600 dark:text-gray-400">{status}</span>
          </div>
          
          <div className="flex items-center space-x-2 sm:space-x-3 w-full sm:w-auto">
            {hasPackage && (
              <button
                onClick={onDownload}
                className="btn-secondary flex items-center space-x-2 flex-1 sm:flex-initial text-sm"
              >
                <Download className="w-4 h-4" />
                <span className="hidden sm:inline">Скачать последний пакет</span>
                <span className="sm:hidden">Скачать</span>
              </button>
            )}
            
            <button
              onClick={onGenerate}
              disabled={!canGenerate || isGenerating}
              className="btn-primary flex items-center justify-center space-x-2 flex-1 sm:flex-initial text-sm"
            >
              {isGenerating ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  <span>Генерация...</span>
                </>
              ) : (
                <>
                  <Package className="w-4 h-4" />
                  <span className="hidden sm:inline">Создать SCORM пакет</span>
                  <span className="sm:hidden">Создать</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </footer>
  );
}


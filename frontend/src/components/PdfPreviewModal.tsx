import { useState, useEffect, useRef } from 'react';
import { X, Check, CheckSquare, Square } from 'lucide-react';
import * as pdfjsLib from 'pdfjs-dist';

// Настройка worker для pdf.js
if (typeof window !== 'undefined') {
  pdfjsLib.GlobalWorkerOptions.workerSrc = `https://unpkg.com/pdfjs-dist@${pdfjsLib.version}/build/pdf.worker.min.mjs`;
}

interface PdfPreviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  file: File;
  selectedPages?: number[];
  onPagesSelect: (pages: number[]) => void;
}

export function PdfPreviewModal({
  isOpen,
  onClose,
  file,
  selectedPages,
  onPagesSelect,
}: PdfPreviewModalProps) {
  const [numPages, setNumPages] = useState<number>(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Set<number>>(
    new Set(selectedPages || [])
  );
  const [fileData, setFileData] = useState<Uint8Array | null>(null);
  const [pdfDoc, setPdfDoc] = useState<any>(null);
  const [thumbnails, setThumbnails] = useState<Map<number, string>>(new Map());

  // Загрузка PDF документа
  useEffect(() => {
    if (isOpen && file) {
      setLoading(true);
      setError(null);
      setNumPages(0);
      setPdfDoc(null);
      setThumbnails(new Map());
      
      // Проверяем, что файл действительно PDF
      if (file.type !== 'application/pdf' && !file.name.toLowerCase().endsWith('.pdf')) {
        setError('Файл не является PDF документом');
        setLoading(false);
        return;
      }
      
      const loadPdf = async () => {
        try {
          // Читаем файл как ArrayBuffer
          const arrayBuffer = await file.arrayBuffer();
          const uint8Array = new Uint8Array(arrayBuffer);
          setFileData(uint8Array);
          
          
          // Загружаем PDF документ
          const loadingTask = pdfjsLib.getDocument({ data: uint8Array });
          const pdf = await loadingTask.promise;
          
          
          setPdfDoc(pdf);
          setNumPages(pdf.numPages);
          setLoading(false);
          
          // Если страницы не выбраны, выбираем все
          if (selectedPages && selectedPages.length > 0) {
            setSelected(new Set(selectedPages));
          } else {
            const allPages = Array.from({ length: pdf.numPages }, (_, i) => i + 1);
            setSelected(new Set(allPages));
          }
          
          // Генерируем миниатюры для всех страниц
          generateThumbnails(pdf);
        } catch (err: any) {
          console.error('Error loading PDF:', err);
          setError(`Ошибка загрузки PDF: ${err?.message || 'Неизвестная ошибка'}`);
          setLoading(false);
        }
      };
      
      loadPdf();
    }
  }, [isOpen, file, selectedPages]);

  // Генерация миниатюр страниц
  const generateThumbnails = async (pdf: any) => {
    const newThumbnails = new Map<string, number>();
    
    for (let pageNum = 1; pageNum <= pdf.numPages; pageNum++) {
      try {
        const page = await pdf.getPage(pageNum);
        const viewport = page.getViewport({ scale: 0.3 }); // Маленький масштаб для миниатюр
        
        const canvas = document.createElement('canvas');
        const context = canvas.getContext('2d');
        if (!context) continue;
        
        canvas.height = viewport.height;
        canvas.width = viewport.width;
        
        await page.render({
          canvasContext: context,
          viewport: viewport,
        }).promise;
        
        const thumbnailUrl = canvas.toDataURL('image/png');
        newThumbnails.set(pageNum, thumbnailUrl);
        setThumbnails(new Map(newThumbnails));
      } catch (err) {
        console.error(`Error generating thumbnail for page ${pageNum}:`, err);
      }
    }
  };


  const togglePage = (pageNum: number) => {
    setSelected((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(pageNum)) {
        newSet.delete(pageNum);
      } else {
        newSet.add(pageNum);
      }
      return newSet;
    });
  };

  const selectAll = () => {
    if (numPages > 0) {
      const allPages = Array.from({ length: numPages }, (_, i) => i + 1);
      setSelected(new Set(allPages));
    }
  };

  const deselectAll = () => {
    setSelected(new Set());
  };

  const handleApply = () => {
    // Если ничего не выбрано, передаем все страницы (пустой массив означает "все")
    // Или если выбраны все страницы, тоже передаем пустой массив для оптимизации
    let pagesArray: number[];
    if (selected.size === 0) {
      // Ничего не выбрано - передаем все страницы
      pagesArray = Array.from({ length: numPages }, (_, i) => i + 1);
    } else if (selected.size === numPages) {
      // Выбраны все страницы - передаем пустой массив (означает "все")
      pagesArray = [];
    } else {
      // Выбраны конкретные страницы
      pagesArray = Array.from(selected).sort((a, b) => a - b);
    }
    onPagesSelect(pagesArray);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 animate-fade-in"
      onClick={onClose}
    >
      <div
        className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl max-w-6xl w-full mx-4 max-h-[90vh] flex flex-col animate-slide-up"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="sticky top-0 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-6 py-4 flex items-center justify-between flex-shrink-0">
          <div className="flex items-center space-x-4">
            <h2 className="text-xl font-bold text-gray-900 dark:text-white">
              Предпросмотр PDF: {file.name}
            </h2>
            {numPages > 0 && (
              <span className="text-sm text-gray-500 dark:text-gray-400">
                Всего страниц: {numPages} | Выбрано: {selected.size}
              </span>
            )}
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors cursor-pointer"
            aria-label="Закрыть"
          >
            <X className="w-5 h-5 text-gray-600 dark:text-gray-300" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-hidden flex">
          {/* Main Content - Page Thumbnails Grid */}
          <div className="flex-1 overflow-y-auto bg-gray-50 dark:bg-gray-900 p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                Выберите страницы для включения в SCORM пакет
              </h3>
              <div className="flex space-x-2">
                <button
                  onClick={selectAll}
                  disabled={numPages === 0}
                  className="px-3 py-1.5 text-sm bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Выбрать все
                </button>
                <button
                  onClick={deselectAll}
                  disabled={numPages === 0}
                  className="px-3 py-1.5 text-sm bg-gray-300 dark:bg-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-400 dark:hover:bg-gray-500 transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Снять все
                </button>
              </div>
            </div>

            {loading ? (
              <div className="text-center py-16 text-gray-500 dark:text-gray-400">
                <div className="w-16 h-16 border-4 border-primary-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
                <p>Загрузка PDF...</p>
              </div>
            ) : error ? (
              <div className="text-center py-16">
                <div className="text-red-500 mb-4 font-semibold">Ошибка загрузки PDF</div>
                <div className="text-gray-600 dark:text-gray-400 text-sm mb-4">{error}</div>
                <button
                  onClick={() => {
                    setError(null);
                    setLoading(true);
                    setNumPages(0);
                    setPdfDoc(null);
                    // Перезагружаем файл
                    const loadPdf = async () => {
                      try {
                        const arrayBuffer = await file.arrayBuffer();
                        const uint8Array = new Uint8Array(arrayBuffer);
                        const loadingTask = pdfjsLib.getDocument({ data: uint8Array });
                        const pdf = await loadingTask.promise;
                        setPdfDoc(pdf);
                        setNumPages(pdf.numPages);
                        setLoading(false);
                        generateThumbnails(pdf);
                      } catch (err: any) {
                        setError(`Ошибка: ${err?.message || 'Неизвестная ошибка'}`);
                        setLoading(false);
                      }
                    };
                    loadPdf();
                  }}
                  className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors cursor-pointer"
                >
                  Попробовать снова
                </button>
              </div>
            ) : (
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
                {Array.from({ length: numPages }, (_, i) => {
                  const pageNum = i + 1;
                  const isSelected = selected.has(pageNum);
                  const thumbnail = thumbnails.get(pageNum);
                  
                  return (
                    <div
                      key={pageNum}
                      onClick={() => togglePage(pageNum)}
                      className={`
                        relative cursor-pointer rounded-lg border-2 transition-all duration-200
                        ${
                          isSelected
                            ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20 shadow-lg scale-105'
                            : 'border-gray-300 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500 hover:shadow-md'
                        }
                      `}
                    >
                      <div className="aspect-[3/4] bg-white dark:bg-gray-800 rounded-t-lg overflow-hidden flex items-center justify-center">
                        {thumbnail ? (
                          <img
                            src={thumbnail}
                            alt={`Страница ${pageNum}`}
                            className="w-full h-full object-contain"
                          />
                        ) : (
                          <div className="text-xs text-gray-400">Загрузка...</div>
                        )}
                      </div>
                      <div className="p-2 bg-white dark:bg-gray-800 rounded-b-lg flex items-center justify-center">
                        <span className="text-xs font-medium text-gray-700 dark:text-gray-300">
                          {pageNum}
                        </span>
                        {isSelected && (
                          <div className="absolute top-2 right-2">
                            <div className="w-6 h-6 bg-primary-600 rounded-full flex items-center justify-center">
                              <CheckSquare className="w-4 h-4 text-white" />
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-6 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 flex-shrink-0">
          <div className="text-sm text-gray-600 dark:text-gray-400">
            {selected.size > 0
              ? `Выбрано страниц: ${selected.size} из ${numPages}`
              : 'Выберите страницы для включения в SCORM пакет'}
          </div>
          <div className="flex items-center space-x-3">
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors cursor-pointer"
            >
              Отмена
            </button>
            <button
              onClick={handleApply}
              disabled={numPages === 0}
              className="px-6 py-2 text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 rounded-lg transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
            >
              <Check className="w-4 h-4" />
              <span>Применить ({selected.size > 0 ? selected.size : numPages})</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

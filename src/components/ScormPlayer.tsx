import { useState, useEffect, useRef } from 'react';
import { X, Play, Loader, Menu, ChevronRight, ChevronLeft } from 'lucide-react';
import JSZip from 'jszip';
import { SCORMConfig } from '../types';

interface ScormPlayerProps {
  packageBlob: Blob;
  config: SCORMConfig;
  onClose: () => void;
}

interface ManifestData {
  launchFile: string;
  title: string;
  files: Map<string, string>; // path -> content
}

interface ScoItem {
  identifier: string;
  title: string;
  href: string;
  order: number;
}

export function ScormPlayer({ packageBlob, config, onClose }: ScormPlayerProps) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [manifest, setManifest] = useState<ManifestData | null>(null);
  const [launchUrl, setLaunchUrl] = useState<string | null>(null);
  const [scoItems, setScoItems] = useState<ScoItem[]>([]);
  const [currentScoIndex, setCurrentScoIndex] = useState(0);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const blobUrlRef = useRef<string | null>(null);
  const resourceUrlsRef = useRef<Map<string, string>>(new Map());
  const fileMapRef = useRef<Map<string, Blob>>(new Map());
  const textFilesRef = useRef<Map<string, string>>(new Map());

  useEffect(() => {
    loadPackage();
    return () => {
      // Очистка blob URL при размонтировании
      if (blobUrlRef.current) {
        URL.revokeObjectURL(blobUrlRef.current);
      }
    };
  }, [packageBlob]);

  const loadPackage = async () => {
    try {
      setLoading(true);
      setError(null);

      // Распаковываем ZIP
      const zip = await JSZip.loadAsync(packageBlob);
      const files: Map<string, string> = new Map();

      // Извлекаем все файлы (только текстовые)
      for (const [path, file] of Object.entries(zip.files)) {
        if (!file.dir) {
          // Пробуем извлечь как текст только для текстовых файлов
          const ext = path.split('.').pop()?.toLowerCase();
          const textExtensions = ['html', 'htm', 'js', 'css', 'xml', 'json', 'txt'];
          if (ext && textExtensions.includes(ext)) {
            try {
              const content = await file.async('string');
              files.set(path, content);
            } catch (e) {
            }
          }
        }
      }

      // Парсим imsmanifest.xml
      const manifestContent = files.get('imsmanifest.xml');
      if (!manifestContent) {
        throw new Error('imsmanifest.xml не найден в пакете');
      }

      const parser = new DOMParser();
      const manifestDoc = parser.parseFromString(manifestContent, 'text/xml');

      // Проверяем на ошибки парсинга
      const parserError = manifestDoc.querySelector('parsererror');
      if (parserError) {
        throw new Error('Ошибка парсинга XML: ' + parserError.textContent);
      }

      let launchFile = '';
      let title = 'SCORM Курс';
      const scoList: ScoItem[] = [];

      // Получаем название из organization
      const orgTitle = manifestDoc.querySelector('organization > title');
      if (orgTitle) {
        title = orgTitle.textContent || title;
      }

      // Парсим все items и resources для создания списка SCO
      const items = manifestDoc.querySelectorAll('item');
      const allResources = manifestDoc.querySelectorAll('resource');
      
      // Создаём карту resources по identifier
      const resourceMap = new Map<string, { href: string; title: string }>();
      for (const resource of Array.from(allResources)) {
        const identifier = resource.getAttribute('identifier') || '';
        const href = resource.getAttribute('href') || '';
        const scormType = resource.getAttribute('scormType') || 
                         resource.getAttributeNS('http://www.adlnet.org/xsd/adlcp_v1p3', 'scormType');
        
        if (scormType === 'sco' && href) {
          // Получаем title из соответствующего item
          let itemTitle = '';
          const item = manifestDoc.querySelector(`item[identifierref="${identifier}"]`);
          if (item) {
            const titleEl = item.querySelector('title');
            if (titleEl) {
              itemTitle = titleEl.textContent || '';
            }
          }
          
          resourceMap.set(identifier, { href, title: itemTitle || href });
        }
      }

      // Собираем список SCO из items
      let order = 0;
      for (const item of Array.from(items)) {
        const identifierref = item.getAttribute('identifierref');
        if (identifierref) {
          const resource = resourceMap.get(identifierref);
          if (resource && resource.href) {
            const itemTitle = item.querySelector('title');
            const scoTitle = itemTitle?.textContent || resource.title || resource.href;
            
            scoList.push({
              identifier: identifierref,
              title: scoTitle,
              href: resource.href,
              order: order++,
            });
          }
        }
      }

      // Если не нашли через items, ищем напрямую в resources
      if (scoList.length === 0) {
        for (const resource of Array.from(allResources)) {
          const scormType = resource.getAttribute('scormType') || 
                           resource.getAttributeNS('http://www.adlnet.org/xsd/adlcp_v1p3', 'scormType');
          if (scormType === 'sco') {
            const href = resource.getAttribute('href') || '';
            if (href) {
              const identifier = resource.getAttribute('identifier') || '';
              scoList.push({
                identifier,
                title: href,
                href,
                order: order++,
              });
            }
          }
        }
      }

      // Если всё ещё пусто, ищем HTML файлы
      if (scoList.length === 0) {
        const htmlFiles: string[] = [];
        for (const [path] of files.entries()) {
          if (path.endsWith('.html') || path.endsWith('.htm')) {
            if (!path.includes('manifest') && path !== 'index.html') {
              htmlFiles.push(path);
            }
          }
        }
        // Числовая сортировка по номеру страницы (page_1.html, page_2.html, ...)
        htmlFiles.sort((a, b) => {
          const matchA = a.match(/page_(\d+)\.html/);
          const matchB = b.match(/page_(\d+)\.html/);
          if (matchA && matchB) {
            return parseInt(matchA[1], 10) - parseInt(matchB[1], 10);
          }
          // Если не найден номер, используем строковую сортировку
          return a.localeCompare(b);
        });
        for (const path of htmlFiles) {
          scoList.push({
            identifier: path,
            title: path,
            href: path,
            order: order++,
          });
        }
      }

      if (scoList.length === 0) {
        throw new Error('SCO элементы не найдены в manifest. Доступные файлы: ' + Array.from(files.keys()).join(', '));
      }

      // Устанавливаем первый SCO как launch файл
      launchFile = scoList[0].href;
      setScoItems(scoList);

      // Создаём blob URL для всех файлов
      const fileMap = new Map<string, Blob>();
      const resourceUrls = new Map<string, string>();
      
      // Конвертируем все файлы в Blob
      for (const [path, file] of Object.entries(zip.files)) {
        if (!file.dir) {
          let blob: Blob;
          const ext = path.split('.').pop()?.toLowerCase();
          const textExtensions = ['html', 'htm', 'js', 'css', 'xml', 'json', 'txt'];
          
          if (ext && textExtensions.includes(ext)) {
            // Текстовые файлы - используем уже извлечённое содержимое или извлекаем заново
            let content = files.get(path);
            if (!content) {
              try {
                content = await file.async('string');
              } catch (e) {
                content = '';
              }
            }
            blob = new Blob([content], { type: getMimeType(path) });
          } else {
            // Бинарные файлы (изображения, видео и т.д.)
            blob = await file.async('blob');
          }
          fileMap.set(path, blob);
          // Создаём blob URL сразу
          resourceUrls.set(path, URL.createObjectURL(blob));
        }
      }
      
      resourceUrlsRef.current = resourceUrls;
      fileMapRef.current = fileMap;
      textFilesRef.current = files;

      // Создаём HTML страницу с mock SCORM API и iframe для первого SCO
      const firstScoUrl = await createScoUrl(launchFile, fileMap, files, resourceUrls, config);
      blobUrlRef.current = firstScoUrl;

      setManifest({ launchFile, title, files });
      setLaunchUrl(firstScoUrl);
      setCurrentScoIndex(0);
      setLoading(false);
    } catch (err: any) {
      setError(err.message || 'Ошибка при загрузке SCORM пакета');
      setLoading(false);
    }
  };

  const getMimeType = (path: string): string => {
    const ext = path.split('.').pop()?.toLowerCase();
    const mimeTypes: Record<string, string> = {
      html: 'text/html',
      htm: 'text/html',
      js: 'application/javascript',
      css: 'text/css',
      xml: 'text/xml',
      json: 'application/json',
    };
    return mimeTypes[ext || ''] || 'application/octet-stream';
  };

  const createScoUrl = async (scoFile: string, fileMap: Map<string, Blob>, textFiles: Map<string, string>, resourceUrls: Map<string, string>, scormConfig: SCORMConfig): Promise<string> => {
    // Получаем содержимое SCO файла
    let scoContent = textFiles.get(scoFile) || '';
    
    // Получаем содержимое SCORM_API_wrapper.js из ZIP архива
    let scormApiWrapperContent = '';
    const scormApiWrapperPath = 'SCORM_API_wrapper.js';
    if (textFiles.has(scormApiWrapperPath)) {
      scormApiWrapperContent = textFiles.get(scormApiWrapperPath) || '';
    } else {
      // Если не найден в textFiles, пробуем получить из fileMap
      const scormApiBlob = fileMap.get(scormApiWrapperPath);
      if (scormApiBlob) {
        scormApiWrapperContent = await scormApiBlob.text();
      }
    }
    
    // Заменяем <script src="SCORM_API_wrapper.js"></script> на inline скрипт
    if (scormApiWrapperContent) {
      const inlineScormApi = `<script>${scormApiWrapperContent}</script>`;
      // Заменяем все варианты ссылок на SCORM_API_wrapper.js
      scoContent = scoContent.replace(
        /<script[^>]*src\s*=\s*["']SCORM_API_wrapper\.js["'][^>]*><\/script>/gi,
        inlineScormApi
      );
      // Также заменяем варианты без закрывающего тега
      scoContent = scoContent.replace(
        /<script[^>]*src\s*=\s*["']SCORM_API_wrapper\.js["'][^>]*>/gi,
        inlineScormApi
      );
    }
    
    // Заменяем относительные пути на blob URLs
    // Определяем базовый путь для SCO файла
    const lastSlashIndex = scoFile.lastIndexOf('/');
    const basePath = lastSlashIndex >= 0 ? scoFile.substring(0, lastSlashIndex + 1) : '';
    
    // Обрабатываем src и href атрибуты
    scoContent = scoContent.replace(
      /(src|href)=["']([^"']+)["']/g,
      (match, attr, path) => {
        // Пропускаем абсолютные URL и data URI
        if (path.startsWith('http://') || path.startsWith('https://') || path.startsWith('data:') || path.startsWith('blob:')) {
          return match;
        }
        
        // Решаем относительный путь
        let resolvedPath = path;
        if (path.startsWith('/')) {
          // Абсолютный путь от корня пакета
          resolvedPath = path.substring(1); // Убираем ведущий /
        } else {
          // Относительный путь от SCO файла
          if (basePath) {
            resolvedPath = basePath + path;
          } else {
            // Если SCO файл в корне, путь уже правильный
            resolvedPath = path;
          }
        }
        
        // Нормализуем путь (убираем .. и .)
        const parts = resolvedPath.split('/');
        const normalized: string[] = [];
        for (const part of parts) {
          if (part === '..') {
            if (normalized.length > 0) {
              normalized.pop();
            }
          } else if (part !== '.' && part !== '') {
            normalized.push(part);
          }
        }
        resolvedPath = normalized.join('/');
        
        // Пробуем найти blob URL для ресурса
        // Проверяем точное совпадение
        let blobUrl = resourceUrls.get(resolvedPath);
        
        // Если не найдено, пробуем варианты с разными регистрами и путями
        if (!blobUrl) {
          // Пробуем найти в fileMap по разным вариантам пути
          for (const [filePath, blob] of fileMap.entries()) {
            // Нормализуем путь файла для сравнения
            const normalizedFilePath = filePath.split('/').filter((p: string) => p).join('/');
            const normalizedResolved = resolvedPath.split('/').filter((p: string) => p).join('/');
            
            if (normalizedFilePath.toLowerCase() === normalizedResolved.toLowerCase() ||
                normalizedFilePath.endsWith('/' + normalizedResolved) ||
                normalizedFilePath === normalizedResolved) {
              // Создаем blob URL для этого файла
              blobUrl = URL.createObjectURL(blob);
              resourceUrls.set(resolvedPath, blobUrl);
              break;
            }
          }
        }
        
        if (blobUrl) {
          return `${attr}="${blobUrl}"`;
        }
        
        // Если не найдено, оставляем оригинальный путь (может быть ошибка в пакете)
        console.warn(`Resource not found in package: ${resolvedPath} (original: ${path})`);
        return match;
      }
    );

    // Применяем настройки дизайна к CSS
    const playerStyle = scormConfig.playerStyle || {};
    const primaryColor = playerStyle.primaryColor || '#4CAF50';
    const theme = playerStyle.theme || 'auto';
    const highContrast = playerStyle.highContrast || false;
    const largeFont = playerStyle.largeFont || false;
    
    // Обновляем цвета в CSS
    scoContent = scoContent.replace(
      /background-color:\s*#4CAF50/g,
      `background-color: ${primaryColor}`
    );
    
    if (theme === 'dark' || (theme === 'auto' && highContrast)) {
      scoContent = scoContent.replace(
        /background-color:\s*#2c3e50/g,
        'background-color: #1a1a1a'
      );
    }
    
    // Добавляем стили для больших шрифтов
    if (largeFont) {
      const fontStyle = `
        <style>
          body { font-size: 1.2em !important; }
          .header h1 { font-size: 26px !important; }
          .page-info { font-size: 16px !important; }
        </style>
      `;
      scoContent = scoContent.replace('</head>', fontStyle + '</head>');
    }

    // Создаём конфигурацию для инжекции
    const configData = {
      progressCompletion: {
        rememberLastPage: scormConfig.progressCompletion?.rememberLastPage ?? true,
        saveOnEachTransition: scormConfig.progressCompletion?.saveOnEachTransition ?? true,
        askOnReentry: scormConfig.progressCompletion?.askOnReentry ?? false,
        progressMethod: scormConfig.progressCompletion?.progressMethod || 'screens',
        completionThreshold: scormConfig.progressCompletion?.completionThreshold || 80,
        successCriterion: scormConfig.progressCompletion?.successCriterion || 'score'
      }
    };
    
    // Создаём JSON без форматирования для безопасной вставки в строку
    const configJson = JSON.stringify(configData).replace(/</g, '\\u003c').replace(/>/g, '\\u003e');

    // Создаём mock SCORM API для SCORM 2004
    // ВАЖНО: используем безопасную вставку JSON
    const scormApi = `
      <script>
        // SCORM Configuration - ПРИМЕНЯЕМСЯ ПЕРЕД ВСЕМИ ФУНКЦИЯМИ
        try {
          window.SCORM_CONFIG = ${configJson};
        } catch (e) {
          window.SCORM_CONFIG = {};
        }
        
        // Mock SCORM 2004 API (API_1484_11)
        window.API_1484_11 = {
          data: {},
          
          Initialize: function(param) {
            this.data = {
              'cmi.completion_status': 'unknown',
              'cmi.success_status': 'unknown',
              'cmi.location': '',
              'cmi.suspend_data': '',
              'cmi.progress_measure': '0',
              'cmi.session_time': 'PT0H0M0S',
              'cmi.total_time': 'PT0H0M0S',
              'cmi.score.scaled': '0',
              'cmi.score.raw': '0',
              'cmi.score.min': '0',
              'cmi.score.max': '100',
            };
            return 'true';
          },
          
          GetValue: function(element) {
            return this.data[element] || '';
          },
          
          SetValue: function(element, value) {
            this.data[element] = value;
            return 'true';
          },
          
          Commit: function(param) {
            return 'true';
          },
          
          GetLastError: function() {
            return '0';
          },
          
          GetErrorString: function(errorCode) {
            return 'No Error';
          },
          
          GetDiagnostic: function(errorCode) {
            return 'No Error';
          },
          
          Terminate: function(param) {
            return 'true';
          }
        };
        
        // Также создаём window.API для совместимости
        window.API = window.API_1484_11;
        
        // Применяем настройки после загрузки страницы
        window.addEventListener('DOMContentLoaded', function() {
          // Переопределяем loadProgress для использования rememberLastPage
          if (typeof loadProgress === 'function') {
            var originalLoadProgress = loadProgress;
            window.loadProgress = function() {
              if (window.SCORM_CONFIG && window.SCORM_CONFIG.progressCompletion && window.SCORM_CONFIG.progressCompletion.rememberLastPage) {
                originalLoadProgress();
              }
            };
          }
          
          // Переопределяем saveProgress для использования saveOnEachTransition
          if (typeof saveProgress === 'function') {
            var originalSaveProgress = saveProgress;
            window.saveProgress = function() {
              if (!window.SCORM_CONFIG || !window.SCORM_CONFIG.progressCompletion || window.SCORM_CONFIG.progressCompletion.saveOnEachTransition) {
                originalSaveProgress();
                
                // Проверяем completion threshold
                if (window.SCORM_CONFIG && window.SCORM_CONFIG.progressCompletion && window.scorm && window.scorm.API && window.scorm.API.isPresent) {
                  var config = window.SCORM_CONFIG.progressCompletion;
                  var threshold = (config.completionThreshold || 80) / 100.0;
                  var progressMethod = config.progressMethod || 'screens';
                  
                  // Вычисляем прогресс
                  var progress = 0;
                  try {
                    var suspendData = window.scorm.get(window.scormVersion === "2004" ? "cmi.suspend_data" : "cmi.suspend_data");
                    if (suspendData && suspendData !== "" && suspendData !== "null") {
                      var progressData = JSON.parse(suspendData);
                      if (progressData.visitedPages && window.totalPages) {
                        if (progressMethod === 'screens') {
                          progress = progressData.visitedPages.length / window.totalPages;
                        } else if (progressMethod === 'combined') {
                          progress = (progressData.visitedPages.length / window.totalPages) * 0.5;
                        }
                      }
                    }
                  } catch (e) {
                  }
                  
                  // Проверяем completion
                  if (progress >= threshold) {
                    var statusField = window.scormVersion === "2004" ? "cmi.completion_status" : "cmi.core.lesson_status";
                    window.scorm.set(statusField, "completed");
                    window.scorm.save();
                  }
                }
              }
            };
          }
          
          // Обновляем автосохранение
          if (window.SCORM_CONFIG && window.SCORM_CONFIG.progressCompletion) {
            if (window.saveInterval && !window.SCORM_CONFIG.progressCompletion.saveOnEachTransition) {
              clearInterval(window.saveInterval);
            }
          }
        });
      </script>
    `;

    // ВАЖНО: Применяем настройки к HTML контенту
    // Удаляем существующую конфигурацию, если есть (чтобы избежать дублирования)
    if (scoContent.includes('window.SCORM_CONFIG')) {
      // Удаляем старую конфигурацию более аккуратно
      scoContent = scoContent.replace(
        /window\.SCORM_CONFIG\s*=\s*\{[^}]*\};?/g,
        ''
      );
    }
    
    // ВАЖНО: Порядок инжекции имеет значение!
    // 1. SCORM_API_wrapper.js (pipwerks) - уже заменён на inline скрипт выше
    // 2. Mock SCORM API и конфигурация - вставляем в начало <head>
    // Это гарантирует, что конфигурация будет доступна для всех функций
    if (scoContent.includes('</head>')) {
      // Вставляем в конец <head>, но перед </head>
      scoContent = scoContent.replace('</head>', scormApi + '</head>');
    } else if (scoContent.includes('<head>')) {
      // Если есть <head>, но нет </head>, вставляем после <head>
      scoContent = scoContent.replace('<head>', '<head>' + scormApi);
    } else if (scoContent.includes('<body>')) {
      // Если нет <head>, вставляем перед <body>
      scoContent = scoContent.replace('<body>', scormApi + '<body>');
    } else {
      // Последний вариант - в начало документа
      scoContent = scormApi + scoContent;
    }
    
    // Создаём blob URL для обработанного SCO файла
    const scoBlob = new Blob([scoContent], { type: 'text/html' });
    return URL.createObjectURL(scoBlob);
  };

  const switchToSco = async (index: number) => {
    if (index < 0 || index >= scoItems.length) return;
    
    const sco = scoItems[index];
    
    // Используем сохранённые файлы
    const fileMap = fileMapRef.current;
    const textFiles = textFilesRef.current;
    const resourceUrls = resourceUrlsRef.current;
    
    // Создаём новый URL для этого SCO
    const newScoUrl = await createScoUrl(
      sco.href,
      fileMap,
      textFiles,
      resourceUrls,
      config
    );
    
    // Освобождаем старый URL
    if (blobUrlRef.current) {
      URL.revokeObjectURL(blobUrlRef.current);
    }
    
    blobUrlRef.current = newScoUrl;
    setLaunchUrl(newScoUrl);
    setCurrentScoIndex(index);
  };

  if (loading) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 backdrop-blur-sm">
        <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl p-8 max-w-md w-full mx-4">
          <div className="flex flex-col items-center space-y-4">
            <Loader className="w-12 h-12 text-primary-600 dark:text-primary-400 animate-spin" />
            <p className="text-lg font-medium text-gray-900 dark:text-white">
              Загрузка SCORM пакета...
            </p>
            <p className="text-sm text-gray-500 dark:text-gray-400 text-center">
              Распаковка архива и подготовка к воспроизведению
            </p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 backdrop-blur-sm">
        <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl p-8 max-w-md w-full mx-4">
          <div className="flex flex-col items-center space-y-4">
            <div className="p-3 bg-red-100 dark:bg-red-900 rounded-full">
              <X className="w-8 h-8 text-red-600 dark:text-red-400" />
            </div>
            <p className="text-lg font-medium text-gray-900 dark:text-white">
              Ошибка загрузки
            </p>
            <p className="text-sm text-red-600 dark:text-red-400 text-center">
              {error}
            </p>
            <button
              onClick={onClose}
              className="px-6 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg transition-colors cursor-pointer"
            >
              Закрыть
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 z-50 flex flex-col bg-gray-900">
      {/* Header */}
      <div className="flex items-center justify-between p-4 bg-gray-800 border-b border-gray-700">
        <div className="flex items-center space-x-3">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-2 rounded-lg hover:bg-gray-700 transition-colors cursor-pointer"
            aria-label="Переключить меню"
          >
            <Menu className="w-5 h-5 text-gray-300" />
          </button>
          <div className="p-2 bg-primary-600 rounded-lg">
            <Play className="w-5 h-5 text-white" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-white">
              {manifest?.title || 'SCORM Курс'}
            </h2>
            <p className="text-xs text-gray-400">
              Режим предпросмотра • {currentScoIndex + 1} из {scoItems.length}
            </p>
          </div>
        </div>
        
        <div className="flex items-center space-x-2">
          <button
            onClick={() => switchToSco(currentScoIndex - 1)}
            disabled={currentScoIndex === 0}
            className="p-2 rounded-lg hover:bg-gray-700 transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
            aria-label="Предыдущая страница"
          >
            <ChevronLeft className="w-5 h-5 text-gray-300" />
          </button>
          <button
            onClick={() => switchToSco(currentScoIndex + 1)}
            disabled={currentScoIndex >= scoItems.length - 1}
            className="p-2 rounded-lg hover:bg-gray-700 transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
            aria-label="Следующая страница"
          >
            <ChevronRight className="w-5 h-5 text-gray-300" />
          </button>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-gray-700 transition-colors cursor-pointer"
            aria-label="Закрыть"
          >
            <X className="w-5 h-5 text-gray-300" />
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar Navigation */}
        {sidebarOpen && (
          <div className="w-64 bg-gray-800 border-r border-gray-700 overflow-y-auto">
            <div className="p-4">
              <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-3">
                Содержание
              </h3>
              <nav className="space-y-1">
                {scoItems.map((sco, index) => (
                  <button
                    key={sco.identifier}
                    onClick={() => switchToSco(index)}
                    className={`w-full text-left px-3 py-2 rounded-lg transition-colors cursor-pointer ${
                      index === currentScoIndex
                        ? 'bg-primary-600 text-white'
                        : 'text-gray-300 hover:bg-gray-700'
                    }`}
                  >
                    <div className="flex items-center space-x-2">
                      <span className="text-xs font-medium opacity-75">
                        {index + 1}.
                      </span>
                      <span className="text-sm truncate">
                        {sco.title}
                      </span>
                    </div>
                  </button>
                ))}
              </nav>
            </div>
          </div>
        )}

        {/* Player */}
        <div className="flex-1 relative">
          {launchUrl && (
            <iframe
              key={launchUrl} // Принудительная перезагрузка при смене URL
              ref={iframeRef}
              src={launchUrl}
              className="w-full h-full border-0"
              title="SCORM Player"
              sandbox="allow-scripts allow-forms allow-popups"
            />
          )}
        </div>
      </div>
    </div>
  );
}


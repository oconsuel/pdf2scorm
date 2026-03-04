import { useState, useRef, DragEvent } from 'react';
import { Upload, Trash2, Star, Eye } from 'lucide-react';
import { UploadedFile } from '../types';
import { formatFileSize, getFileIcon, validateFile, createFileId } from '../utils/fileUtils';
import { PdfPreviewModal } from './PdfPreviewModal';

interface FileUploadProps {
  files: UploadedFile[];
  onFilesChange: (files: UploadedFile[]) => void;
}

export function FileUpload({
  files,
  onFilesChange,
}: FileUploadProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<Record<string, number>>({});
  const [previewFile, setPreviewFile] = useState<UploadedFile | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    
    const droppedFiles = Array.from(e.dataTransfer.files);
    processFiles(droppedFiles);
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const selectedFiles = Array.from(e.target.files);
      processFiles(selectedFiles);
    }
  };

  const isPdfFile = (file: File) => {
    return file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf');
  };

  const processFiles = (newFiles: File[]) => {
    const validFiles: UploadedFile[] = [];
    let firstPdfFile: UploadedFile | null = null;
    
    newFiles.forEach((file) => {
      const validation = validateFile(file);
      if (validation.valid) {
        const uploadedFile: UploadedFile = {
          id: createFileId(),
          file,
          type: 'sco', // Все PDF файлы являются SCO
          isLaunchFile: files.length === 0, // Первый файл по умолчанию launch
          size: file.size,
          selectedPages: [], // Инициализируем пустым массивом для PDF
        };
        validFiles.push(uploadedFile);
        
        // Сохраняем первый PDF файл для автоматического открытия
        if (!firstPdfFile && isPdfFile(file)) {
          firstPdfFile = uploadedFile;
        }
        
        // Симуляция прогресса загрузки
        setUploadProgress((prev) => ({ ...prev, [uploadedFile.id]: 0 }));
        simulateUpload(uploadedFile.id);
      } else {
        // В реальном приложении здесь был бы toast
      }
    });
    
    if (validFiles.length > 0) {
      onFilesChange([...files, ...validFiles]);
      
      // Автоматически открываем предпросмотр для первого PDF файла
      if (firstPdfFile) {
        // Небольшая задержка, чтобы файл успел добавиться в список
        setTimeout(() => {
          setPreviewFile(firstPdfFile);
        }, 100);
      }
    }
  };

  const simulateUpload = (fileId: string) => {
    let progress = 0;
    const interval = setInterval(() => {
      progress += 10;
      setUploadProgress((prev) => ({ ...prev, [fileId]: progress }));
      
      if (progress >= 100) {
        clearInterval(interval);
        setTimeout(() => {
          setUploadProgress((prev) => {
            const newProgress = { ...prev };
            delete newProgress[fileId];
            return newProgress;
          });
        }, 500);
      }
    }, 100);
  };

  const removeFile = (id: string) => {
    onFilesChange(files.filter((f) => f.id !== id));
  };

  const toggleLaunchFile = (id: string) => {
    onFilesChange(
      files.map((f) => ({
        ...f,
        isLaunchFile: f.id === id ? !f.isLaunchFile : false,
      }))
    );
  };

  const handlePreviewPdf = (file: UploadedFile) => {
    setPreviewFile(file);
  };

  const handlePagesSelect = (fileId: string, pages: number[]) => {
    const updatedFiles = files.map((f) =>
      f.id === fileId ? { ...f, selectedPages: pages } : f
    );
    onFilesChange(updatedFiles);
  };

  return (
    <div className="space-y-4">
      {/* Drag & Drop Area */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`
          relative border-2 border-dashed rounded-2xl p-12 text-center cursor-pointer
          transition-all duration-300
          ${
            isDragging
              ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20 shadow-xl'
              : 'border-gray-300 dark:border-gray-600 hover:border-primary-400 hover:bg-gray-50 dark:hover:bg-gray-800 hover:shadow-lg'
          }
        `}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          onChange={handleFileSelect}
          className="hidden"
          accept=".pdf"
        />
        
        <div className="flex flex-col items-center space-y-4">
          <div
            className={`
              w-16 h-16 rounded-full flex items-center justify-center
              transition-all duration-300
              ${
                isDragging
                  ? 'bg-primary-500'
                  : 'bg-gray-200 dark:bg-gray-700'
              }
            `}
          >
            <Upload
              className={`w-8 h-8 ${
                isDragging ? 'text-white' : 'text-gray-500 dark:text-gray-400'
              }`}
            />
          </div>
          
          <div>
            <p className="text-lg font-medium text-gray-900 dark:text-white">
              Перетащите файлы сюда или нажмите для выбора
            </p>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              Поддерживаемый формат: PDF (.pdf)
            </p>
          </div>
        </div>
      </div>

      {/* Files List */}
      {files.length > 0 && (
        <div className="space-y-4">
          <div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              Загруженные файлы ({files.length})
            </h3>
          </div>

          <div className="space-y-2">
            {files.map((file) => (
              <div
                key={file.id}
                className="card group hover:shadow-xl transition-shadow duration-200"
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start space-x-3 flex-1 min-w-0">
                    <div className="text-2xl flex-shrink-0">
                      {getFileIcon(file.file.type)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center space-x-2">
                        <p className="font-medium text-gray-900 dark:text-white truncate">
                          {file.file.name}
                        </p>
                        {file.isLaunchFile && (
                          <Star className="w-4 h-4 text-yellow-500 fill-yellow-500 flex-shrink-0" />
                        )}
                      </div>
                      <p className="text-sm text-gray-500 dark:text-gray-400">
                        {formatFileSize(file.size)}
                        {isPdfFile(file.file) && file.selectedPages && file.selectedPages.length > 0 && (
                          <span className="ml-2 text-primary-600 dark:text-primary-400">
                            ({file.selectedPages.length} стр.)
                          </span>
                        )}
                      </p>
                    </div>
                  </div>
                  
                  <div className="flex items-center space-x-1 flex-shrink-0">
                    {isPdfFile(file.file) && (
                      <button
                        onClick={() => handlePreviewPdf(file)}
                        className="p-1.5 rounded-lg hover:bg-blue-100 dark:hover:bg-blue-900/30 transition-colors cursor-pointer"
                        aria-label="Preview PDF"
                        title="Предпросмотр и выбор страниц PDF"
                      >
                        <Eye className="w-4 h-4 text-blue-500" />
                      </button>
                    )}
                    <button
                      onClick={() => toggleLaunchFile(file.id)}
                      className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors cursor-pointer"
                      aria-label="Toggle launch file"
                      title={file.isLaunchFile ? 'Убрать как Launch file' : 'Установить как Launch file'}
                    >
                      <Star
                        className={`w-4 h-4 ${
                          file.isLaunchFile
                            ? 'text-yellow-500 fill-yellow-500'
                            : 'text-gray-400'
                        }`}
                      />
                    </button>
                    <button
                      onClick={() => removeFile(file.id)}
                      className="p-1.5 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/30 transition-colors cursor-pointer"
                      aria-label="Remove file"
                    >
                      <Trash2 className="w-4 h-4 text-red-500" />
                    </button>
                  </div>
                </div>

                {/* Progress Bar */}
                {uploadProgress[file.id] !== undefined && (
                  <div className="mt-3">
                    <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                      <div
                        className="bg-primary-600 h-2 rounded-full transition-all duration-300"
                        style={{ width: `${uploadProgress[file.id]}%` }}
                      />
                    </div>
                  </div>
                )}

              </div>
            ))}
          </div>
        </div>
      )}

      {/* PDF Preview Modal */}
      {previewFile && (
        <PdfPreviewModal
          isOpen={!!previewFile}
          onClose={() => setPreviewFile(null)}
          file={previewFile.file}
          selectedPages={previewFile.selectedPages}
          onPagesSelect={(pages) => {
            handlePagesSelect(previewFile.id, pages);
            setPreviewFile(null);
          }}
        />
      )}
    </div>
  );
}

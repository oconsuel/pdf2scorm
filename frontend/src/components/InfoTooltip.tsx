import { Info } from 'lucide-react';
import { useState, useRef, useEffect } from 'react';

interface InfoTooltipProps {
  content: string | React.ReactNode;
  position?: 'top' | 'bottom' | 'left' | 'right';
}

export function InfoTooltip({ content, position = 'top' }: InfoTooltipProps) {
  const [isVisible, setIsVisible] = useState(false);
  const tooltipRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isVisible && tooltipRef.current && containerRef.current) {
      const tooltip = tooltipRef.current;
      const container = containerRef.current;
      const rect = container.getBoundingClientRect();
      const tooltipRect = tooltip.getBoundingClientRect();
      
      // Проверяем границы viewport
      if (position === 'top' && rect.top < tooltipRect.height + 20) {
        tooltip.style.top = `${rect.bottom + 8}px`;
        tooltip.style.bottom = 'auto';
        tooltip.classList.remove('bottom-full', 'mb-2');
        tooltip.classList.add('top-full', 'mt-2');
      } else if (position === 'bottom' && rect.bottom + tooltipRect.height + 20 > window.innerHeight) {
        tooltip.style.bottom = `${window.innerHeight - rect.top + 8}px`;
        tooltip.style.top = 'auto';
        tooltip.classList.remove('top-full', 'mt-2');
        tooltip.classList.add('bottom-full', 'mb-2');
      }
    }
  }, [isVisible, position]);

  const positionClasses = {
    top: 'bottom-full left-1/2 -translate-x-1/2 mb-2',
    bottom: 'top-full left-1/2 -translate-x-1/2 mt-2',
    left: 'right-full top-1/2 -translate-y-1/2 mr-2',
    right: 'left-full top-1/2 -translate-y-1/2 ml-2',
  };

  return (
    <div ref={containerRef} className="relative inline-flex items-center">
      <button
        type="button"
        onMouseEnter={() => setIsVisible(true)}
        onMouseLeave={() => setIsVisible(false)}
        onFocus={() => setIsVisible(true)}
        onBlur={() => setIsVisible(false)}
        className="p-1 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500 cursor-pointer flex-shrink-0"
        aria-label="Информация"
      >
        <Info className="w-4 h-4 text-primary-600 dark:text-primary-400" />
      </button>
      
      {isVisible && (
        <div
          ref={tooltipRef}
          className={`absolute z-50 w-64 max-w-[90vw] p-3 bg-gray-900 text-white text-xs rounded-lg shadow-xl pointer-events-none ${positionClasses[position]}`}
          role="tooltip"
        >
          <div className="whitespace-pre-wrap break-words">{content}</div>
          {/* Arrow */}
          <div
            className={`absolute ${
              position === 'top'
                ? 'top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-900'
                : position === 'bottom'
                ? 'bottom-full left-1/2 -translate-x-1/2 border-4 border-transparent border-b-gray-900'
                : position === 'left'
                ? 'left-full top-1/2 -translate-y-1/2 border-4 border-transparent border-l-gray-900'
                : 'right-full top-1/2 -translate-y-1/2 border-4 border-transparent border-r-gray-900'
            }`}
          />
        </div>
      )}
    </div>
  );
}

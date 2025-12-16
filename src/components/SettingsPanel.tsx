import { useState } from 'react';
import { SCORMConfig } from '../types';
import { ProgressCompletionTab } from './settings/ProgressCompletionTab';
import { LearnerPreferencesTab } from './settings/LearnerPreferencesTab';
import { PlayerStyleTab } from './settings/PlayerStyleTab';
import { LivePreview } from './LivePreview';

interface SettingsPanelProps {
  config: SCORMConfig;
  onConfigChange: (config: SCORMConfig) => void;
}

const tabs = [
  { id: 'progress', label: 'Прогресс и завершение', number: 1 },
  { id: 'preferences', label: 'Предпочтения обучающегося', number: 2 },
  { id: 'player', label: 'Стиль плеера и UX', number: 3 },
];

export function SettingsPanel({ config, onConfigChange }: SettingsPanelProps) {
  const [activeTab, setActiveTab] = useState('progress');

  const updateConfig = (section: keyof SCORMConfig, updates: any) => {
    onConfigChange({
      ...config,
      [section]: {
        ...config[section],
        ...updates,
      },
    });
  };

  const currentTabIndex = tabs.findIndex(tab => tab.id === activeTab);

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 flex flex-col min-h-0">
        {/* Timeline Tabs */}
        <div className="border-b border-gray-200 dark:border-gray-700 px-4 py-3 overflow-x-auto">
          <div className="flex items-center space-x-2 min-w-max">
            {tabs.map((tab, index) => {
              const isActive = tab.id === activeTab;
              const isCompleted = index < currentTabIndex;
              
              return (
                <div key={tab.id} className="flex items-center">
                  <button
                    onClick={() => setActiveTab(tab.id)}
                    className={`
                      flex items-center space-x-2 px-4 py-2 rounded-lg transition-all duration-200 cursor-pointer
                      ${isActive 
                        ? 'bg-primary-100 dark:bg-primary-900 text-primary-700 dark:text-primary-300 shadow-md' 
                        : 'hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300'
                      }
                    `}
                  >
                    <div className={`
                      w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold
                      transition-all duration-200
                      ${isActive 
                        ? 'bg-primary-600 text-white' 
                        : isCompleted
                        ? 'bg-green-500 text-white'
                        : 'bg-gray-300 dark:bg-gray-600 text-gray-700 dark:text-gray-300'
                      }
                    `}>
                      {isCompleted ? '✓' : tab.number}
                    </div>
                    <span className="text-sm font-medium whitespace-nowrap">{tab.label}</span>
                  </button>
                  
                  {index < tabs.length - 1 && (
                    <div className={`
                      w-12 h-0.5 mx-2 transition-colors duration-200
                      ${isCompleted || isActive 
                        ? 'bg-primary-600' 
                        : 'bg-gray-300 dark:bg-gray-600'
                      }
                    `} />
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Tab Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {activeTab === 'progress' && (
            <ProgressCompletionTab
              config={config.progressCompletion}
              onChange={(updates) => updateConfig('progressCompletion', updates)}
            />
          )}
          {activeTab === 'preferences' && (
            <LearnerPreferencesTab
              config={config.learnerPreferences}
              onChange={(updates) => updateConfig('learnerPreferences', updates)}
            />
          )}
          {activeTab === 'player' && (
            <PlayerStyleTab
              config={config.playerStyle}
              onChange={(updates) => updateConfig('playerStyle', updates)}
            />
          )}
        </div>
      </div>

      <LivePreview config={config} />
    </div>
  );
}

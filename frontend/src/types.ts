export interface UploadedFile {
  id: string;
  file: File;
  type: 'sco' | 'resource';
  isLaunchFile: boolean;
  size: number;
  selectedPages?: number[]; // Для PDF: выбранные страницы (1-based, если undefined - все страницы)
}

export interface ProgressCompletionConfig {
  rememberLastPage: boolean;
  saveOnEachTransition: boolean;
  askOnReentry: boolean;
  progressMethod: 'screens' | 'tasks' | 'combined';
  completionThreshold: number;
  successCriterion: 'score' | 'tasks' | 'none';
}

export interface LearnerPreferencesConfig {
  defaultVolume: number;
  defaultLanguage: string;
  deliverySpeed: number;
  alwaysSubtitles: boolean;
  rememberPreferences: boolean;
}

export interface PlayerStyleConfig {
  theme: 'light' | 'dark' | 'auto';
  primaryColor: string;
  accentColor: string;
  tocLayout: 'sidebar' | 'tabs' | 'overlay';
  progressIndicator: 'linear' | 'steps' | 'percentage';
  highContrast: boolean;
  largeFont: boolean;
  transitionType: 'none' | 'fade' | 'slide';
  reduceAnimations: boolean;
}

export interface SCORMConfig {
  title?: string;
  progressCompletion: ProgressCompletionConfig;
  learnerPreferences: LearnerPreferencesConfig;
  playerStyle: PlayerStyleConfig;
}

export type Theme = 'light' | 'dark';


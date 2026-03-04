import { SCORMConfig } from '../types';

export const defaultConfig: SCORMConfig = {
  progressCompletion: {
    rememberLastPage: true,
    saveOnEachTransition: true,
    askOnReentry: false,
    progressMethod: 'screens',
    completionThreshold: 80,
    successCriterion: 'score',
  },
  learnerPreferences: {
    defaultVolume: 75,
    defaultLanguage: 'ru',
    deliverySpeed: 50,
    alwaysSubtitles: false,
    rememberPreferences: true,
  },
  playerStyle: {
    theme: 'auto',
    primaryColor: '#0ea5e9',
    accentColor: '#8b5cf6',
    tocLayout: 'sidebar',
    progressIndicator: 'linear',
    highContrast: false,
    largeFont: false,
    transitionType: 'fade',
    reduceAnimations: false,
  },
};


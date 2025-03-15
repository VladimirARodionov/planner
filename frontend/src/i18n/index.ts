import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

import ruTranslation from './locales/ru.json';
import enTranslation from './locales/en.json';

// Ресурсы переводов
export const resources = {
  ru: {
    translation: ruTranslation
  },
  en: {
    translation: enTranslation
  }
};

// Принудительно приводим тип, чтобы обойти проблемы TypeScript
(i18n as any)
  // Определение языка браузера
  .use(LanguageDetector)
  // Интеграция с React
  .use(initReactI18next)
  // Инициализация i18next
  .init({
    resources,
    fallbackLng: 'ru', // Язык по умолчанию
    interpolation: {
      escapeValue: false // React уже защищает от XSS
    },
    detection: {
      order: ['localStorage', 'navigator'],
      caches: ['localStorage']
    }
  });

export default i18n; 
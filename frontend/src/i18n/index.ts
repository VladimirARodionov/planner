import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';
import { AuthAPI } from '../api/auth';

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

// Функция для загрузки языка пользователя после инициализации i18n
export const loadUserLanguage = async () => {
  try {
    // Проверяем, авторизован ли пользователь
    const token = localStorage.getItem('token');
    if (token) {
      // Получаем язык пользователя с сервера
      const language = await AuthAPI.getUserLanguage();
      if (language && language !== (i18n as any).language) {
        // Меняем язык в i18n, если он отличается от текущего
        await (i18n as any).changeLanguage(language);
      }
    }
  } catch (error) {
    console.error('Error loading user language:', error);
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

// Пытаемся загрузить язык пользователя после инициализации
loadUserLanguage();

export default i18n; 
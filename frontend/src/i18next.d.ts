import 'react-i18next';
import 'i18next';

// Расширяем интерфейс i18n
declare module 'i18next' {
  interface i18n {
    use(plugin: any): i18n;
    changeLanguage(lng?: string): Promise<TFunction>;
    language: string;
    languages: string[];
    resolvedLanguage: string;
  }
  
  // Расширяем сам i18next, чтобы у него был метод use
  interface i18nextStatic {
    use(plugin: any): i18nextStatic;
  }
}

// Расширяем интерфейс ресурсов i18next
declare module 'i18next' {
  interface CustomTypeOptions {
    defaultNS: 'translation';
    resources: {
      translation: {
        [key: string]: any;
      }
    };
  }
} 
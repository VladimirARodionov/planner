import 'i18next';

// расширяем определение i18n
declare module 'i18next' {
  interface i18n {
    changeLanguage(lng?: string): Promise<Function>;
    language: string;
    languages: string[];
    resolvedLanguage: string;
  }
  
  // добавляем методы к статическому объекту i18next
  export interface i18next {
    use(plugin: any): i18next;
  }
} 
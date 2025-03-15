/// <reference types="react-scripts" />

import 'i18next';

declare module 'i18next' {
  export interface i18n {
    changeLanguage(lng?: string): Promise<Function>;
    language: string;
    languages: string[];
    resolvedLanguage: string;
  }
}

declare module '*.json' {
  const value: any;
  export default value;
} 
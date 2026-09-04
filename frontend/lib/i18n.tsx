"""Simple i18n provider for Aarogya (M17)."""

import React, { createContext, useContext, useState } from "react";

type Locale = "en" | "hi";

type Translations = Record<Locale, Record<string, string>>;

const translations: Translations = {
  en: {
    "app.title": "Aarogya",
    "app.tagline": "Your family's health records, understood",
    "nav.home": "Home",
    "nav.dashboard": "Dashboard",
    "nav.members": "Members",
    "nav.appointments": "Appointments",
    "nav.vitals": "Vitals",
    "nav.nutrition": "Nutrition",
    "nav.workout": "Workout",
    "nav.settings": "Settings",
    "common.save": "Save",
    "common.cancel": "Cancel",
    "common.loading": "Loading...",
    "common.error": "Something went wrong",
    "voice.start": "Start voice input",
    "voice.stop": "Stop voice input",
    "voice.transcript": "Transcript",
    "voice.fallback": "Voice unavailable. Please type instead.",
  },
  hi: {
    "app.title": "आरोग्य",
    "app.tagline": "आपके परिवार के स्वास्थ्य रिकॉर्ड, समझे हुए",
    "nav.home": "होम",
    "nav.dashboard": "डैशबोर्ड",
    "nav.members": "सदस्य",
    "nav.appointments": "अपॉइंटमेंट",
    "nav.vitals": "वाइटल",
    "nav.nutrition": "पोषण",
    "nav.workout": "वर्कआउट",
    "nav.settings": "सेटिंग्स",
    "common.save": "सहेजें",
    "common.cancel": "रद्द करें",
    "common.loading": "लोड हो रहा है...",
    "common.error": "कुछ गलत हो गया",
    "voice.start": "वॉयस इनपुट शुरू करें",
    "voice.stop": "वॉयस इनपुट बंद करें",
    "voice.transcript": "ट्रांसक्रिप्ट",
    "voice.fallback": "वॉयस उपलब्ध नहीं है। कृपया टाइप करें।",
  },
};

type I18nContextType = {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: (key: string) => string;
};

const I18nContext = createContext<I18nContextType | undefined>(undefined);

export function I18nProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocale] = useState<Locale>("en");

  const t = (key: string): string => {
    return translations[locale][key] || key;
  };

  return (
    <I18nContext.Provider value={{ locale, setLocale, t }}>
      {children}
    </I18nContext.Provider>
  );
}

export function useI18n() {
  const context = useContext(I18nContext);
  if (!context) {
    throw new Error("useI18n must be used within I18nProvider");
  }
  return context;
}

"""Voice input component (M17).

Wraps the Web Speech API with a transcript fallback for unsupported
browsers or when the user denies microphone permission.
"""

"use client";

import { useCallback, useEffect, useState } from "react";
import { useI18n } from "@/lib/i18n";

type VoiceInputProps = {
  onTranscript: (text: string) => void;
  placeholder?: string;
};

export function VoiceInput({ onTranscript, placeholder }: VoiceInputProps) {
  const { t } = useI18n();
  const [isListening, setIsListening] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [transcript, setTranscript] = useState("");

  const startListening = useCallback(() => {
    if (!("webkitSpeechRecognition" in window) && !("SpeechRecognition" in window)) {
      setError(t("voice.fallback"));
      return;
    }

    const SpeechRecognition = (window as unknown as { SpeechRecognition: unknown; webkitSpeechRecognition: unknown }).SpeechRecognition
      || (window as unknown as { webkitSpeechRecognition: unknown }).webkitSpeechRecognition;

    const recognition = new SpeechRecognition() as unknown as {
      lang: string;
      continuous: boolean;
      interimResults: boolean;
      onresult: (event: { results: { [key: number]: { [key: number]: { transcript: string } } }) => void;
      onerror: () => void;
      onend: () => void;
    };

    recognition.lang = "en-IN";
    recognition.continuous = false;
    recognition.interimResults = true;

    recognition.onresult = (event: { results: { [key: number]: { [key: number]: { transcript: string } } }) => {
      const result = event.results[0][0].transcript;
      setTranscript(result);
      onTranscript(result);
    };

    recognition.onerror = () => {
      setError(t("voice.fallback"));
      setIsListening(false);
    };

    recognition.onend = () => {
      setIsListening(false);
    };

    recognition.start();
    setIsListening(true);
    setError(null);
  }, [onTranscript, t]);

  const stopListening = useCallback(() => {
    setIsListening(false);
  }, []);

  useEffect(() => {
    if (!isListening) return;
    return stopListening;
  }, [isListening, stopListening]);

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={isListening ? stopListening : startListening}
          className="rounded-full bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
        >
          {isListening ? t("voice.stop") : t("voice.start")}
        </button>
        {isListening && (
          <span className="inline-flex h-2 w-2 animate-pulse rounded-full bg-red-500" />
        )}
      </div>
      {error && <p className="text-sm text-red-500">{error}</p>}
      {transcript && (
        <p className="text-sm text-muted-foreground">
          {t("voice.transcript")}: {transcript}
        </p>
      )}
    </div>
  );
}

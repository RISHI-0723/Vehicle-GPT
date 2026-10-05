// Browser-only speech-to-text via window.SpeechRecognition / webkitSpeechRecognition.
// No Whisper, no cloud STT, no server-side audio transcription -- if the
// browser doesn't expose this API, voice input is simply unavailable.
import { useCallback, useEffect, useRef, useState } from "react";

export type VoiceState = "IDLE" | "LISTENING" | "PROCESSING" | "RESULT" | "ERROR" | "UNAVAILABLE";

export const VOICE_UNAVAILABLE_COPY = "Voice input isn't available here. You can type your question instead.";
const PERMISSION_DENIED_COPY = "Microphone access was denied. You can type your question instead.";
const GENERIC_ERROR_COPY = "Voice input failed. Please try again or type your question.";

interface SpeechRecognitionResultLike {
  [index: number]: { transcript: string };
  isFinal: boolean;
}

interface SpeechRecognitionEventLike extends Event {
  results: ArrayLike<SpeechRecognitionResultLike>;
}

interface SpeechRecognitionErrorEventLike extends Event {
  error: string;
}

export interface SpeechRecognitionLike extends EventTarget {
  lang: string;
  interimResults: boolean;
  continuous: boolean;
  start: () => void;
  stop: () => void;
  onresult: ((event: SpeechRecognitionEventLike) => void) | null;
  onerror: ((event: SpeechRecognitionErrorEventLike) => void) | null;
  onend: (() => void) | null;
}

type SpeechRecognitionCtor = new () => SpeechRecognitionLike;

function getSpeechRecognitionCtor(): SpeechRecognitionCtor | null {
  if (typeof window === "undefined") return null;
  const w = window as unknown as {
    SpeechRecognition?: SpeechRecognitionCtor;
    webkitSpeechRecognition?: SpeechRecognitionCtor;
  };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}

export interface VoiceRecognition {
  state: VoiceState;
  transcript: string;
  errorMessage: string | null;
  start: () => void;
  stop: () => void;
  reset: () => void;
}

export function useSpeechRecognition(): VoiceRecognition {
  const ctorRef = useRef<SpeechRecognitionCtor | null>(getSpeechRecognitionCtor());
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);
  const [state, setState] = useState<VoiceState>(() => (getSpeechRecognitionCtor() ? "IDLE" : "UNAVAILABLE"));
  const [transcript, setTranscript] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    return () => {
      recognitionRef.current?.stop();
    };
  }, []);

  const start = useCallback(() => {
    const Ctor = ctorRef.current;
    if (!Ctor) {
      setState("UNAVAILABLE");
      return;
    }
    setErrorMessage(null);
    setTranscript("");

    const recognition = new Ctor();
    recognition.lang = "en-IN";
    recognition.interimResults = false;
    recognition.continuous = false;

    recognition.onresult = (event) => {
      setState("PROCESSING");
      const last = event.results[event.results.length - 1];
      const text = last?.[0]?.transcript ?? "";
      setTranscript(text);
      setState("RESULT");
    };
    recognition.onerror = (event) => {
      setErrorMessage(
        event.error === "not-allowed" || event.error === "permission-denied"
          ? PERMISSION_DENIED_COPY
          : GENERIC_ERROR_COPY,
      );
      setState("ERROR");
    };
    recognition.onend = () => {
      setState((current) => (current === "LISTENING" ? "IDLE" : current));
    };

    recognitionRef.current = recognition;
    setState("LISTENING");
    recognition.start();
  }, []);

  const stop = useCallback(() => {
    recognitionRef.current?.stop();
  }, []);

  const reset = useCallback(() => {
    setState(ctorRef.current ? "IDLE" : "UNAVAILABLE");
    setTranscript("");
    setErrorMessage(null);
  }, []);

  return { state, transcript, errorMessage, start, stop, reset };
}

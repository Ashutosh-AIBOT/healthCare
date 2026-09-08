"use client";

import React, { useEffect, useRef, useState, useCallback } from "react";
import { Mic, MicOff, PhoneOff, Volume2, Sparkles, Loader2, Activity, Radio, AlertCircle } from "lucide-react";
import { apiClient, getAccessToken } from "@/lib/auth-client";
import { cn } from "@/lib/utils";

interface LiveKitVoiceModalProps {
  isOpen: boolean;
  onClose: () => void;
  conversationId: string | null;
  mode: string;
  onMessageAdded: (msg: { role: "user" | "assistant"; content: string; action?: any }) => void;
  onConversationCreated?: (id: string) => void;
}

type VoiceStatus = "connecting" | "listening" | "processing" | "speaking" | "idle" | "error";

export function LiveKitVoiceModal({
  isOpen,
  onClose,
  conversationId,
  mode,
  onMessageAdded,
  onConversationCreated,
}: LiveKitVoiceModalProps) {
  const [status, setStatus] = useState<VoiceStatus>("connecting");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isMuted, setIsMuted] = useState(false);
  const [transcript, setTranscript] = useState<string>("");
  const [assistantReply, setAssistantReply] = useState<string>("");
  const [roomInfo, setRoomInfo] = useState<{ roomName: string; identity: string } | null>(null);
  const [volumeLevel, setVolumeLevel] = useState<number>(0);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const animFrameRef = useRef<number | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const synthRef = useRef<SpeechSynthesis | null>(null);
  const activeConvIdRef = useRef<string | null>(conversationId);

  useEffect(() => {
    activeConvIdRef.current = conversationId;
  }, [conversationId]);

  // Audio level meter
  const startVolumeMeter = (stream: MediaStream) => {
    try {
      const audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)();
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 64;
      const source = audioCtx.createMediaStreamSource(stream);
      source.connect(analyser);

      audioCtxRef.current = audioCtx;
      analyserRef.current = analyser;

      const dataArray = new Uint8Array(analyser.frequencyBinCount);
      const updateVolume = () => {
        if (!analyserRef.current) return;
        analyserRef.current.getByteFrequencyData(dataArray);
        let sum = 0;
        for (let i = 0; i < dataArray.length; i++) {
          sum += dataArray[i];
        }
        const avg = sum / dataArray.length;
        setVolumeLevel(Math.min(100, Math.round((avg / 128) * 100)));
        animFrameRef.current = requestAnimationFrame(updateVolume);
      };
      updateVolume();
    } catch {
      // AudioContext may be blocked before gesture
    }
  };

  const stopVolumeMeter = () => {
    if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    if (audioCtxRef.current && audioCtxRef.current.state !== "closed") {
      void audioCtxRef.current.close();
    }
    analyserRef.current = null;
    audioCtxRef.current = null;
    setVolumeLevel(0);
  };

  // Connect to LiveKit session
  const initVoiceSession = useCallback(async () => {
    setStatus("connecting");
    setErrorMessage(null);

    try {
      // 1. Fetch LiveKit Token from backend
      const res = await apiClient<{
        token: string;
        room_name: string;
        livekit_url: string;
        participant_identity: string;
      }>("/api/v1/xomni/voice/livekit-token", {
        method: "POST",
        body: JSON.stringify({
          conversation_id: activeConvIdRef.current,
        }),
      });

      if (res.error || !res.data) {
        throw new Error(res.error?.detail || "Could not allocate voice session room.");
      }

      setRoomInfo({
        roomName: res.data.room_name,
        identity: res.data.participant_identity,
      });

      // 2. Request user microphone
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });

      startVolumeMeter(stream);

      // 3. Setup recorder for voice turns
      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : "audio/webm";

      const recorder = new MediaRecorder(stream, { mimeType });
      mediaRecorderRef.current = recorder;
      audioChunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunksRef.current.push(e.data);
      };

      recorder.onstop = async () => {
        if (audioChunksRef.current.length === 0) {
          setStatus("listening");
          return;
        }

        setStatus("processing");
        const audioBlob = new Blob(audioChunksRef.current, { type: mimeType });
        audioChunksRef.current = [];

        try {
          const formData = new FormData();
          formData.append("audio", audioBlob, "voice.webm");
          const token = getAccessToken();

          // STT
          const sttRes = await fetch("/api/v1/xomni/voice/transcribe", {
            method: "POST",
            headers: token ? { Authorization: `Bearer ${token}` } : {},
            credentials: "include",
            body: formData,
          });

          if (!sttRes.ok) {
            throw new Error("Could not transcribe speech");
          }

          const sttData = await sttRes.json();
          const userText = sttData.transcript?.trim();

          if (!userText) {
            setStatus("listening");
            return;
          }

          setTranscript(userText);
          onMessageAdded({ role: "user", content: userText });

          // Send message to shared conversation
          const chatRes = await fetch("/api/v1/xomni/chat", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              ...(token ? { Authorization: `Bearer ${token}` } : {}),
            },
            credentials: "include",
            body: JSON.stringify({
              message: userText,
              mode,
              conversation_id: activeConvIdRef.current,
              stream: false,
            }),
          });

          if (!chatRes.ok) {
            throw new Error("Failed to get agent response");
          }

          const chatData = await chatRes.json();
          const replyText = chatData.answer || "I hear you. Let me check that.";
          setAssistantReply(replyText);

          if (chatData.conversation_id && chatData.conversation_id !== activeConvIdRef.current) {
            activeConvIdRef.current = chatData.conversation_id;
            if (onConversationCreated) onConversationCreated(chatData.conversation_id);
          }

          onMessageAdded({
            role: "assistant",
            content: replyText,
            action: chatData.action,
          });

          // Speak reply via TTS
          speakReply(replyText);
        } catch (err: any) {
          setErrorMessage(err.message || "Voice processing issue.");
          setStatus("listening");
        }
      };

      recorder.start();
      setStatus("listening");
    } catch (err: any) {
      setStatus("error");
      setErrorMessage(err.message || "Failed to initialize microphone or LiveKit voice session.");
    }
  }, [mode, onMessageAdded, onConversationCreated]);

  const speakReply = (text: string) => {
    if (typeof window === "undefined" || !("speechSynthesis" in window)) {
      setStatus("listening");
      return;
    }
    window.speechSynthesis.cancel();

    // Clean markdown before speaking
    const cleanText = text
      .replace(/[#*_`~[\]()]/g, "")
      .replace(/\{.*?\}/g, "")
      .trim();

    const utterance = new SpeechSynthesisUtterance(cleanText);
    utterance.rate = 1.05;
    utterance.pitch = 1.0;

    const voices = window.speechSynthesis.getVoices();
    const naturalVoice = voices.find(v => v.lang.startsWith("en") && (v.name.includes("Natural") || v.name.includes("Google") || v.name.includes("Samantha")));
    if (naturalVoice) utterance.voice = naturalVoice;

    utterance.onstart = () => setStatus("speaking");
    utterance.onend = () => {
      setStatus("listening");
      // Restart recorder for next user turn
      if (mediaRecorderRef.current && mediaRecorderRef.current.state === "inactive") {
        mediaRecorderRef.current.start();
      }
    };
    utterance.onerror = () => setStatus("listening");

    window.speechSynthesis.speak(utterance);
  };

  const handleFinishTurn = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
      mediaRecorderRef.current.stop();
    }
  };

  useEffect(() => {
    if (isOpen) {
      void initVoiceSession();
    } else {
      stopVolumeMeter();
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
        mediaRecorderRef.current.stop();
      }
      if (typeof window !== "undefined" && "speechSynthesis" in window) {
        window.speechSynthesis.cancel();
      }
    }
    return () => {
      stopVolumeMeter();
    };
  }, [isOpen, initVoiceSession]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-md p-4 animate-in fade-in duration-200">
      <div className="relative w-full max-w-lg overflow-hidden rounded-[2.5rem] border border-line/40 bg-surface/90 p-8 shadow-2xl backdrop-blur-xl">
        {/* Glow backdrop */}
        <div className="absolute -top-24 -left-24 h-64 w-64 rounded-full bg-primary/20 blur-3xl" />
        <div className="absolute -bottom-24 -right-24 h-64 w-64 rounded-full bg-primary/15 blur-3xl" />

        {/* Header */}
        <div className="relative flex items-center justify-between pb-6 border-b border-line/40">
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-2xl bg-primary text-primary-foreground shadow-md">
              <Radio className="h-4 w-4 animate-pulse" />
            </div>
            <div>
              <h3 className="font-display text-lg font-semibold text-ink">Xomni LiveKit Voice</h3>
              <p className="text-xs text-muted flex items-center gap-1.5">
                <span className="inline-block h-2 w-2 rounded-full bg-emerald-500 animate-ping" />
                WebRTC Room: {roomInfo?.roomName || "Connecting..."}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="flex h-8 w-8 items-center justify-center rounded-full border border-line text-muted hover:bg-mist hover:text-ink transition"
          >
            ✕
          </button>
        </div>

        {/* Dynamic Voice Visualizer Circle */}
        <div className="relative my-8 flex flex-col items-center justify-center">
          <div className="relative flex items-center justify-center">
            {/* Outer pulsating rings based on volume */}
            <div
              className={cn(
                "absolute rounded-full transition-all duration-100",
                status === "speaking" ? "bg-primary/20" : "bg-emerald-500/20"
              )}
              style={{
                width: `${120 + volumeLevel * 1.2}px`,
                height: `${120 + volumeLevel * 1.2}px`,
              }}
            />
            <div
              className={cn(
                "absolute rounded-full transition-all duration-150",
                status === "speaking" ? "bg-primary/30" : "bg-emerald-500/30"
              )}
              style={{
                width: `${100 + volumeLevel * 0.7}px`,
                height: `${100 + volumeLevel * 0.7}px`,
              }}
            />

            {/* Central glowing sphere */}
            <div
              className={cn(
                "relative flex h-24 w-24 items-center justify-center rounded-full shadow-lg transition-transform duration-200",
                status === "speaking"
                  ? "bg-gradient-to-tr from-primary to-primary-hover text-white scale-105"
                  : status === "listening"
                  ? "bg-gradient-to-tr from-emerald-500 to-teal-400 text-white"
                  : status === "processing"
                  ? "bg-gradient-to-tr from-amber-500 to-orange-400 text-white"
                  : "bg-surface border border-line text-muted"
              )}
            >
              {status === "processing" ? (
                <Loader2 className="h-8 w-8 animate-spin" />
              ) : status === "speaking" ? (
                <Volume2 className="h-8 w-8 animate-bounce" />
              ) : (
                <Mic className="h-8 w-8" />
              )}
            </div>
          </div>

          {/* Status badge */}
          <div className="mt-6 flex items-center gap-2">
            <span
              className={cn(
                "rounded-full px-3 py-1 text-xs font-semibold capitalize",
                status === "listening" && "bg-emerald-50 text-emerald-700 border border-emerald-200",
                status === "processing" && "bg-amber-50 text-amber-700 border border-amber-200",
                status === "speaking" && "bg-primary-soft text-primary border border-primary/20",
                status === "connecting" && "bg-mist text-muted border border-line",
                status === "error" && "bg-rose-50 text-rose-700 border border-rose-200"
              )}
            >
              {status === "listening" && "Listening to you..."}
              {status === "processing" && "RAG Reasoning & Formulating..."}
              {status === "speaking" && "Xomni is speaking..."}
              {status === "connecting" && "Connecting WebRTC room..."}
              {status === "error" && "Connection error"}
            </span>
          </div>

          {/* Real-time speech transcript & response display */}
          <div className="mt-5 w-full space-y-2 rounded-2xl bg-surface/60 border border-line/60 p-4 text-left min-h-[90px] max-h-[140px] overflow-y-auto">
            {transcript && (
              <p className="text-xs text-ink">
                <strong className="text-muted">You:</strong> {transcript}
              </p>
            )}
            {assistantReply && (
              <p className="text-xs text-primary font-medium">
                <strong className="text-primary-hover">Xomni:</strong> {assistantReply}
              </p>
            )}
            {!transcript && !assistantReply && (
              <p className="text-xs text-muted/70 italic text-center pt-5">
                Speak naturally. Xomni accesses your food preferences, health records, and schedule in real time.
              </p>
            )}
          </div>

          {errorMessage && (
            <div className="mt-3 flex items-center gap-2 text-xs text-rose-600">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{errorMessage}</span>
            </div>
          )}
        </div>

        {/* Action Controls */}
        <div className="relative flex items-center justify-center gap-4 pt-4 border-t border-line/40">
          {status === "listening" && (
            <button
              onClick={handleFinishTurn}
              className="flex items-center gap-2 rounded-full bg-primary px-5 py-2.5 text-xs font-semibold text-primary-foreground shadow-sm hover:bg-primary-hover transition"
            >
              <Sparkles className="h-3.5 w-3.5" />
              Done Speaking
            </button>
          )}

          <button
            onClick={() => {
              if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
                mediaRecorderRef.current.pause();
                setIsMuted(true);
              } else if (mediaRecorderRef.current && mediaRecorderRef.current.state === "paused") {
                mediaRecorderRef.current.resume();
                setIsMuted(false);
              }
            }}
            className="flex h-11 w-11 items-center justify-center rounded-full border border-line bg-surface text-ink hover:bg-mist transition"
            title={isMuted ? "Unmute" : "Mute"}
          >
            {isMuted ? <MicOff className="h-4 w-4 text-rose-500" /> : <Mic className="h-4 w-4" />}
          </button>

          <button
            onClick={onClose}
            className="flex items-center gap-2 rounded-full bg-rose-600 px-5 py-2.5 text-xs font-semibold text-white shadow-sm hover:bg-rose-700 transition"
          >
            <PhoneOff className="h-3.5 w-3.5" />
            End Voice Call
          </button>
        </div>
      </div>
    </div>
  );
}

"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { LiveKitRoom, RoomAudioRenderer, useRoomContext } from "@livekit/components-react";
import { RoomEvent } from "livekit-client";
import type { Participant, TrackPublication, TranscriptionSegment } from "livekit-client";
import { Mic, MicOff } from "lucide-react";
import { cn } from "@/lib/utils";
import { apiClient } from "@/lib/auth-client";

type VoiceRoomStatus = "idle" | "connecting" | "listening" | "thinking" | "speaking";

interface VoiceTalkButtonProps {
  onTranscript: (text: string) => void;
  onError: (message: string) => void;
  context?: string;
}

interface TokenResponse {
  token: string;
  livekit_url: string;
  room_name: string;
}

type TranscriptPayload = {
  text?: string;
  transcript?: string;
  message?: string;
  state?: string;
  type?: string;
};

function extractTranscriptText(raw: string): string | null {
  const trimmed = raw.trim();
  if (!trimmed) return null;
  try {
    const parsed = JSON.parse(trimmed) as TranscriptPayload;
    // Agent lifecycle messages (thinking/speaking flags) are state, not speech.
    if (typeof parsed.text === "string" && parsed.text.trim()) return parsed.text.trim();
    if (typeof parsed.transcript === "string" && parsed.transcript.trim())
      return parsed.transcript.trim();
    if (typeof parsed.message === "string" && parsed.message.trim() && parsed.type !== "state")
      return parsed.message.trim();
    return null;
  } catch {
    return trimmed;
  }
}

function VoiceRoomEvents({
  onTranscript,
  onError,
  onStatusChange,
  onRequestLeave,
}: {
  onTranscript: (text: string) => void;
  onError: (message: string) => void;
  onStatusChange: (status: VoiceRoomStatus) => void;
  onRequestLeave: () => void;
}) {
  const room = useRoomContext();
  const lastTranscriptRef = useRef<{ text: string; at: number }>({ text: "", at: 0 });
  const onTranscriptRef = useRef(onTranscript);
  const onErrorRef = useRef(onError);
  const onStatusChangeRef = useRef(onStatusChange);
  const onRequestLeaveRef = useRef(onRequestLeave);
  onTranscriptRef.current = onTranscript;
  onErrorRef.current = onError;
  onStatusChangeRef.current = onStatusChange;
  onRequestLeaveRef.current = onRequestLeave;

  const forwardTranscript = useCallback((text: string) => {
    const trimmed = text.trim();
    if (trimmed.length < 2) return;
    const now = Date.now();
    const last = lastTranscriptRef.current;
    if (last.text === trimmed && now - last.at < 2000) return;
    lastTranscriptRef.current = { text: trimmed, at: now };
    onTranscriptRef.current(trimmed);
  }, []);

  const deriveSpeakingStatus = useCallback(() => {
    const speakers = room.activeSpeakers;
    const remoteSpeaking = speakers.some((p: Participant) => !p.isLocal && p.isSpeaking);
    if (remoteSpeaking) {
      onStatusChangeRef.current("speaking");
      return;
    }
    const localSpeaking = speakers.some((p: Participant) => p.isLocal && p.isSpeaking);
    onStatusChangeRef.current(localSpeaking ? "thinking" : "listening");
  }, [room]);

  useEffect(() => {
    const handleData = (payload: Uint8Array) => {
      const text = extractTranscriptText(new TextDecoder().decode(payload));
      if (text) forwardTranscript(text);
    };
    const handleTranscription = (
      segments: TranscriptionSegment[],
      _participant?: Participant,
      _publication?: TrackPublication
    ) => {
      for (const seg of segments) {
        if (seg.final && seg.text.trim()) forwardTranscript(seg.text);
      }
    };
    const handleSpeakers = () => deriveSpeakingStatus();

    room.on(RoomEvent.DataReceived, handleData);
    room.on(RoomEvent.TranscriptionReceived, handleTranscription);
    room.on(RoomEvent.ActiveSpeakersChanged, handleSpeakers);
    room.on(RoomEvent.ParticipantConnected, handleSpeakers);
    room.on(RoomEvent.ParticipantDisconnected, handleSpeakers);
    room.on(RoomEvent.TrackSubscribed, handleSpeakers);
    return () => {
      room.off(RoomEvent.DataReceived, handleData);
      room.off(RoomEvent.TranscriptionReceived, handleTranscription);
      room.off(RoomEvent.ActiveSpeakersChanged, handleSpeakers);
      room.off(RoomEvent.ParticipantConnected, handleSpeakers);
      room.off(RoomEvent.ParticipantDisconnected, handleSpeakers);
      room.off(RoomEvent.TrackSubscribed, handleSpeakers);
    };
  }, [room, forwardTranscript, deriveSpeakingStatus]);

  // Worker-offline: room stayed empty (no agent joined) 15s after connect.
  useEffect(() => {
    const timer = window.setTimeout(() => {
      if (room.remoteParticipants.size === 0) {
        onErrorRef.current("Voice worker offline. Please try again later.");
        onRequestLeaveRef.current();
      }
    }, 15000);
    const cancelEarly = () => window.clearTimeout(timer);
    room.on(RoomEvent.ParticipantConnected, cancelEarly);
    room.once(RoomEvent.Disconnected, cancelEarly);
    return () => {
      window.clearTimeout(timer);
      room.off(RoomEvent.ParticipantConnected, cancelEarly);
    };
  }, [room]);

  return null;
}

export function VoiceTalkButton({ onTranscript, onError, context = "general" }: VoiceTalkButtonProps) {
  const [status, setStatus] = useState<VoiceRoomStatus>("idle");
  const [token, setToken] = useState<string | null>(null);
  const [serverUrl, setServerUrl] = useState<string | null>(null);
  const startingRef = useRef(false);

  const leave = useCallback(() => {
    setToken(null);
    setServerUrl(null);
    setStatus("idle");
    startingRef.current = false;
  }, []);

  const start = useCallback(async () => {
    if (startingRef.current || status !== "idle") return;
    startingRef.current = true;
    setStatus("connecting");

    // Early mic-permission check so denial surfaces with the page's voice copy.
    try {
      const probe = await navigator.mediaDevices.getUserMedia({ audio: true });
      probe.getTracks().forEach((t) => t.stop());
    } catch {
      onError("Microphone access denied. Please allow microphone permissions.");
      setStatus("idle");
      startingRef.current = false;
      return;
    }

    const { data, error } = await apiClient<TokenResponse>("/api/v1/xomni/voice/livekit-token", {
      method: "POST",
      body: JSON.stringify({ context }),
    });
    if (error || !data?.token || !data?.livekit_url) {
      onError("Could not start voice session. Please try again.");
      setStatus("idle");
      startingRef.current = false;
      return;
    }
    setToken(data.token);
    setServerUrl(data.livekit_url);
    setStatus("listening");
  }, [context, onError, status]);

  const toggle = useCallback(() => {
    if (status === "idle") {
      void start();
    } else {
      leave();
    }
  }, [status, start, leave]);

  const active = status !== "idle";

  return (
    <>
      <button
        type="button"
        onClick={toggle}
        aria-label={active ? `Leave voice room (${status})` : "Join voice room"}
        aria-pressed={active}
        title={active ? `Voice room: ${status} — tap to leave` : "Talk live (voice room)"}
        className={cn(
          "h-10 w-10 shrink-0 rounded-full flex items-center justify-center transition-all relative",
          status === "idle" && "bg-primary/10 text-primary hover:bg-primary/20",
          status === "connecting" && "bg-amber-500 text-white animate-pulse",
          status === "listening" &&
            "bg-rose-500 text-white shadow-[0_0_15px_rgba(244,63,94,0.4)] animate-pulse",
          status === "thinking" && "bg-amber-500 text-white animate-pulse",
          status === "speaking" && "bg-primary text-white shadow-sm"
        )}
      >
        {status === "connecting" || status === "thinking" ? (
          <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
        ) : active ? (
          <MicOff className="h-4 w-4" />
        ) : (
          <Mic className="h-4 w-4" />
        )}
        {status === "speaking" && (
          <span className="absolute -top-0.5 -right-0.5 flex h-3 w-3">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-white opacity-75" />
            <span className="relative inline-flex rounded-full h-3 w-3 bg-white" />
          </span>
        )}
      </button>

      {token && serverUrl && (
        <LiveKitRoom
          token={token}
          serverUrl={serverUrl}
          connect
          audio
          video={false}
          onConnected={() => setStatus("listening")}
          onDisconnected={leave}
          onError={() => {
            onError("Voice connection failed. Please try again.");
            leave();
          }}
        >
          <RoomAudioRenderer />
          <VoiceRoomEvents
            onTranscript={onTranscript}
            onError={onError}
            onStatusChange={setStatus}
            onRequestLeave={leave}
          />
        </LiveKitRoom>
      )}
    </>
  );
}

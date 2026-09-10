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
  onActiveChange?: (active: boolean) => void;
  /** Soft cap per call (free-tier inference budget). 0 = no cap. */
  maxMinutes?: number;
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

export function VoiceTalkButton({ onTranscript, onError, context = "general", onActiveChange, maxMinutes = 10 }: VoiceTalkButtonProps) {
  const [status, setStatus] = useState<VoiceRoomStatus>("idle");
  const [token, setToken] = useState<string | null>(null);
  const [serverUrl, setServerUrl] = useState<string | null>(null);
  const [roomName, setRoomName] = useState<string | null>(null);
  const startingRef = useRef(false);
  const capTimerRef = useRef<number | null>(null);

  const clearCapTimer = useCallback(() => {
    if (capTimerRef.current !== null) {
      window.clearTimeout(capTimerRef.current);
      capTimerRef.current = null;
    }
  }, []);

  const leave = useCallback(() => {
    clearCapTimer();
    // Best-effort slot release so the next caller is not blocked.
    // The 12-minute server TTL covers missed hangups.
    const room = roomName;
    if (room) {
      void apiClient("/api/v1/xomni/voice/hangup", {
        method: "DELETE",
        body: JSON.stringify({ room_name: room }),
      }).catch(() => undefined);
    }
    setToken(null);
    setServerUrl(null);
    setRoomName(null);
    setStatus("idle");
    startingRef.current = false;
    onActiveChange?.(false);
  }, [clearCapTimer, onActiveChange, roomName]);

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
      if (error?.status === 409) {
        onError("Someone is on a live voice call right now. Please try again in a few minutes.");
      } else {
        onError("Could not start voice session. Please try again.");
      }
      setStatus("idle");
      startingRef.current = false;
      return;
    }
    setToken(data.token);
    setServerUrl(data.livekit_url);
    setRoomName(data.room_name ?? null);
    setStatus("listening");
    onActiveChange?.(true);
    // Free-tier guard: end the call at the cap so one session cannot burn
    // the monthly inference budget. 0 disables.
    clearCapTimer();
    if (maxMinutes > 0) {
      capTimerRef.current = window.setTimeout(() => {
        onError("Voice session ended at the 10-minute free-tier limit. Rejoin to continue.");
        leave();
      }, maxMinutes * 60 * 1000);
    }
  }, [context, onActiveChange, onError, status, maxMinutes, clearCapTimer, leave]);

  const toggle = useCallback(() => {
    if (status === "idle") {
      void start();
    } else {
      leave();
    }
  }, [status, start, leave]);

  const active = status !== "idle";

  useEffect(() => clearCapTimer, [clearCapTimer]);

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
          status === "connecting" && "bg-accent-water text-primary-foreground animate-pulse",
          status === "listening" &&
            "bg-accent-water text-primary-foreground animate-pulse",
          status === "thinking" && "bg-accent-water text-primary-foreground animate-pulse",
          status === "speaking" && "bg-primary text-primary-foreground shadow-sm"
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
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary-foreground opacity-75" />
            <span className="relative inline-flex rounded-full h-3 w-3 bg-primary-foreground" />
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

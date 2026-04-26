"use client";

import { useCallback, useState } from "react";
import {
  LiveKitRoom,
  RoomAudioRenderer,
  StartAudio,
  useVoiceAssistant,
  BarVisualizer,
  VoiceAssistantControlBar,
} from "@livekit/components-react";
import "@livekit/components-styles";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Mic, PhoneOff, Loader2, Volume2 } from "lucide-react";

type ConnectionState = "idle" | "connecting" | "connected";

interface TokenData {
  token: string;
  url: string;
  room: string;
}

export function VoiceAgent() {
  const [state, setState] = useState<ConnectionState>("idle");
  const [tokenData, setTokenData] = useState<TokenData | null>(null);

  const connect = useCallback(async () => {
    setState("connecting");
    try {
      const res = await fetch("/api/token");
      if (!res.ok) throw new Error("Failed to get token");
      const data: TokenData = await res.json();
      setTokenData(data);
      setState("connected");
    } catch {
      setState("idle");
      alert(
        "Could not connect. Check your .env.local and make sure the agent is running."
      );
    }
  }, []);

  const disconnect = useCallback(() => {
    setState("idle");
    setTokenData(null);
  }, []);

  if (state === "idle") {
    return (
      <div className="flex flex-col items-center gap-6">
        <div className="text-center space-y-2">
          <h2 className="text-2xl font-semibold tracking-tight">Voice Assistant</h2>
          <p className="text-muted-foreground text-sm">
            Click below to start a conversation with your AI agent
          </p>
        </div>
        <Button size="lg" className="gap-2 px-8 rounded-full" onClick={connect}>
          <Mic className="h-5 w-5" />
          Start Conversation
        </Button>
      </div>
    );
  }

  if (state === "connecting") {
    return (
      <div className="flex flex-col items-center gap-4">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        <p className="text-sm text-muted-foreground">Connecting…</p>
      </div>
    );
  }

  return (
    <LiveKitRoom
      token={tokenData!.token}
      serverUrl={tokenData!.url}
      connect
      audio
      video={false}
      onDisconnected={disconnect}
      className="w-full"
    >
      {/* Renders all remote audio tracks (agent voice) */}
      <RoomAudioRenderer />

      {/*
        Required: browsers block audio autoplay until a user gesture.
        StartAudio renders a visible button ONLY when audio is blocked —
        the user clicks it once and agent audio starts playing.
      */}
      <StartAudio
        label="Click to enable agent audio"
        className="flex items-center gap-2 mx-auto px-4 py-2 rounded-full bg-amber-100 text-amber-800 text-sm font-medium border border-amber-300 hover:bg-amber-200 transition-colors"
      />

      <AgentView onDisconnect={disconnect} />
    </LiveKitRoom>
  );
}

function AgentView({ onDisconnect }: { onDisconnect: () => void }) {
  const { state, audioTrack, agentTranscriptions } = useVoiceAssistant();

  const statusLabel: Record<string, string> = {
    disconnected: "Waiting for agent…",
    connecting: "Connecting",
    initializing: "Initializing",
    listening: "Listening",
    thinking: "Thinking",
    speaking: "Speaking",
  };

  const statusColor: Record<string, string> = {
    listening: "bg-green-500",
    thinking: "bg-yellow-500",
    speaking: "bg-blue-500",
    initializing: "bg-purple-500",
  };

  // Last few transcription segments from the agent
  const recentTranscriptions = agentTranscriptions.slice(-4);

  return (
    <div className="flex flex-col items-center gap-6 w-full">
      <div className="flex items-center gap-2 mt-2">
        <span
          className={`inline-block h-2.5 w-2.5 rounded-full ${statusColor[state] ?? "bg-zinc-400"}`}
        />
        <Badge variant="secondary" className="font-medium text-sm">
          {statusLabel[state] ?? state}
        </Badge>
      </div>

      <Card className="w-full">
        <CardContent className="pt-6 pb-6 flex items-center justify-center">
          <BarVisualizer
            state={state}
            trackRef={audioTrack}
            barCount={24}
            style={{ width: "100%", height: "80px" }}
          />
        </CardContent>
      </Card>

      {recentTranscriptions.length > 0 && (
        <div className="w-full rounded-lg border bg-muted/40 px-4 py-3 space-y-1">
          {recentTranscriptions.map((seg) => (
            <p key={seg.id} className="text-sm text-foreground/80 leading-snug">
              {seg.text}
            </p>
          ))}
        </div>
      )}

      <VoiceAssistantControlBar />

      <Button
        variant="destructive"
        size="sm"
        className="gap-2 rounded-full"
        onClick={onDisconnect}
      >
        <PhoneOff className="h-4 w-4" />
        End Call
      </Button>
    </div>
  );
}

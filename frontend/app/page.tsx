import { VoiceAgent } from "@/components/VoiceAgent";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8 bg-background">
      <div className="w-full max-w-md">
        <div className="mb-10 text-center">
          <h1 className="text-3xl font-bold tracking-tight">LiveKit Voice Agent</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Powered by OpenAI · Deepgram · Cartesia
          </p>
        </div>
        <VoiceAgent />
      </div>
    </main>
  );
}

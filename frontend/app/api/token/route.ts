import { AccessToken, AgentDispatchClient } from "livekit-server-sdk";
import { NextRequest, NextResponse } from "next/server";

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const roomName = searchParams.get("room") ?? `voice-room-${Date.now()}`;
  const participantName = searchParams.get("username") ?? `user-${Math.random().toString(36).slice(2, 7)}`;

  const apiKey = process.env.LIVEKIT_API_KEY;
  const apiSecret = process.env.LIVEKIT_API_SECRET;
  const livekitUrl = process.env.LIVEKIT_URL;

  if (!apiKey || !apiSecret || !livekitUrl) {
    return NextResponse.json(
      { error: "Server misconfigured: missing LiveKit env vars" },
      { status: 500 }
    );
  }

  const at = new AccessToken(apiKey, apiSecret, {
    identity: participantName,
    ttl: "1h",
  });

  at.addGrant({
    roomJoin: true,
    room: roomName,
    canPublish: true,
    canSubscribe: true,
  });

  const token = await at.toJwt();

  // Dispatch the agent to the room. AgentDispatchClient requires https:// not wss://
  const httpUrl = livekitUrl.replace(/^wss?:\/\//, "https://");
  const dispatchClient = new AgentDispatchClient(httpUrl, apiKey, apiSecret);
  await dispatchClient.createDispatch(roomName, "my-agent");

  return NextResponse.json({ token, url: livekitUrl, room: roomName });
}

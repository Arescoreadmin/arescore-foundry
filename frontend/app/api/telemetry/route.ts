import { NextResponse } from "next/server";
import { buildMockTelemetry } from "@/lib/telemetry";

export const runtime = "edge";

export async function GET() {
  const stream = new ReadableStream({
    start(controller) {
      const encoder = new TextEncoder();
      const interval = setInterval(() => {
        const frame = buildMockTelemetry();
        controller.enqueue(encoder.encode(`data: ${JSON.stringify(frame)}\n\n`));
      }, 3000);

      controller.enqueue(encoder.encode(`event: frostgate\n`));

      const close = () => {
        clearInterval(interval);
        controller.close();
      };

      controller.enqueue(encoder.encode("retry: 5000\n"));

      // close after 1 minute to avoid runaway streams
      setTimeout(close, 60_000);
    },
  });

  return new NextResponse(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
    },
  });
}

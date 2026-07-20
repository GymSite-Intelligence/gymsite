interface Env {
  WEBHOOK_EVENTS: KVNamespace;
  WEBHOOK_SECRET: string;
  FORWARD_URL?: string;
}

interface StoredWebhookEvent {
  id: string;
  receivedAt: string;
  payload: unknown;
}

const CORS_HEADERS: Record<string, string> = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
  "Access-Control-Allow-Headers": "content-type, authorization",
};

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      ...CORS_HEADERS,
    },
  });
}

async function forwardPayload(
  forwardUrl: string,
  payload: unknown,
  headers: Headers,
): Promise<void> {
  const forwardHeaders = new Headers({ "Content-Type": "application/json" });
  const auth = headers.get("Authorization");
  if (auth) {
    forwardHeaders.set("Authorization", auth);
  }

  const response = await fetch(forwardUrl, {
    method: "POST",
    headers: forwardHeaders,
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    console.error("Forward failed", response.status, await response.text());
  }
}

export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const url = new URL(request.url);

    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: CORS_HEADERS });
    }

    if (url.pathname === "/health" && request.method === "GET") {
      return jsonResponse({ ok: true, service: "wascript-webhook" });
    }

    const match = url.pathname.match(/^\/webhook\/wascript\/([^/]+)$/);
    if (!match) {
      return jsonResponse({ error: "not_found" }, 404);
    }

    const pathSecret = match[1];
    if (!env.WEBHOOK_SECRET || pathSecret !== env.WEBHOOK_SECRET) {
      return jsonResponse({ error: "unauthorized" }, 401);
    }

    if (request.method !== "POST") {
      return jsonResponse({ error: "method_not_allowed" }, 405);
    }

    let payload: unknown;
    try {
      payload = await request.json();
    } catch {
      return jsonResponse({ error: "invalid_json" }, 400);
    }

    const eventId = crypto.randomUUID();
    const record: StoredWebhookEvent = {
      id: eventId,
      receivedAt: new Date().toISOString(),
      payload,
    };

    await env.WEBHOOK_EVENTS.put(`event:${eventId}`, JSON.stringify(record), {
      expirationTtl: 60 * 60 * 24 * 30,
    });

    await env.WEBHOOK_EVENTS.put("event:latest", JSON.stringify(record), {
      expirationTtl: 60 * 60 * 24 * 7,
    });

    if (env.FORWARD_URL) {
      ctx.waitUntil(forwardPayload(env.FORWARD_URL, payload, request.headers));
    }

    console.log("wascript_webhook_received", eventId);
    return jsonResponse({ ok: true, id: eventId });
  },
} satisfies ExportedHandler<Env>;

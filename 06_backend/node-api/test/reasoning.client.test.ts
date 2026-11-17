import assert from "node:assert/strict";
import { createServer, type IncomingMessage, type ServerResponse } from "node:http";
import test from "node:test";

import {
  createReasoningClient,
  type ReasoningClient,
} from "../src/services/reasoning.client.js";
import {
  ReasoningError,
  ReasoningUnavailableError,
} from "../src/lib/errors.js";

interface TestServer {
  url: string;
  close: () => Promise<void>;
}

async function startServer(
  handler: (req: IncomingMessage, res: ServerResponse) => void
): Promise<TestServer> {
  const server = createServer(handler);
  await new Promise<void>((resolve) => {
    server.listen(0, "127.0.0.1", resolve);
  });

  const address = server.address();
  if (address === null || typeof address === "string") {
    throw new Error("Alamat server test tidak valid");
  }

  return {
    url: `http://127.0.0.1:${address.port}`,
    close: () =>
      new Promise<void>((resolve, reject) => {
        server.close((error) => {
          if (error) {
            reject(error);
            return;
          }
          resolve();
        });
      }),
  };
}

function sendJson(
  res: ServerResponse,
  status: number,
  body: unknown
): void {
  res.writeHead(status, { "Content-Type": "application/json" });
  res.end(JSON.stringify(body));
}

function clientFor(
  server: TestServer,
  overrides: { timeoutMs?: number; retryCount?: number } = {}
): ReasoningClient {
  return createReasoningClient({
    baseUrl: server.url,
    timeoutMs: overrides.timeoutMs ?? 1_000,
    retryCount: overrides.retryCount ?? 0,
    retryDelayMs: 1,
  });
}

test("client: response sukses mengembalikan data", async (t) => {
  const server = await startServer((_req, res) => {
    sendJson(res, 200, { success: true, data: { loaded: true } });
  });
  t.after(server.close);

  const data = (await clientFor(server).getStatus()) as {
    loaded: boolean;
  };
  assert.equal(data.loaded, true);
});

test("client: envelope error diteruskan sebagai ReasoningError", async (t) => {
  const server = await startServer((_req, res) => {
    sendJson(res, 503, {
      success: false,
      error: {
        code: "ONTOLOGY_NOT_LOADED",
        message: "Ontology belum dimuat",
      },
    });
  });
  t.after(server.close);

  await assert.rejects(
    () => clientFor(server).getStatus(),
    (error: unknown) => {
      assert.ok(error instanceof ReasoningError);
      assert.equal(error.code, "ONTOLOGY_NOT_LOADED");
      return true;
    }
  );
});

test("client: body bukan JSON menjadi REASONING_INVALID_RESPONSE", async (t) => {
  const server = await startServer((_req, res) => {
    res.writeHead(200, { "Content-Type": "text/plain" });
    res.end("bukan json");
  });
  t.after(server.close);

  await assert.rejects(
    () => clientFor(server).getStatus(),
    (error: unknown) => {
      assert.ok(error instanceof ReasoningError);
      assert.equal(error.code, "REASONING_INVALID_RESPONSE");
      return true;
    }
  );
});

test("client: retry sekali pada 503", async (t) => {
  let calls = 0;
  const server = await startServer((_req, res) => {
    calls += 1;
    if (calls === 1) {
      sendJson(res, 503, {
        success: false,
        error: { code: "REASONING_UNAVAILABLE", message: "sementara" },
      });
      return;
    }
    sendJson(res, 200, { success: true, data: { loaded: true } });
  });
  t.after(server.close);

  const data = (await clientFor(server, {
    retryCount: 1,
  }).getStatus()) as { loaded: boolean };

  assert.equal(calls, 2);
  assert.equal(data.loaded, true);
});

test("client: timeout tidak diretry", async (t) => {
  let calls = 0;
  const server = await startServer((_req, res) => {
    calls += 1;
    setTimeout(() => {
      sendJson(res, 200, { success: true, data: { loaded: true } });
    }, 200);
  });
  t.after(server.close);

  await assert.rejects(
    () =>
      clientFor(server, {
        timeoutMs: 30,
        retryCount: 1,
      }).getStatus(),
    (error: unknown) => {
      assert.ok(error instanceof ReasoningUnavailableError);
      assert.equal(error.code, "REASONING_UNAVAILABLE");
      return true;
    }
  );

  assert.equal(calls, 1);
});

test("client: server mati menjadi REASONING_UNAVAILABLE", async (t) => {
  const server = await startServer((_req, res) => {
    sendJson(res, 200, { success: true, data: { loaded: true } });
  });
  const url = server.url;
  await server.close();

  const client = createReasoningClient({
    baseUrl: url,
    timeoutMs: 500,
    retryCount: 0,
  });

  await assert.rejects(
    () => client.getStatus(),
    (error: unknown) => {
      assert.ok(error instanceof ReasoningUnavailableError);
      assert.equal(error.code, "REASONING_UNAVAILABLE");
      return true;
    }
  );
});

test("client: meneruskan X-Request-Id", async (t) => {
  let observed: string | undefined;
  const server = await startServer((req, res) => {
    observed = req.headers["x-request-id"] as string | undefined;
    sendJson(res, 200, { success: true, data: { loaded: true } });
  });
  t.after(server.close);

  await clientFor(server).getStatus("req-123");
  assert.equal(observed, "req-123");
});

test("client: mengirim body diseaseIris", async (t) => {
  let body = "";
  const server = await startServer((req, res) => {
    req.on("data", (chunk) => {
      body += chunk.toString();
    });
    req.on("end", () => {
      sendJson(res, 200, {
        success: true,
        data: { categories: {}, counts: {} },
      });
    });
  });
  t.after(server.close);

  await clientFor(server).getDiseaseCategories(
    ["PenyakitBlasPadi"],
    "req-456"
  );

  assert.deepEqual(JSON.parse(body), {
    diseaseIris: ["PenyakitBlasPadi"],
  });
});

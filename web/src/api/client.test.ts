import { afterEach, expect, it, vi } from "vitest";
import { ReadApiError, readEndpoint, readQuery } from "./client";

afterEach(() => vi.unstubAllGlobals());

it("uses the bounded same-origin read contract and forwards cancellation", async () => {
  const fetcher = vi
    .fn()
    .mockResolvedValue({ ok: true, json: async () => ({ hits: [] }) });
  vi.stubGlobal("fetch", fetcher);
  const controller = new AbortController();
  await readQuery(
    "search",
    { schema_version: 1, query: { limit: 10 } },
    { signal: controller.signal },
  );
  expect(fetcher).toHaveBeenCalledWith(
    "/api/v1/search",
    expect.objectContaining({
      method: "POST",
      headers: { "Content-Type": "application/json", "X-NetAtlas-Read": "1" },
      credentials: "omit",
      redirect: "error",
      cache: "no-store",
      signal: controller.signal,
    }),
  );
  expect(JSON.parse(fetcher.mock.calls[0][1].body)).toEqual({
    schema_version: 1,
    query: { limit: 10 },
  });
});

it("encodes endpoint paths including IPv6 without interpreting URLs", async () => {
  const fetcher = vi
    .fn()
    .mockResolvedValue({ ok: true, json: async () => ({}) });
  vi.stubGlobal("fetch", fetcher);
  await readEndpoint(
    "endpointHistory",
    { address: "2001:db8::1", transport: "tcp", port: 80 },
    { schema_version: 1 },
  );
  expect(fetcher.mock.calls[0][0]).toBe(
    "/api/v1/endpoints/2001%3Adb8%3A%3A1/tcp/80/history",
  );
});

it("reports stable errors and does not display proxy error bodies", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: false,
      status: 410,
      json: async () => ({ error: { code: "cursor_expired" } }),
    }),
  );
  await expect(readQuery("search", { schema_version: 1 })).rejects.toEqual(
    new ReadApiError(410, "cursor_expired"),
  );
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: false,
      status: 503,
      json: async () => {
        throw new Error("private body");
      },
    }),
  );
  await expect(readQuery("search", { schema_version: 1 })).rejects.toEqual(
    new ReadApiError(503, "unavailable"),
  );
});

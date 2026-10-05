import {
  type ErrorResponse,
  errorCodes,
  type Operations,
  routes,
} from "./schema";

export class ReadApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: ErrorResponse["error"]["code"],
  ) {
    super(`Read API: ${code}`);
  }
}

export type Endpoint = {
  address: string;
  transport: "tcp" | "udp";
  port: number;
};
type EndpointOperation =
  | "endpointDetail"
  | "endpointHistory"
  | "endpointInspection";
type Options = { signal?: AbortSignal };

// Same-origin only; callers render all returned labels/URLs as inert text.
// Types come from OpenAPI; this client does not promise runtime schema validation.
async function request<K extends keyof Operations>(
  body: Operations[K]["request"],
  path: string,
  options?: Options,
): Promise<Operations[K]["response"]> {
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-NetAtlas-Read": "1" },
    body: JSON.stringify(body),
    credentials: "omit",
    cache: "no-store",
    redirect: "error",
    signal: options?.signal,
  });
  if (!response.ok) {
    let code: ErrorResponse["error"]["code"] = "unavailable";
    try {
      const error = (await response.json()) as ErrorResponse;
      if (errorCodes.includes(error.error?.code)) code = error.error.code;
    } catch {
      // Never expose HTML/error bodies or echoed request values as messages.
    }
    throw new ReadApiError(response.status, code);
  }
  return response.json() as Promise<Operations[K]["response"]>;
}

export function readQuery<
  K extends "search" | "facets" | "places" | "operations",
>(
  operation: K,
  body: Operations[K]["request"],
  options?: Options,
): Promise<Operations[K]["response"]> {
  return request<K>(body, routes[operation], options);
}

export function readEndpoint<K extends EndpointOperation>(
  operation: K,
  endpoint: Endpoint,
  body: Operations[K]["request"],
  options?: Options,
): Promise<Operations[K]["response"]> {
  const path = routes[operation]
    .replace("{address}", encodeURIComponent(endpoint.address))
    .replace("{transport}", encodeURIComponent(endpoint.transport))
    .replace("{port}", encodeURIComponent(String(endpoint.port)));
  return request<K>(body, path, options);
}

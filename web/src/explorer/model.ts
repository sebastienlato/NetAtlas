import type { FeatureCollection, Point } from "geojson";
import { ReadApiError } from "../api/client";
import type { Category, Hit, PlaceSummary, SearchQuery } from "../api/schema";

export const categories: Record<Category, string> = {
  unknown: "Unknown",
  web_server: "Web server",
  camera_nvr: "Camera / NVR",
  router: "Router",
  nas: "Network storage",
  printer: "Printer",
  ssh_server: "SSH server",
  vpn_appliance: "VPN appliance",
  mail_server: "Mail server",
  database: "Database",
  iot: "IoT",
  industrial: "Industrial",
};

// React escapes markup; also make invisible controls and directional overrides visible.
export function inert(value: string): string {
  return value.replace(
    /[\p{Cc}\p{Cf}\p{Zl}\p{Zp}]/gu,
    (c) =>
      `[U+${c.codePointAt(0)?.toString(16).toUpperCase().padStart(4, "0")}]`,
  );
}
export function placeLabel(p: PlaceSummary): string {
  return inert(
    `${p.name} · ${p.kind} · ${p.country_code} · ${p.admin_code ?? "admin unknown"} · ${p.id} · source ${p.origin}`,
  );
}
export function placeFilter(p: PlaceSummary, boundary = false): SearchQuery {
  if (boundary) return { boundary_place_id: p.id };
  if (p.kind === "country") return { country: p.country_code };
  return { place_id: p.id };
}
export function features(hits: readonly Hit[]): FeatureCollection<Point> {
  return {
    type: "FeatureCollection",
    features: hits.flatMap((h) => {
      const p = h.place?.point;
      if (
        h.geography_state !== "known" ||
        !p ||
        !p.every(Number.isFinite) ||
        Math.abs(p[0]) > 180 ||
        Math.abs(p[1]) > 90
      )
        return [];
      return [
        {
          type: "Feature" as const,
          geometry: { type: "Point" as const, coordinates: [...p] },
          properties: {
            id: h.id,
            category:
              h.category_state === "multiple"
                ? "multiple"
                : (h.categories[0] ?? "unknown"),
          },
        },
      ];
    }),
  };
}
// Unwrap about the first point so nearby dateline points remain nearby.
export function mapBounds(
  points: readonly number[][],
): [[number, number], [number, number]] | null {
  if (!points.length) return null;
  const ref = points[0][0];
  const xs = points.map(([x]) => ref + ((((x - ref) % 360) + 540) % 360) - 180);
  const ys = points.map((p) => Math.max(-85, Math.min(85, p[1])));
  return [
    [Math.min(...xs), Math.min(...ys)],
    [Math.max(...xs), Math.max(...ys)],
  ];
}
export function message(error: unknown): string {
  if (!(error instanceof ReadApiError))
    return "The local API could not be reached. Check the local services, then retry.";
  switch (error.code) {
    case "busy":
      return "The local API is busy with another read. Wait for it to finish, then retry.";
    case "invalid_cursor":
    case "cursor_expired":
      return "This page has expired or the API restarted. Restart the search.";
    case "unavailable":
      return "Storage is unavailable or the query timed out. Check the local database or narrow the search, then retry.";
    case "too_large":
    case "response_too_large":
      return "The response or request is too large. Choose a smaller page or narrow the search.";
    case "not_found":
      return "That source or dataset is unavailable, expired, removed or suppressed. Run a fresh search.";
    case "forbidden":
      return "Local access was refused. Use the approved loopback address and same-origin proxy.";
    case "invalid_request":
      return "The filters are invalid. Check hashes, literal network, country code and field limits.";
    case "request_timeout":
      return "The request timed out. Retry when the local API is ready.";
    default:
      return "The local read failed. Check the local services, then retry.";
  }
}

// A single shared lane for places and search. Abort obsolete fetches and skip queued
// obsolete jobs; generation checks in the view also guard noncooperative responses.
export class ReadLane {
  private tail: Promise<unknown> = Promise.resolve();
  private controller?: AbortController;
  cancel() {
    this.controller?.abort();
  }
  run<T>(work: (signal: AbortSignal) => Promise<T>): Promise<T> {
    this.cancel();
    const controller = new AbortController();
    this.controller = controller;
    const next = this.tail
      .catch(() => {})
      .then(() => {
        controller.signal.throwIfAborted();
        return work(controller.signal);
      });
    this.tail = next;
    return next;
  }
}

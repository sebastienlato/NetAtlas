import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
} from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { OperationsDashboard } from "./OperationsDashboard";

const snapshot = {
  readiness: {
    status: "ready",
    database: "ok",
    migration: "ok",
    blobs: "ok",
    capacity: "ok",
  },
  checked_at: "2026-10-05T12:00:00Z",
  global_stopped: true,
  stored_jobs: {
    queued: 0,
    leased: 0,
    measuring: 0,
    delivered: 1,
    uncertain: 0,
    cancelled: 0,
    failed: 0,
  },
  permits_issued: 1,
  delivery_receipts: 1,
  retained_sources: 1,
  outbox_events: 1,
  overdue_leases: 0,
  removal_due_sources: 0,
  registered_workers: 2,
  recent_workers: 0,
  blob_free_bytes: 100000000,
};
afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.unstubAllGlobals();
});
it("loads only on explicit refresh through the guarded client and expires", async () => {
  const fetch = vi
    .fn()
    .mockResolvedValue({ ok: true, json: async () => snapshot });
  vi.stubGlobal("fetch", fetch);
  render(<OperationsDashboard />);
  expect(fetch).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Refresh operations" }));
  await screen.findByRole("heading", { name: "New work stopped" });
  expect(fetch.mock.calls[0][0]).toBe("/api/v1/operations");
  expect(fetch.mock.calls[0][1].credentials).toBe("omit");
  expect(fetch.mock.calls[0][1].redirect).toBe("error");
  expect(JSON.parse(fetch.mock.calls[0][1].body)).toEqual({
    schema_version: 1,
  });
  vi.useFakeTimers();
  // Refresh creates a new 60-second timer under the fake clock.
  await act(async () => {
    fireEvent.click(screen.getByRole("button", { name: "Refresh operations" }));
  });
  act(() => vi.advanceTimersByTime(60000));
  expect(
    screen.queryByRole("heading", { name: "New work stopped" }),
  ).toBeNull();
  expect(screen.getByRole("status").textContent).toContain("expired");
});
it("rejects late responses after pagehide and shows only generic failures", async () => {
  let resolve: (value: unknown) => void = () => {};
  const fetch = vi
    .fn()
    .mockImplementationOnce(
      () =>
        new Promise((r) => {
          resolve = r;
        }),
    )
    .mockResolvedValueOnce({
      ok: false,
      status: 503,
      json: async () => ({ secret: "not-for-display" }),
    });
  vi.stubGlobal("fetch", fetch);
  render(<OperationsDashboard />);
  fireEvent.click(screen.getByRole("button", { name: "Refresh operations" }));
  act(() => window.dispatchEvent(new Event("pagehide")));
  await act(async () => resolve({ ok: true, json: async () => snapshot }));
  expect(
    screen.queryByRole("heading", { name: "New work stopped" }),
  ).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Refresh operations" }));
  await screen.findByText("Operations unavailable or busy. Retry explicitly.");
  expect(document.body.textContent).not.toContain("not-for-display");
});

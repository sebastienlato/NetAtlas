import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { App } from "./App";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it("shows API connectivity and clearly identifies the empty foundation", async () => {
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValue({ ok: true, json: async () => ({ status: "ok" }) }),
  );
  render(<App />);
  await screen.findByText("Local API connected");
  expect(
    screen.getByText(
      "This preview shows no measured data and cannot start scans.",
    ),
  ).toBeTruthy();
  expect(
    screen
      .getByRole("link", { name: /synthetic observation/ })
      .getAttribute("href"),
  ).toBe("/api/v1/examples/observation");
});

it("handles an unavailable API without presenting live data", async () => {
  vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));
  render(<App />);
  await screen.findByText("Local API unavailable");
  expect(
    screen.queryByRole("link", { name: /synthetic observation/ }),
  ).toBeNull();
});

it("rejects malformed health responses", async () => {
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValue({ ok: true, json: async () => ({ unrelated: true }) }),
  );
  render(<App />);
  await screen.findByText("Local API unavailable");
});

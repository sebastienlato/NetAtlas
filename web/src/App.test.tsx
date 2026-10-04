import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { App } from "./App";
import { places, response } from "./explorer/fixtures";

vi.mock("./explorer/Map", () => ({ ResultMap: () => <div>Offline map</div> }));
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.useRealTimers();
});
const ok = (body: unknown) => ({ ok: true, json: async () => body });
const submit = () =>
  fireEvent.click(screen.getByRole("button", { name: /Search observations/ }));

it("starts without any data read; enrichment is explicitly disabled by default", async () => {
  const fetch = vi.fn().mockResolvedValue(ok(response));
  vi.stubGlobal("fetch", fetch);
  render(<App />);
  expect(fetch).not.toHaveBeenCalled();
  submit();
  await screen.findByText("Search results");
  const request = JSON.parse(fetch.mock.calls[0][1].body);
  expect(request.query.dataset_sha256).toBeNull();
  expect(request.schema_version).toBe(1);
  expect(fetch.mock.calls[0][1].headers["X-NetAtlas-Read"]).toBe("1");
  expect(screen.getByText("Accuracy radius: unknown")).toBeTruthy();
  expect(screen.getByText(/AS64496 \/ AS64497/)).toBeTruthy();
});
it("uses the original query for continuation and replaces the displayed page", async () => {
  const fetch = vi
    .fn()
    .mockResolvedValueOnce(ok(response))
    .mockResolvedValueOnce(ok({ ...response, hits: [], next_cursor: null }));
  vi.stubGlobal("fetch", fetch);
  render(<App />);
  submit();
  await screen.findByText("Search results");
  fireEvent.click(screen.getByRole("button", { name: "Next results page" }));
  await screen.findByText("No matching observations");
  const first = JSON.parse(fetch.mock.calls[0][1].body),
    second = JSON.parse(fetch.mock.calls[1][1].body);
  expect(second.query).toEqual(first.query);
  expect(second.query.as_of).toBeUndefined();
  expect(second.cursor).toBe(response.next_cursor);
  expect(screen.queryByRole("article")).toBeNull();
});
it("disambiguates same-name places by admin, stable ID and source", async () => {
  const fetch = vi
    .fn()
    .mockResolvedValueOnce(ok(places))
    .mockResolvedValueOnce(ok(response));
  vi.stubGlobal("fetch", fetch);
  render(<App />);
  fireEvent.change(screen.getByLabelText("Dataset SHA-256"), {
    target: { value: "d".repeat(64) },
  });
  fireEvent.change(screen.getByLabelText("Exact place name"), {
    target: { value: "Example Harbor" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Find places" }));
  fireEvent.click(
    await screen.findByRole("button", {
      name: /Example Harbor.*fixture:west.*source fixture/,
    }),
  );
  submit();
  await screen.findByText("Search results");
  expect(JSON.parse(fetch.mock.calls[1][1].body).query.place_id).toBe(
    "fixture:west",
  );
});
it("renders hostile markup, URLs and invisible controls as inert visible text", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(ok(response)));
  const { container } = render(<App />);
  submit();
  await screen.findByText(/\[U\+202E\]/);
  expect(container.querySelector("img, iframe")).toBeNull();
  expect(
    container.querySelector(
      'a[href^="javascript:"], a[href*="hostile.invalid"]',
    ),
  ).toBeNull();
  expect(screen.getByText("Source: javascript:alert(1)")).toBeTruthy();
  expect(screen.getByText("Showing 1 of 3 buckets · truncated")).toBeTruthy();
});
it("aborts obsolete reads and prevents late data replacing changed filters", async () => {
  let resolve: (value: unknown) => void = () => {};
  const fetch = vi
    .fn()
    .mockImplementationOnce(
      () =>
        new Promise((r) => {
          resolve = r;
        }),
    )
    .mockResolvedValueOnce(ok({ ...response, hits: [], next_cursor: null }));
  vi.stubGlobal("fetch", fetch);
  render(<App />);
  submit();
  await waitFor(() => expect(fetch).toHaveBeenCalledTimes(1));
  fireEvent.change(screen.getByLabelText("Product labels"), {
    target: { value: "absent" },
  });
  submit();
  expect(fetch.mock.calls[0][1].signal.aborted).toBe(true);
  expect(fetch).toHaveBeenCalledTimes(1);
  await act(async () => resolve(ok(response)));
  await screen.findByText("No matching observations");
  expect(screen.queryByRole("article")).toBeNull();
  expect(fetch).toHaveBeenCalledTimes(2);
});
it.each([
  [429, "busy", /busy with another read/],
  [503, "unavailable", /Storage is unavailable/],
  [410, "cursor_expired", /page has expired/],
  [400, "invalid_cursor", /page has expired/],
  [413, "response_too_large", /too large/],
  [403, "forbidden", /Local access was refused/],
])(
  "handles generic error %s / %s without arbitrary server text",
  async (status, code, pattern) => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status,
        json: async () => ({ error: { code }, secret: "DO NOT DISPLAY" }),
      }),
    );
    render(<App />);
    submit();
    await screen.findByText(pattern);
    expect(screen.queryByText("DO NOT DISPLAY")).toBeNull();
  },
);
it("clears hidden views and does not restore removed results from cache", async () => {
  const fetch = vi
    .fn()
    .mockResolvedValueOnce(ok(response))
    .mockResolvedValueOnce(ok({ ...response, hits: [] }));
  vi.stubGlobal("fetch", fetch);
  render(<App />);
  submit();
  await screen.findByText("Search results");
  act(() => window.dispatchEvent(new Event("pagehide")));
  expect(screen.queryByRole("article")).toBeNull();
  submit();
  await screen.findByText("No matching observations");
  expect(fetch).toHaveBeenCalledTimes(2);
});
it("clears aged display data instead of keeping an indefinite result cache", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(ok(response)));
  render(<App />);
  submit();
  await screen.findByText("Search results");
  vi.useFakeTimers();
  // Trigger another real response under the fake clock so its expiry timer is owned here.
  submit();
  await act(async () => {
    await Promise.resolve();
    await Promise.resolve();
  });
  await act(async () => vi.advanceTimersByTime(60001));
  expect(screen.queryByRole("article")).toBeNull();
});
it("shows stale and empty place states without interpreting gazetteer entries as observations", async () => {
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValue(
        ok({ ...places, dataset_state: "stale", places: [], total: 0 }),
      ),
  );
  render(<App />);
  fireEvent.change(screen.getByLabelText("Dataset SHA-256"), {
    target: { value: "d".repeat(64) },
  });
  fireEvent.click(screen.getByRole("button", { name: "Find places" }));
  await screen.findByText(/no places are available/);
});

it("keeps places and search in the same cancellable request lane", async () => {
  let resolve: (value: unknown) => void = () => {};
  const fetch = vi
    .fn()
    .mockImplementationOnce(
      () =>
        new Promise((r) => {
          resolve = r;
        }),
    )
    .mockResolvedValueOnce(ok(places));
  vi.stubGlobal("fetch", fetch);
  render(<App />);
  submit();
  await waitFor(() => expect(fetch).toHaveBeenCalledTimes(1));
  fireEvent.change(screen.getByLabelText("Dataset SHA-256"), {
    target: { value: "d".repeat(64) },
  });
  fireEvent.click(screen.getByRole("button", { name: "Find places" }));
  expect(fetch).toHaveBeenCalledTimes(1);
  await act(async () => resolve(ok(response)));
  await screen.findByText(/2 gazetteer matches/);
  expect(fetch.mock.calls.map((call) => call[0])).toEqual([
    "/api/v1/search",
    "/api/v1/places",
  ]);
  expect(screen.queryByRole("article")).toBeNull();
});
it("continues places using the original query and reports traversal caps", async () => {
  const fetch = vi
    .fn()
    .mockResolvedValueOnce(ok({ ...places, next_cursor: "place-next" }))
    .mockResolvedValueOnce(ok({ ...places, places: [], next_cursor: null }))
    .mockResolvedValueOnce(
      ok({ ...response, next_cursor: null, page_limit_reached: true }),
    );
  vi.stubGlobal("fetch", fetch);
  render(<App />);
  fireEvent.change(screen.getByLabelText("Dataset SHA-256"), {
    target: { value: "d".repeat(64) },
  });
  fireEvent.click(screen.getByRole("button", { name: "Find places" }));
  fireEvent.click(
    await screen.findByRole("button", { name: "Next places page" }),
  );
  await screen.findByText(/No places match/);
  expect(JSON.parse(fetch.mock.calls[1][1].body).query).toEqual(
    JSON.parse(fetch.mock.calls[0][1].body).query,
  );
  expect(JSON.parse(fetch.mock.calls[1][1].body).cursor).toBe("place-next");
  submit();
  await screen.findByText(/10,000-hit traversal limit/);
  expect(
    screen.queryByRole("button", { name: "Next results page" }),
  ).toBeNull();
});

it("clears the selected place metadata when the view is hidden", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(ok(places)));
  render(<App />);
  fireEvent.change(screen.getByLabelText("Dataset SHA-256"), {
    target: { value: "d".repeat(64) },
  });
  fireEvent.click(screen.getByRole("button", { name: "Find places" }));
  fireEvent.click(await screen.findByRole("button", { name: /fixture:east/ }));
  expect(screen.getByText("Selected place")).toBeTruthy();
  act(() => window.dispatchEvent(new Event("pagehide")));
  expect(screen.queryByText("Selected place")).toBeNull();
  expect(screen.queryByText(/Example Harbor · city/)).toBeNull();
});

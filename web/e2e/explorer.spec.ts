import { readFileSync } from "node:fs";
import AxeBuilder from "@axe-core/playwright";
import { expect, type Page, test } from "@playwright/test";

const seed = () =>
  JSON.parse(readFileSync("../.cache/web-demo.json", "utf8")) as {
    dataset_sha256: string;
  };
async function start(page: Page) {
  await page.goto("/");
  await page
    .getByLabel("Dataset SHA-256", { exact: true })
    .fill(seed().dataset_sha256);
}
async function search(page: Page) {
  await page.getByRole("button", { name: "Search observations" }).click();
  await expect(
    page.getByRole("heading", { name: "Search results", exact: true }),
  ).toBeVisible();
}
async function find(page: Page, name: string, kind = "") {
  await page.getByLabel("Exact place name").fill(name);
  await page.getByLabel("Place kind").selectOption(kind);
  await page.getByRole("button", { name: "Find places", exact: true }).click();
}

test("real API: country, region, city, disambiguation, filters, pagination and offline clusters", async ({
  page,
}) => {
  const external: string[] = [];
  page.on("request", (req) => {
    if (
      !req.url().startsWith("http://127.0.0.1:5173") &&
      !req.url().startsWith("blob:")
    )
      external.push(req.url());
  });
  await start(page);
  await search(page);
  await expect(page.locator(".counts")).toContainText("12");
  await expect(
    page.getByText("11 mapped / 12 displayed observations"),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: /Zoom into cluster/ }).first(),
  ).toBeVisible();
  await expect(
    page.getByText("Accuracy radius: unknown").first(),
  ).toBeVisible();
  await expect(
    page.getByText("Accuracy radius: 250 km (dataset reported)"),
  ).toBeVisible();
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({ path: "test-results/desktop.png" });
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
  await page
    .getByRole("button", { name: /Zoom into cluster/ })
    .first()
    .click();
  await page
    .getByRole("button", { name: "Locate approximate point" })
    .first()
    .click();
  await expect(page.locator(".map-error")).toHaveCount(0);
  // Same-name places remain separate even in the same country.
  await find(page, "Example Harbor", "city");
  await expect(
    page.getByRole("button", { name: /Example Harbor.*demo:east/ }),
  ).toBeVisible();
  await page.getByRole("button", { name: /Example Harbor.*demo:west/ }).click();
  await search(page);
  await expect(page.getByRole("article")).toHaveCount(1);
  await expect(page.getByRole("article")).toContainText("192.0.2.10");
  await page.getByRole("button", { name: "Clear selected place" }).click();
  await find(page, "Fiji", "country");
  await page.getByRole("button", { name: /Fiji.*ne:1159320625/ }).click();
  await search(page);
  await expect(page.getByRole("article")).toHaveCount(11);
  await page.getByRole("button", { name: "Clear selected place" }).click();
  await find(page, "Example Region", "region");
  await page
    .getByRole("button", { name: /Example Region.*demo:region/ })
    .click();
  await expect(page.getByLabel("Match points within boundary")).toBeChecked();
  await search(page);
  await expect(page.getByRole("article")).toHaveCount(10);
  await page.getByRole("button", { name: "Clear selected place" }).click();
  await find(page, "Suva", "city");
  await page.getByRole("button", { name: /Suva.*ne:1159150917/ }).click();
  await search(page);
  await expect(page.getByRole("article")).toHaveCount(9);
  await page.getByRole("button", { name: "Clear selected place" }).click();
  await page.getByLabel("Product labels").fill("nginx");
  await page.getByLabel("Category", { exact: true }).selectOption("web_server");
  await search(page);
  await expect(page.getByRole("article")).toHaveCount(6);
  await page.getByLabel("Current source").selectOption("evidence");
  await search(page);
  await expect(page.getByRole("article")).toHaveCount(7);
  await page.getByLabel("Product labels").fill("");
  await page.getByLabel("Category", { exact: true }).selectOption("");
  await page
    .getByText("Network, freshness & selection", { exact: true })
    .click();
  await page.getByLabel("Page size").selectOption("5");
  await search(page);
  await expect(page.getByRole("article")).toHaveCount(5);
  const first = await page.getByRole("article").first().getAttribute("id");
  await page.getByRole("button", { name: "Next results page" }).click();
  await expect(page.getByText("PAGE 2 / 5 SHOWN")).toBeVisible();
  expect(await page.getByRole("article").first().getAttribute("id")).not.toBe(
    first,
  );
  await page.getByLabel("Geography state").selectOption("unknown");
  await search(page);
  await expect(
    page.getByRole("heading", { name: "No matching observations" }),
  ).toBeVisible();
  await page.getByLabel("Current source").selectOption("attempt");
  await search(page);
  await expect(page.getByRole("article")).toHaveCount(1);
  await expect(
    page.getByText("0 mapped / 1 displayed observations"),
  ).toBeVisible();
  expect(external).toEqual([]);
});

test("responsive and keyboard-accessible list with no remote resources", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await start(page);
  await search(page);
  await expect(
    page.getByRole("heading", { name: "Search results", exact: true }),
  ).toBeFocused();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({ path: "test-results/mobile.png" });
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
  await page.keyboard.press("Control+Home");
  await page.getByRole("link", { name: "Skip to results" }).focus();
  await page.keyboard.press("Enter");
  await expect(page.locator("#results")).toBeInViewport();
});

test("browser hostile metadata is inert; API failures and empty states are recoverable", async ({
  page,
}) => {
  await start(page);
  await page.route("**/api/v1/search", async (route) => {
    const live = await route.fetch();
    const data = await live.json();
    data.hits[0].products = [
      '<img src="https://hostile.invalid/pixel" onerror="window.pwned=1">\u202E',
    ];
    data.dataset.origins[0].source_url = "javascript:alert(1)";
    await route.fulfill({ response: live, json: data });
  });
  await search(page);
  await expect(page.getByText(/\[U\+202E\]/)).toBeVisible();
  expect(
    await page.locator('img, iframe, a[href^="javascript:"]').count(),
  ).toBe(0);
  await page.unroute("**/api/v1/search");
  await page.route("**/api/v1/search", (r) =>
    r.fulfill({ status: 429, json: { error: { code: "busy" } } }),
  );
  await page.getByRole("button", { name: "Refresh / first page" }).click();
  await expect(page.getByRole("alert")).toContainText("busy");
  await expect(page.getByRole("article")).toHaveCount(0);
  await page.unroute("**/api/v1/search");
  await page.getByRole("button", { name: "Restart search" }).click();
  await expect(page.getByRole("article")).toHaveCount(12);
  await page.getByLabel("Product labels").fill("nonexistent");
  await search(page);
  await expect(
    page.getByText("No matching observations", { exact: true }),
  ).toBeVisible();
});

test("unavailable WebGL preserves the accessible result list", async ({
  page,
}) => {
  await page.addInitScript(() => {
    const original = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function (
      ...args: Parameters<typeof original>
    ) {
      if (String(args[0]).startsWith("webgl")) return null;
      return original.apply(this, args);
    } as typeof original;
  });
  await start(page);
  await search(page);
  await expect(page.getByText(/Map rendering is unavailable/)).toBeVisible();
  await expect(page.getByRole("article")).toHaveCount(12);
});

test("retained timeline and bounded evidence are inert, accessible and cleared", async ({
  page,
}) => {
  const external: string[] = [];
  page.on("request", (req) => {
    if (
      !req.url().startsWith("http://127.0.0.1:5173") &&
      !req.url().startsWith("blob:")
    )
      external.push(req.url());
  });
  await start(page);
  await search(page);
  const negative = page.getByRole("article", {
    name: "192.0.2.1 port 80",
    exact: true,
  });
  await negative
    .getByRole("button", { name: "View endpoint timeline" })
    .click();
  await expect(
    page.getByRole("heading", { name: "Endpoint timeline" }),
  ).toBeFocused();
  await expect(page.getByRole("article")).toHaveCount(2);
  await expect(page.getByRole("article").first()).toContainText("timeout");
  await page
    .getByRole("article")
    .last()
    .getByRole("button", { name: "Inspect this observation" })
    .click();
  await expect(
    page.getByRole("heading", { name: "Service & evidence inspection" }),
  ).toBeFocused();
  await expect(page.locator(".inspection")).toContainText("nginx");
  await page.getByRole("button", { name: "Close inspection" }).click();
  await search(page);
  await page
    .getByRole("article", { name: "192.0.2.3 port 80", exact: true })
    .getByRole("button", { name: "Inspect this observation" })
    .click();
  const inspection = page.locator(".inspection");
  await expect(inspection).toContainText("Certificate · parsed");
  await expect(inspection).toContainText("not_performed");
  await expect(inspection).toContainText("[U+202E]");
  await expect(inspection).toContainText("<script>window.pwned=1</script>");
  await expect(inspection).not.toContainText("never-expose");
  await expect(inspection).not.toContainText("/redirect");
  await inspection
    .getByText("nginx · Web server · asserted", { exact: true })
    .click();
  await expect(inspection).toContainText("http.server");
  await expect(inspection).toContainText("decoded bytes [");
  await expect(inspection).toContainText("trace integrity: checked");
  expect(
    await page.locator("img, iframe, video, audio, object, embed").count(),
  ).toBe(0);
  expect(await page.evaluate(() => "pwned" in window)).toBe(false);
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
  await inspection.scrollIntoViewIfNeeded();
  await page.screenshot({ path: "test-results/inspection-desktop.png" });
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
  await page.screenshot({ path: "test-results/inspection-mobile.png" });
  await page.evaluate(() => window.dispatchEvent(new Event("pagehide")));
  await expect(inspection).toHaveCount(0);
  expect(external).toEqual([]);
});

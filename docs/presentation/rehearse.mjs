// Explicit browser rehearsal against an already running, freshly seeded thesis demo.
// Usage: node docs/presentation/rehearse.mjs DATASET_SHA256
// The fixed loopback read-only path never seeds, measures or schedules work.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import { createRequire } from 'node:module';
const require = createRequire(new URL('../../web/package.json', import.meta.url));
const { chromium } = require('@playwright/test');
const sha = process.argv[2];
assert.match(sha ?? '', /^[a-f0-9]{64}$/);
process.umask(0o077);
const output = 'artifacts/phase14/rehearsal';
await fs.mkdir(output, { recursive: true, mode: 0o700 });
const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
const context = await browser.newContext({ viewport: { width: 1440, height: 1100 } });
const external = [];
const sourceIdentities = new Map();
await context.route('**/*', async route => {
  const url = route.request().url();
  if (!url.startsWith('http://127.0.0.1:8000/') && !url.startsWith('blob:')) {
    external.push(url); await route.abort();
  } else await route.continue();
});
const page = await context.newPage();
page.setDefaultTimeout(10000);
page.setDefaultNavigationTimeout(10000);
page.on('response', async response => {
  if (response.url().endsWith('/api/v1/search') && response.ok()) {
    const data = await response.json();
    for (const h of data.hits) sourceIdentities.set(h.id, { id: h.id, source_sha256: h.source_sha256, derivation_id: h.derivation_id });
  }
});
const { expect } = require('@playwright/test');
async function start() {
  await page.goto('http://127.0.0.1:8000/');
  await page.getByLabel('Dataset SHA-256', { exact: true }).fill(sha);
}
async function search(count) {
  await page.getByRole('button', { name: 'Search observations' }).click();
  await expect(page.getByRole('article')).toHaveCount(count);
}
try {
  const health = await (await page.request.get('http://127.0.0.1:8000/healthz')).json();
  assert.equal(health.phase, 14);
  assert.equal((await page.request.get('http://127.0.0.1:8000/readyz')).status(), 200);
  await start(); await search(15);
  await expect(page.getByText('11 mapped / 15 displayed observations')).toBeVisible();
  await expect(page.getByRole('button', { name: /Zoom into cluster/ }).first()).toBeVisible();
  await page.screenshot({ path: `${output}/explorer.png`, fullPage: false });
  await page.getByRole('article', { name: '192.0.2.1 port 80', exact: true }).getByRole('button', { name: 'View endpoint timeline' }).click();
  await expect(page.getByRole('article')).toHaveCount(2);
  await expect(page.getByRole('article').first()).toContainText('timeout');
  await page.locator('[aria-labelledby="timeline-title"]').screenshot({ path: `${output}/timeline.png` });
  await page.getByRole('article').last().getByRole('button', { name: 'Inspect this observation' }).click();
  await expect(page.locator('.inspection')).toContainText('nginx');
  await start();
  await page.getByLabel('Product labels').fill('nginx'); await search(8);
  await page.getByLabel('Current source').selectOption('evidence'); await search(9);
  await start();
  await page.getByText('Network, freshness & selection', { exact: true }).click();
  await page.getByLabel('Freshness').selectOption('stale'); await search(1);
  await expect(page.getByRole('article')).toContainText('203.0.113.14');
  await page.getByRole('article').screenshot({ path: `${output}/stale.png` });
  await page.getByLabel('Freshness').selectOption('any');
  await page.getByLabel('Geography state').selectOption('unknown'); await search(4);
  await page.getByLabel('Geography state').selectOption('any');
  await page.getByLabel('Observation mode').selectOption('history'); await search(16);
  await start(); await search(15);
  await page.getByRole('article', { name: '203.0.113.15 port 80', exact: true }).getByRole('button', { name: 'Inspect this observation' }).click();
  await expect(page.locator('.inspection')).toContainText('nginx');
  await expect(page.locator('.inspection')).toContainText('OpenSSH');
  await page.locator('.inspection').getByText('nginx · Web server · asserted', { exact: true }).click();
  await expect(page.locator('.inspection')).toContainText('trace integrity: checked');
  await page.locator('.inspection').screenshot({ path: `${output}/ambiguity.png` });
  await page.goto('http://127.0.0.1:8000/operations');
  await page.getByRole('button', { name: 'Refresh operations' }).click();
  await expect(page.getByRole('heading', { name: 'Dependencies: ready' })).toBeVisible();
  await page.screenshot({ path: `${output}/operations.png`, fullPage: true });
  const ops = await (await page.request.post('http://127.0.0.1:8000/api/v1/operations', { headers: { 'X-NetAtlas-Read': '1' }, data: { schema_version: 1 } })).json();
  assert.equal(ops.retained_sources, 16);
  assert.equal(ops.registered_workers, 0);
  assert.equal(ops.permits_issued, 0);
  assert.equal(ops.delivery_receipts, 0);
  assert.equal(sourceIdentities.size, 16);
  assert.deepEqual(external, []);
  await fs.writeFile(`${output}/acceptance.json`, JSON.stringify({ health, dataset_sha256: sha, external_requests: external.length, sources: [...sourceIdentities.values()], operations: ops, passed: true }, null, 2), { mode: 0o600 });
  console.log('Thesis browser walkthrough passed; zero external requests. Private screenshots and identity ledger saved.');
} finally { await browser.close(); }

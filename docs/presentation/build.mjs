// Optional document tooling only. No application dependency or network request.
import fs from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { Presentation, PresentationFile } from '@oai/artifact-tool';

const { SKILL_DIR, NETATLAS_DECK_BUILD, NETATLAS_DECK_OUTPUT, RUNTIME_PYTHON } = process.env;
for (const p of [SKILL_DIR, NETATLAS_DECK_BUILD, NETATLAS_DECK_OUTPUT, RUNTIME_PYTHON]) {
  if (!path.isAbsolute(p ?? '')) throw Error('Explicit absolute authoring paths required');
}
const { resolvePresentationFont, finalizePresentation } = await import(pathToFileURL(
  path.join(SKILL_DIR, 'container_tools/artifact_tool_utils.mjs')).href);
await fs.mkdir(NETATLAS_DECK_BUILD, { recursive: true });
await fs.mkdir(NETATLAS_DECK_OUTPUT, { recursive: true });
const font = resolvePresentationFont();
const p = Presentation.create({ slideSize: { width: 1280, height: 720 } });
const ink = '#123047', muted = '#435D6F', teal = '#087F83';
function text(s, value, x, y, w, h, size = 30, color = ink, bold = false) {
  const shape = s.shapes.add({ geometry: 'textbox', position: { left: x, top: y, width: w, height: h }, fill: 'none', line: { fill: 'none', width: 0 } });
  shape.text = value;
  shape.text.style = { typeface: font, fontSize: size, color, bold, autoFit: 'none' };
}
function slide(title, notes) {
  const s = p.slides.add(); s.background.fill = '#F5F8FA';
  text(s, title, 64, 48, 1152, 112, 44, ink, true);
  s.speakerNotes.textFrame.setText(notes);
  return s;
}
function body(s, lines, y = 196) {
  lines.forEach((line, i) => text(s, line, 72, y + i * 94, 1120, 84, 30));
}
function table(s, values, y = 194, height = 330) {
  const t = s.tables.add({ rows: values.length, columns: values[0].length, left: 72, top: y, width: 1136, height, values });
  for (let r = 0; r < values.length; r++) for (let c = 0; c < values[0].length; c++) {
    const cell = t.getCell(r, c);
    cell.fill = r === 0 ? ink : (r % 2 ? '#FFFFFF' : '#EAF1F4');
    cell.text.style = { typeface: font, fontSize: 26, color: r === 0 ? '#FFFFFF' : ink, bold: r === 0 };
  }
  return t;
}
function foot(s, value) { text(s, value, 72, 605, 1136, 75, 23, muted); }
let s = slide('NetAtlas', 'Private thesis candidate. Package 0.15.0, Phase 14. Read docs/DEMONSTRATION.md for the 12-minute live sequence. No publication or license grant.');
text(s, 'Internet exposure search\nand geographic exploration', 72, 230, 1100, 155, 52, teal, true);
text(s, 'An evidence-preserving local demonstration', 72, 452, 1100, 72, 32);
foot(s, 'Independent university thesis project\nPrivate review candidate, 5 October 2026');

s = slide('Research scope', 'Sources: README.md, SECURITY.md, docs/PROTOCOL_EVIDENCE.md. No Shodan/Censys database, paid infrastructure or real campaign. The system collects only explicitly authored loopback fixtures during acceptance.');
body(s, ['Bounded collection records ordinary unauthenticated exposure.', 'Immutable sources retain independent, replayable interpretations.', 'Search and inspection read retained evidence without starting probes.', 'Qualification uses authored fixtures and local loopback services.']);
foot(s, 'Real-world accuracy, physical-device identity and worldwide capacity remain unqualified.');

s = slide('Architecture and operator boundaries', 'Sources: ARCHITECTURE.md, docs/DISTRIBUTED.md, docs/SCHEDULING.md. Domain contracts are I/O-free. The coordinator is separate from the read service. Fingerprint and enrichment operations are explicit. Search indexes authoritative tables directly. No asynchronous search-copy deletion lag or external exactly-once effect is claimed.');
table(s, [['Boundary', 'Responsibility'], ['Policy / scheduler / workers', 'Authored scope, central permits, bounded collection'], ['Spool / ingestion / history', 'Fsynced bytes, immutable source UUID and digest'], ['Fingerprint / enrichment', 'Separate versioned, source-bound derivations'], ['Search / read API / UI', 'PostgreSQL indexes, retained reads, inert views']], 180, 350);
foot(s, 'A search does not run collection or derivation. Independent modules share explicit contracts.');

s = slide('Negative history stays visible', 'Sources: docs/DEMONSTRATION.md, docs/SEARCH.md, docs/INSPECTION.md. Live example: 192.0.2.1:80. Use the current card to open timeline and inspect the older positive with its exact UUID/digest. Do not hardcode identities between runs.');
table(s, [['Source choice', '192.0.2.1:80 in the authored seed'], ['Latest attempt', 'Timeout, distinct source identity'], ['Last nonempty evidence', 'Older nginx assertion remains retained'], ['All retained attempts', 'Both original sources remain inspectable']], 205, 280);
foot(s, 'Source choice precedes filters. Replaying delivery preserves identity. Refresh reserves a new identity.');

s = slide('Live geographic explorer', 'Sources: docs/DEMONSTRATION.md and docs/GEOGRAPHIC_UI.md. Follow live walkthrough: exact seed hash, then search, Example Harbor west, source choice, timeline and ambiguity. The packaged basemap covers Fiji only. Natural Earth v5.1.2 public domain, fictional IP/ASN associations.');
body(s, ['One thesis seed: 16 sources across 15 endpoint keys.', 'Latest attempt: 15 sources and 13 candidate records.', '11 mapped points and 4 geographic gaps on the displayed page.', 'Example Harbor retains separate east and west place identities.']);
foot(s, 'Local assets only. Map clusters count displayed observations, never physical devices.');

s = slide('Product assertions and unknowns', 'Source: docs/EVALUATION_REPORT.md, Phase 13 run 2026-10-05T17:07:00Z. 30 purposive same-author cases labelled separately from predictions. 29 product-labelled sources, one null truth. Fixed core pack. Precision = TP/(TP+FP), recall = TP/(TP+FN). No population estimate. Role precision/recall is separately lower: web 5/6 and 5/10, SSH 2/3 and 2/4, mail 1/1 and 1/2. Eight unsupported classes remain misses. Nominal intervals only show tiny-denominator sensitivity.');
text(s, '30 same-author authored cases. Role scoring is separate. No population accuracy claim.', 72, 143, 1136, 38, 24, muted);
table(s, [['Assertion', 'Precision', 'Recall'], ['nginx', '6 / 6', '6 / 7'], ['OpenSSH', '3 / 3', '3 / 4'], ['Postfix', '1 / 1', '1 / 1'], ['Apache', 'Undefined', '0 / 1']], 200, 310);
foot(s, '21 / 30 sources yield no candidates. One preserves multiple products and roles. Spoofed markers defeat identity inference.');

s = slide('Geography and selection bias', 'Source: docs/EVALUATION_REPORT.md. This six-source evaluation fixture differs from the 15-endpoint presentation seed. Country associations include sources without a point. No physical device location or country membership follows. IPv6 counts are seeds/regions, never exhaustive address-space coverage.');
body(s, ['Evaluation view: 4 points, 2 gaps, 3 unknown radii among points.', 'The only known fixture radius is 250 km, not measured error.', 'Same-name places retain exact dataset and stable place identities.', 'Seedless IPv6 regions remain unseen by the authored schedule.']);
foot(s, 'Unknown geography is not random missingness. Point maps cannot describe global prevalence.');

s = slide('Worker failure and refresh semantics', 'Sources: docs/DISTRIBUTED.md, docs/SCHEDULING.md, tests/test_control.py and tests/test_scheduler.py. Full acceptance includes two actual processes, authored HTTP/TLS, two lost delivery ACKs, three permits, two sources. These are safety checks, not measured distributed throughput.');
table(s, [['Event', 'Behavior'], ['Connection request', 'Committed one-use 250-ms permit'], ['Lost delivery acknowledgement', 'Replay original saved UUID and digest'], ['Issued attempt becomes uncertain', 'No automatic remeasurement'], ['Explicit source-bound refresh', 'New job, attempt and source under ordinary budgets']], 180, 350);
foot(s, 'Two trusted local workers. Heartbeat loss normally closes active I/O within about 3 seconds, subject to scheduling.');

s = slide('Local performance evidence', 'Source: docs/EVALUATION_REPORT.md, original Phase 13 three-repetition run. 128 endpoints / 384 sources, one excluded warm-up, 10 complete timed queries per shape per repetition, warm caches and single client. p95 with 10 samples is the maximum. Source pipeline includes three commits, fixture construction and serialization. Standalone loopback is four greeting services at normal pacing. These measurements exclude browser/HTTP, remote latency and sustained/concurrent/global operation.');
table(s, [['Operation', 'Observed range'], ['Current-evidence query p50', '7.878–8.317 ms'], ['Evidence-history query p50', '14.163–14.305 ms'], ['Three-commit durable source pipeline', '108.6–112.5 sources/s'], ['Standalone loopback capture to search', '1.298–1.306 sources/s']], 180, 350);
foot(s, 'Small warm-cache single-client trials. OpenSearch remains deferred. No worldwide rate or cost extrapolation.');

s = slide('Operations and local cost', 'Sources: docs/OPERATIONS.md, docs/EVALUATION_REPORT.md, docs/DEPENDENCIES.md. Relation bytes include indexes and exclude WAL, backups, VM disk and physical allocation. Two repeated blobs total only 94 logical bytes. VM budget is shared with other disposable rehearsal container while it runs. Readiness does not verify every blob/backup or independent copy.');
body(s, ['Readiness checks dependencies. The dashboard only reads counts.', 'Read and control roles have separate explicit database grants.', 'Sources retain 30 days. Backups retain at most 7 days.', 'The demo needs no paid service. Hardware and operator time still cost.']);
foot(s, 'Original fixture relations: 565,248 B empty to 4,276,224 B at 384 sources. Repetitive payloads cannot forecast real storage.');

s = slide('Reproducibility', 'Sources: docs/INSTALLATION.md and docs/RELEASE_CANDIDATE.md. Fresh local clone, fresh caches and disposable volume use pinned prerequisites. Offline package rebuild succeeds after initial acquisition. Browser and image prerequisites may be reused. No virgin-machine or host-wide network-blocking claim. See docs/DEMONSTRATION.md for exact commands and source identity handling.');
body(s, ['Pinned runtime and locked packages define installation inputs.', 'Fresh clone and disposable storage preserve the owner installation.', 'Explicit seed prints its exact dataset hash and validity window.', 'Full acceptance includes database, worker and production-browser checks.']);
foot(s, 'Initial downloads are required. After setup, the demo uses local assets, storage and loopback only.');

s = slide('Candidate status and remaining decisions', 'Sources: PROJECT_STATE.md, ROADMAP.md, docs/RELEASE_CANDIDATE.md, SECURITY.md. All independently deliverable Phase 14 work is a private candidate. Ask the owner/university for license and publication permission before any public sharing or tag/release. No next roadmap implementation phase is invented. External institutional study remains a separately authorized proposal.');
body(s, ['The candidate demonstrates the complete local evidence workflow.', 'The fixed corpus exposes unknowns, spoofing and unsupported classes.', 'Public redistribution still needs an owner/university license decision.', 'A tag or release needs explicit authorization for a reviewed commit.']);
foot(s, 'No real campaign, public listener, worldwide workers or comprehensive sanitizer is qualified.');

const candidatePath = path.join(NETATLAS_DECK_BUILD, 'candidate.pptx');
await (await PresentationFile.exportPptx(p)).save(candidatePath);
const result = await finalizePresentation({ workspaceDir: process.cwd(), candidatePath,
  finalPath: path.join(NETATLAS_DECK_OUTPUT, 'NetAtlas-thesis-candidate.pptx'),
  pythonExecutable: RUNTIME_PYTHON,
  integrityValidatorPath: path.join(SKILL_DIR, 'container_tools/inspect_presentation_package_integrity.py'),
  layoutValidatorPath: path.join(SKILL_DIR, 'container_tools/inspect_presentation_layout_geometry.py'),
  layoutArgs: ['--expected-slide-size-emu', '12192000,6858000', '--validate-heading-fit', ...[3, 4, 6, 8, 9].flatMap(n => ['--require-native-table-slide', String(n)])],
  fontPolicy: { basis: 'design', families: [font] },
  requiredNativeTableOwnerSlides: [3, 4, 6, 8, 9],
  verifyArtifactToolImport: true,
  receiptPath: path.join(NETATLAS_DECK_BUILD, 'validation.json'),
});
for (let i = 0; i < p.slides.items.length; i++) {
  const png = await p.export({ slide: p.slides.items[i], format: 'png', scale: 1 });
  await fs.writeFile(path.join(NETATLAS_DECK_BUILD, `slide-${i+1}.png`), new Uint8Array(await png.arrayBuffer()));
}
console.log(JSON.stringify({ font, slides: p.slides.items.length, result }));

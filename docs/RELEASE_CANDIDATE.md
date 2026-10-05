# Phase 14 private release candidate

Prepared **2026-10-05**. Package **0.15.0**, health **14**, Alembic **0006**.
**Engineering/demo work complete; publication/license and tag/release decisions remain
with the owner/university.** No tag, GitHub Release, public repository, hosted listener,
real campaign or new roadmap phase is part of this delivery.

## Reviewable package

- [INSTALLATION](INSTALLATION.md): first acquisition, local deployment, isolated
  rehearsal, offline cache reuse and targeted teardown commands.
- [DEMONSTRATION](DEMONSTRATION.md): 12-minute examiner walkthrough, exact expected
  counts/source choices, worker/schedule evidence, qualified findings and cost limits.
- [Presentation sources](presentation/README.md): editable 12-slide deck with notes,
  source citations and five native tables; reproducible browser walkthrough script.
  Generated deck and screenshots remain ignored/private under artifacts/phase14/.
- [Architecture](../ARCHITECTURE.md), [evaluation protocol](EVALUATION.md) and
  [original measured findings](EVALUATION_REPORT.md) remain the evidence base.
  The original Phase 13 report is preserved without relabelling its timings as new.
- `make thesis-demo`: optional explicit authored profile; no new read/UI controls,
  dependency, migration, fingerprint rule or collection semantics. Existing `make demo`
  still appends its original 13 sources for 12 endpoints. The thesis profile adds
  stale/ambiguous/closed examples, for 16 sources / 15 endpoints in an empty DB.

## Actual installation rehearsal

On the existing macOS arm64 host, runtime checks confirmed Python 3.14.7, uv 0.12.19,
Node 26.8.1 and npm 11.19.0. Existing Colima netatlas remained running at 2 CPUs /
2 GiB / 20 GiB. A fresh local clone with candidate source changes copied in used
empty separate uv/npm caches and a new `.venv`/node_modules. `make local-build` completed
locked installation and both builds. Then those **disposable** dependency directories
were removed and `UV_OFFLINE=1 npm_config_offline=true make setup build smoke`
succeeded from the primed caches. The clone's source state was explicitly dirty,
based on Phase 13 commit `c5d51dd9cb8b9e1e8d37f3f89e669931bd008a8f`.

The first container start from macOS `/var/folders` failed because Colima could not
mount the secret outside its shared paths. Moving only the disposable clone under
the shared workspace and recreating its venv offline resolved it. INSTALLATION now
calls this out. No owner secret or volume was substituted to bypass the failure.

A separate Compose project `netatlas_phase14_rehearsal_1649`, new secret and new named
volume used loopback port **55433**. `up --no-build --pull never --wait` reused the
existing pinned native PostGIS image. Fresh migrations, ordinary expiry, additive
read/control role provisioning, thesis seeding and `verify` succeeded with
**16 observations / 16 fingerprint derivations / 16 enrichments**. The seed clock was
**2026-10-05T17:59:02.987168Z**; its authored dataset window was October 4–12 at that
same clock. The exact hash is recorded privately with the walkthrough, never inferred
from a prior run. `make local-serve` used its restricted read account and built UI.

This was a fresh checkout/dependency environment and storage rehearsal on an existing
host, **not a virgin-machine installation**. It reused acquired tool executables,
Docker/Colima, the pinned image and Chromium. No uncached APT/image rebuild or new OS
browser installation was qualified. Package offline flags and browser external-request
rejection were exercised; no host-wide network air gap is claimed. First downloads,
transitive image limitations and the CDN-dependent optional Swagger `/docs` page are
explicit in INSTALLATION. Core explorer/operations assets remain fully local.

## Verification evidence

- Complete `make check-db COMPOSE=docker-compose`: **396 Python tests, 28 web tests,
  six production Chromium tests**. Ruff/format, strict mypy, Biome/TypeScript, generated
  contract drift, Python/web builds and CLI smoke passed. Worker/schedule/operations,
  retention/suppression, source integrity, restricted roles and stopped restores ran.
- Running under private `umask 077` initially exposed two old tests whose supposedly
  public directories were actually created private. Fixtures now explicitly chmod
  those directories to 0755. The tests still assert rejection; production permission
  behavior is unchanged. Full acceptance then passed under the same private umask.
- The final inventory comparison exposed Playwright's default forced termination
  bypassing browser-fixture cleanup. Playwright now requests SIGTERM with a ten-second
  grace period. A returning outer signal handler additionally handles Uvicorn's
  signal re-raise, allowing finally cleanup. Only the two exact identified leftover
  fixture DBs, their roles and matching private temporary roots were removed across
  the diagnosis runs. Full acceptance was rerun and owner inventory compared again.
- Thesis-profile integration checks assert 15 current endpoints/sources, 13 candidates,
  11 known points, 16 historical sources, exact stale/closed and nginx-selection counts,
  two source-bound candidates with checked traces and unchanged canonical replay.
- Separate read-only browser rehearsal against the actual restricted-role installation
  verifies the thesis counts, negative timeline, exact inspection, stale and unknown
  cases, ambiguity, operations/readiness and **zero external requests**. Private
  screenshots and an exact source UUID/digest/derivation ledger accompany it.
- One repetition / two samples per query evaluation recheck completed at an explicit
  **2026-10-05T18:01:39.226760Z** fixture clock. All classification, exact functional,
  geographic, scheduling and injected-backpressure oracles passed. One excluded
  warm-up and one measured standalone loopback campaign each completed four sources,
  four connections, three candidates, one unknown and zero incomplete sources.
  A first invocation with a future clock failed closed without a completed output;
  the successful invocation used the DB clock minus ten seconds. No bound changed.
- This is a reproducibility recheck, not a replacement performance study. The original
  Phase 13 three-repetition/ten-sample results and failure ledger remain authoritative
  for the thesis numbers. Recheck evaluated-tree SHA-256:
  `3d380079df7ebf93a3a994486667e1ddd644b9b6e797744005c9703d26c5be87`.
  Private completed JSON SHA-256:
  `770449dab4a391a1f54e57ac849137af6255c6a38b7f0fc320416142b236e931`.
- Fresh Python/npm advisory audits found **zero known vulnerabilities** within the
  documented installed-package scope. Local unpublished NetAtlas is skipped by
  pip-audit. No container/OS/security certification follows. See DEPENDENCIES.
- The editable deck passed package/layout/import checks; all 12 slide renders were
  visually inspected. Native PowerPoint execution was not tested. Generated outputs
  remain private, not Git release assets. The existing 1.304-MB JS / 511-kB worker
  build warning remains; no low-bandwidth qualification is claimed.

## Preservation and cleanup

Owner verification remains **2 sources / 1 fingerprint / 1 enrichment**. Comparison
against the private pre-work snapshot checks original source UUID/digests, all owner
active-storage file hashes (including secret/service files; backup archives were
excluded from this hash comparison), DB/role inventories, container
identity and mounts. No persistent owner worker/coordinator was created. The disposable
rehearsal app was stopped, its specific Compose container/volume/network removed and
its identified clone deleted. Private aggregate/log evidence and presentation outputs
remain separately ignored. Normal final test cleanup leaves no new DBs or roles.

## Acceptance and publication checklist

- [x] Rehearse a new checkout, locked installation and disposable storage.
- [x] Distinguish first downloads from offline operation after acquisition.
- [x] Demonstrate collection separately from authored UI seeding and read actions.
- [x] Preserve negative/stale/unknown/ambiguous cases and exact source identities.
- [x] Exercise worker/schedule failures without a new owner coordinator or network.
- [x] Run complete checks and a proportionate evaluation recheck; retain limitations.
- [x] Prepare installation, architecture/evaluation references, speaking guide and deck.
- [x] Recheck dependency advisories and retain third-party notices/asset provenance.
- [x] Review tracked source changes; exclude secrets, captures, generated outputs,
  measured reports, local datasets/configuration and presentation exports.
- [ ] Owner/university decides redistribution license and any thesis embargo/rights.
- [ ] Owner specifies allowed publication audience/scope and any public security/contact
  arrangements. Keeping the repository private remains a valid decision.
- [ ] Owner explicitly authorizes a tag/release for an exact reviewed commit, if desired.
  Preparing this candidate does not supply that authorization.

After those decisions, independently review every proposed distributable (including
Git history, source archive, wheel, static assets, slides and notices). The project
has no selected redistribution license. Natural Earth and dependency licenses do not
grant a license to this project's authored work. Do not upload private measured JSON,
spools, source ledgers, logs, databases or backups as release assets. A license/publication
decision does not authorize real measurement or enable real ingestion.

Git history and the completion report identify the final delivery commit, remote
HEAD equality, clean tree and CI result. They are not self-referential hashes in this
file. No implementation blocker remains. Read NEXT_PHASE for maintenance handoff;
there is no newly invented Phase 15.

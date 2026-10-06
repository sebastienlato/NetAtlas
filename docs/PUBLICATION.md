# Public source and class demonstration — October 6, 2026

The owner requested demonstration readiness and explicitly selected **public source
code only**. The existing [GitHub repository](https://github.com/sebastienlato/NetAtlas)
is public. This is the Phase 14 publication follow-up, not a new roadmap phase.
Classmates can follow [CLASS_DEMO](CLASS_DEMO.md) to run authored samples locally.
No public application, measurement service, release or tag was created. No project
redistribution license was selected. Runtime code, dependencies, schemas and migrations
are unchanged; all existing measurement and data boundaries remain in force.

## Functional evidence

- `make check-db COMPOSE=docker-compose` passed: **396 Python, 28 web and six
  production Chromium tests**, contract/lint/format/type checks, both builds and
  CLI smoke. This includes worker failures, retention/removal, backups/restores,
  restricted roles, hostile-content handling and local HTTP admission controls.
- A separate fresh disposable database with restricted read credentials served the
  thesis profile through the built application. The existing presentation rehearsal
  passed search/map counts, negative history, stale/unknown/ambiguous results,
  source-bound inspection and operations/readiness, with **zero external browser
  requests**. Its explorer screenshot was visually reviewed. Private outputs are
  under ignored `artifacts/publication/`; they are not published.
- The rehearsal listener, its database and service roles were cleaned up. The
  owner's storage still verifies **two observations, one fingerprint and one
  enrichment**. Existing credentials/volume were preserved. This recheck reused
  acquired runtimes, packages, Chromium and the cached image; it is not a new
  cold-machine installation qualification.

## Security and publication review

- Fresh npm audit: **zero known vulnerabilities**. Isolated pip-audit 2.9.0:
  **38 dependencies without known vulnerabilities**; unpublished NetAtlas itself
  is skipped. See [DEPENDENCIES](DEPENDENCIES.md) for reproducible commands/scope.
- Gitleaks **8.30.1** scanned all **21 pre-publication commits** with `--log-opts=--all`
  and redacted private JSON output. Its eight generic-key findings are all line-2
  `// OpenAPI SHA-256:` comments in historical generated `web/src/api/schema.ts`.
  Each exact historical line was checked; the generator computes a public schema
  digest. No credential finding remained after that review. No broad suppression
  or scan exclusion was added.
- All **21 existing GitHub Actions run log archives** were downloaded to ignored
  private storage and scanned with Gitleaks: **no findings**. No uploaded Actions
  artifacts, issues, pull requests or releases existed at publication. Historical
  and current file inventories contain no data/capture/output/credential paths.
  Only authored documentation-address fixtures and reviewed licensed map assets
  are shipped; generated decks, ledgers, captures, logs and local secrets stay ignored.
- Public visibility, secret scanning, secret push protection, dependency alerts and
  private vulnerability reporting were enabled and read back through GitHub.
  Initial GitHub secret-alert list was empty. Automated dependency updates are not
  enabled; dependency changes still require review and locked validation.

These checks support this local demonstration and source publication. They do not
prove absence of all vulnerabilities or qualify a public API, host/container OS,
hostile multi-user isolation, real captures or worldwide measurement. The existing
large web-bundle warning remains. Source visibility does not select a project license.

## Handoff

Read [NEXT_PHASE](NEXT_PHASE.md) before future maintenance. Do not create another
phase or deployment automatically. Final commit, remote equality, clean-tree state
and exact-commit CI result are reported at delivery and can be checked in GitHub.
Keep the original Phase 13 evaluation and October 5 rehearsal as historical evidence.

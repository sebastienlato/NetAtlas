# Phase 12 dependency review — 2026-10-05

The exact application inputs remain uv.lock and web/package-lock.json with runtime
pins Python 3.14.7, uv 0.12.19, Node 26.8.1 and npm 11.19.0. Setup uses locked installs.
No new application dependency was added for telemetry, dashboards or service roles.
PostgreSQL 18.3 image digest and native PostGIS 3.6.4 package pins are unchanged.
Transitive APT packages/build infrastructure remain a reproducibility limitation;
this review is not a full container/OS vulnerability or supply-chain certification.

Commands executed against installed locked application/dev packages:

```sh
npm --prefix web audit --json
uvx --from pip-audit==2.9.0 pip-audit --path .venv/lib/python3.14/site-packages --format json
```

The audit tool runs in an isolated environment, is not an application dependency,
and queries public advisory services with dependency names/versions only. Store full
reports privately under ignored output; do not upload observations, configs or secrets.
A future unavailable advisory service is an unverified audit, never a clean result.
Repeat after dependency changes and before the release phase; do not run automatic
unreviewed fixes. Vulnerability databases change and have coverage gaps.

Initial npm audit: **zero known vulnerabilities**, 184 reported dependency entries
(including development/optional entries). Initial Python audit: three advisories in
cryptography 48.0.1, none in the other audited installed packages:

| Upstream advisory | Affected feature / decision |
| --- | --- |
| [GHSA-g6cj-pr64-35w5](https://github.com/pyca/cryptography/security/advisories/GHSA-g6cj-pr64-35w5) | PKCS#7 decryption error/timing distinctions; upstream fix starts at 50.0.0. NetAtlas performs no PKCS#7 decryption. |
| [GHSA-jwv3-5hgf-82ww](https://github.com/pyca/cryptography/security/advisories/GHSA-jwv3-5hgf-82ww) | Certificate chain-building resource cost; fix starts at 49.0.0. NetAtlas does not call the verifier. |
| [GHSA-m2h6-j472-rp4c](https://github.com/pyca/cryptography/security/advisories/GHSA-m2h6-j472-rp4c) | Verifier DNS name-constraint behavior; fix starts at 49.0.0. NetAtlas neither verifies chains nor resolves names. |

Code review found only local bounded DER assertion parsing in inspection and ephemeral
certificate generation in tests. Those vulnerable features are not invoked. Nevertheless,
updated the reviewed range to `cryptography>=50,<51`, locked **50.0.2**, and reran
certificate/inspection and complete regression acceptance. No trust/verification,
network fetch, preview-policy or canonical-source semantic change was introduced.
Final pip-audit: **no known vulnerabilities found** in 38 audited installed packages;
NetAtlas itself is explicitly skipped because it is a local unpublished package.
This is not a security proof. Source/static/behavior checks cover this repository.

Third-party runtime licenses were inspected from installed distribution/package
metadata: cryptography remains Apache-2.0 OR BSD-3-Clause, alembic/FastAPI/SQLAlchemy/Pydantic use MIT, uvicorn uses BSD-3-Clause,
psycopg uses LGPL-3.0-only, and MapLibre retains BSD-3-Clause plus its
bundled notice. No new map, fingerprint or geography dataset is added. Keep the
existing MAP_ASSETS licenses/hashes and the owner/university publication decision.

References: [pip-audit scope/limitations](https://github.com/pypa/pip-audit),
[npm audit behavior](https://docs.npmjs.com/cli/v11/commands/npm-audit/),
[PostgreSQL grants and inherited PUBLIC privileges](https://www.postgresql.org/docs/18/sql-grant.html).

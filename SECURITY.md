# Measurement and data handling policy

NetAtlas measures ordinary unauthenticated network exposure. It does not guess
credentials, bypass authentication, exploit vulnerabilities, gain persistence,
modify devices, or carry out destructive actions. Service exposure is not itself
evidence of a vulnerability. Phase 1 implements bounded TCP connect-only discovery.
Configuration defaults disabled and CLI defaults dry-run; enabled identity plus
`--measure` are required. No application data is sent or captured. All implementation
validation uses synthetic/loopback fixtures.

## Required before measurement

- Explicit bounded scope, dry-run preview, identifiable operator contact and research
  user-agent, pinned campaign configuration/policy, and a working exclusion/opt-out path.
- Deny non-routable/special-use/multicast addresses and operator exclusions by default.
  A lab override must be restricted to explicit loopback fixture scope.
- Check destination eligibility before every connection, including any future DNS
  resolution or redirect hop. Default collectors do not follow redirects.
- Enforce concurrency, global/per-prefix rate budgets, connect/interaction timeouts,
  byte caps, bounded retries, cancellation, and reliable socket closure.
- Tests use synthetic or local fixtures; developing a scanner does not authorize an
  Internet sweep. Later real campaigns document network/institutional permissions
  and operating constraints separately from ordinary development.

## Phase 1 enforcement

The immutable campaign configuration pins exclusion and opt-out CIDRs. Denials
precede any allowlist; lab mode only accepts explicit `127.0.0.1` and `::1` literals.
When receiving a new opt-out, stop any active campaign, update local configuration,
preview, then restart. No hot-reload or distributed propagation exists yet. Policy
is rechecked immediately before each connection. Identity validation checks syntax;
it does not establish contact ownership or permission to measure a target.

`docs/DISCOVERY.md` specifies hard scope/rate/concurrency/time bounds and graceful
stop semantics. Logs omit addresses, contacts and raw exception text. Preview output
shows requested scope intentionally. Private local manifests contain non-secret
operator metadata and scope; observations contain endpoint addresses. Keep both
under ignored `data/`; no credentials belong in any measurement setting. Graceful
stop flushes results; force-kill/power-loss recovery is not promised in this phase.

## Evidence and privacy

Responses are untrusted and may contain personal data, secrets, hostile scripts, or
terminal escapes. Capture only bounded necessary evidence. Do not authenticate,
enumerate private data, fetch camera streams, or crawl files. Never execute captured
content or render active HTML; use escaped text/hex and explicit safe downloads.
Do not include raw response content, credentials, or full query strings in logs.

Phase 4 must establish access controls, minimization/redaction, retention expiry,
and opt-out/removal semantics before ingesting real captures. Operator opt-outs
must stop new work and define how stored evidence/search projections are removed
or restricted. Store raw sensitive evidence separately from public metadata.
Keep production credentials outside effective-config hashes and committed files.

## Application boundaries

Phase 0 API and UI bind to loopback and have no authentication. Do not expose them
as a public service. Future read API and authenticated measurement control plane
are separate. Protect ingest endpoints from malformed/oversized events and workers
from hostile protocols. Static analysis and validation do not replace these runtime
controls; implement and test them in their respective phases.

## Reporting and response

This is currently a private research repository. Report issues privately to its
owner through an existing trusted channel. Do not post real device addresses,
captured secrets, or exploit instructions in public issues. A public security
contact and operator opt-out URL must be established before public deployment.
If a credential is accidentally committed, revoke/rotate it and remove it from
active use; merely deleting the current file does not remove Git history.

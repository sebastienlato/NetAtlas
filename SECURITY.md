# Measurement and data handling policy

NetAtlas measures ordinary unauthenticated network exposure. It does not guess
credentials, bypass authentication, exploit vulnerabilities, gain persistence,
modify devices, or carry out destructive actions. Service exposure is not itself
evidence of a vulnerability. Phase 2 adds opt-in bounded HTTP/TLS/SSH/SMTP evidence
to TCP discovery.
Configuration defaults disabled and CLI defaults dry-run; enabled identity plus
`--measure` are required. Only protocol opt-in sends bounded HTTP/TLS handshake
traffic and captures evidence; connect-only mode sends no application bytes. All
implementation validation uses synthetic/loopback fixtures.

## Required before measurement

- Explicit bounded scope, dry-run preview, identifiable operator contact and research
  user-agent, pinned campaign configuration/policy, and a working exclusion/opt-out path.
- Deny non-routable/special-use/multicast addresses and operator exclusions by default.
  A lab override must be restricted to explicit loopback fixture scope.
- Check destination eligibility before every connection, including additional collector
  connections. No DNS resolution, SNI names or redirect following is supported.
- Enforce concurrency, global/per-prefix rate budgets, connect/interaction timeouts,
  byte caps, bounded retries, cancellation, and reliable socket closure.
- Tests use synthetic or local fixtures; developing a scanner does not authorize an
  Internet sweep. Later real campaigns document network/institutional permissions
  and operating constraints separately from ordinary development.

## Measurement enforcement through Phase 9

The immutable campaign configuration pins exclusion and opt-out CIDRs. Denials
precede any allowlist; lab mode only accepts explicit `127.0.0.1` and `::1` literals.
When receiving a new opt-out, stop any active campaign, update local configuration,
preview, then restart. Standalone discovery has no hot reload; Phase 10 workers
add the separate DB suppression/heartbeat behavior documented below. Policy
is rechecked immediately before each connection. Identity validation checks syntax;
it does not establish contact ownership or permission to measure a target.

`docs/DISCOVERY.md` and `docs/PROTOCOL_EVIDENCE.md` specify hard scope, rate,
concurrency and time bounds and graceful stop semantics. Logs omit addresses, contacts and raw exception text. Preview output
shows requested scope intentionally. Private local manifests contain non-secret
operator metadata and scope; observations contain endpoint addresses. Keep both
under ignored `data/`; no credentials belong in any measurement setting. Graceful
stop flushes results; force-kill/power-loss recovery is not promised in this phase.

## Protocol enforcement

One port-independent greeting/HTTP attempt and at most one fresh TLS attempt share
all admission and cumulative payload budgets. Ordinary GET / only; SSH/SMTP greetings
only; no authentication, client certificates, mail, STARTTLS, crawling, redirects,
cookie reuse or compression decoding. Host is a literal target address with recorded
provenance. TLS verification is not performed so self-signed/expired peer evidence can
be retained; this is an unauthenticated observation, never an identity/trust assertion.
Certificates and response bytes are opaque, bounded base64; metadata remains hostile.
No credentials or session tokens are used as inputs. Received Set-Cookie or secret
content is not reused, logged, rendered or committed. Raw bytes may still be sensitive
inside the private ignored spool, which is why real ingestion/access/retention controls
are defined by the Phase 4 synthetic-only storage boundary. Test keys are generated ephemerally, not committed.

## Evidence and privacy

Responses are untrusted and may contain personal data, secrets, hostile scripts, or
terminal escapes. Capture only bounded necessary evidence. Do not authenticate,
enumerate private data, fetch camera streams, or crawl files. Never execute captured
content or render active HTML. Phase 9 permits only reviewed bounded inert text;
raw/hex/base64 downloads and captured resource links are not exposed.
Do not include raw response content, credentials, or full query strings in logs.

Phase 4 implements the local synthetic-only storage boundary described below.
Real captures remain prohibited; a future explicit authorization and hardened
access/redaction deployment are required to enable them. Operator opt-outs
must stop new work and define how stored evidence/search projections are removed
or restricted. Store raw sensitive evidence separately from public metadata.
Keep production credentials outside effective-config hashes and committed files.

## Offline derivation enforcement

Phase 3 consumes bounded regular local JSON/JSONL files and declarative literal
rules. It opens no sockets, executes no rule code, and never follows captured or
provenance URLs. Shared bounded syntax parsing does not decode HTML, compressed
bodies or certificate contents. Typed metadata and ports cannot override raw evidence.
Pack/row/count/nesting limits and duplicate-key rejection bound the file boundary.
Validation replays source and pack, including evidence offsets and hashes.

Derived output copies labels and source/evidence hashes/selectors, not raw payloads
or endpoint addresses. This minimizes duplication, not sensitivity: linkage hashes
and rule labels still belong in private ignored storage. Files are mode 0600,
published atomically without overwrite, and diagnostics omit validation details.
The standalone offline adapter has no retention enforcement or public redaction
interface. Phase 4 storage adds the separate controls below, without automatically
managing old spools/offline outputs. No signatures or adversarial-local-user
filesystem guarantees are supplied.
Keep original evidence private for replay; do not equate matching banners with
trusted identity, calibrated probability, physical hardware or vulnerabilities.

## Durable storage boundary (Phase 4)

`netatlas-store ingest` requires `--synthetic` and only accepts documentation-address
or literal loopback fixtures, with bounded files and explicit v1/v2 validation.
The standalone adapter is local only; no real-data override exists. Phase 10 adds
a separate authenticated worker-delivery route limited to literal-loopback fixtures. An address
allowlist is not proof that content is synthetic; operators must author the fixtures.

Raw responses/certificates are private mode-0600 blobs under mode-0700 directories.
Private JSONB envelopes can also contain sensitive peer metadata. Database access
uses a generated local SCRAM password and loopback-only published port. Credentials
stay under ignored data/, outside configuration hashes and logs. The local DB owner
is trusted; Phase 12 provides optional restricted local service roles; encryption, production OS
isolation and remote access are not provided.
CLI output is limited to counts, UUID/digests and generic errors, never captured bytes.
No field-level sanitizer is claimed: sensitive content is removed as an entire
observation with its derivations/references/projections; retained history stays exact.

Sources expire 30 days after measurement, including late arrivals. Reads reject
expired sources; explicit `expire`/`collect` commands physically remove rows and
unreferenced blobs. Run expiry at least daily and at session start; no daemon exists.
Persistent CIDR suppression immediately removes matching history and blocks new
input/replay. Minimal replay tombstones and removed-source outbox metadata last
90 days; suppression entries remain until an independently reviewed policy change.
Local consumer projections are deleted atomically and cannot resurrect via old events.

A DB suppression does not update scanner configuration or erase other files. Stop
campaigns, update `opt_out_cidrs`, remove matching spools/derived files, and handle
backup copies. Backups are private with a 7-day maximum policy; removal requests
require disposal or quarantine and current suppression reapplication before reuse.
Restores are into separate empty databases and expire old evidence before verification.
Archives are trusted operator SQL, never accepted from peers. OS/container admins
retain access, and unlink is not guaranteed forensic erasure. Exact commands,
transaction boundaries and limitations are in [STORAGE.md](docs/STORAGE.md).

## Enrichment boundary (Phase 5)

Offline enrichment never resolves names, downloads provenance URLs, measures targets
or treats geographic gaps as reasons to expand probes. Bounded datasets require exact
file checksums and explicit version/license/attribution metadata. Operators review
rights and validity windows; hashes do not authenticate publishers. Only synthetic
observations may enter the database. Natural Earth demo geography is public domain;
its documentation-IP/ASN associations are clearly fictional.

IP geography means approximate area context, never precise person/device location.
Unknown/stale mappings and missing accuracy radii remain explicit. Raw observation
network/geography fields are untouched. Dataset and result snapshots are immutable,
private and source-linked; expiry/suppression removes dependent results and unused
snapshots/places. Backups include spatial data and inherit the 7-day/quarantine policy.
Downloads/offline outputs remain separate copies. Current search consumers
check both source and dataset expiry, rather than treating historical valid results
as fresh. No public geographic interface, real-data authorization or sanitized display
is introduced. See [ENRICHMENT.md](docs/ENRICHMENT.md) for precise validation limits.

## Search boundary (Phase 6)

Local search reads only the synthetic private database. Product text indexes derived
labels, not captures, headers, certificates, cookies or arbitrary source JSON. Hits
are bounded metadata linked by source/derivation/dataset hashes; labels/addresses
remain private and untrusted. This is not field-level sanitization or permission to
enable real captures. CLI console output contains counts only; detailed output is
escaped JSON in a new private ignored file. Independently remove those output copies.

All modes check actual source expiry and persisted CIDR suppression; historical
as_of cannot resurrect removed data. Current geography additionally checks dataset
validity at query time. Direct indexes disappear with authoritative deletions in the
same transaction; replay reads live rows. The existing backup/quarantine policy
still applies. Query size, result/facet counts, offsets, text length and geographic
areas are bounded, with a 5-second statement timeout and shared local operator lock.
This Phase 6 CLI boundary adds no public access control or raw-content display;
Phase 7 local HTTP policy is specified below.
See [SEARCH.md](docs/SEARCH.md) for exact semantics and limitations.

## Application boundaries

The API and UI bind to loopback. Phase 7 admits only literal loopback socket peers,
local Host values and approved local HTTP Origins; the launcher ignores forwarded
identity headers. Stored reads require the non-secret `X-NetAtlas-Read: 1` browser
guard. No CORS, cookie credentials or public authentication is supplied. Local users
and administrators remain trusted; do not forward this service to remote users.

Search/detail/history export declared metadata only. Phase 9 inspection separately
permits reviewed protocol fields, bounded previews, certificate assertions and exact
trace selectors. Raw blobs/source envelopes and scanner contact metadata remain excluded. JSON escapes controls/non-ASCII/HTML delimiters and responses are
no-store/nosniff. Decoded labels/URLs remain hostile text, not sanitized HTML or safe
links. This does not redact arbitrary sensitive information embedded in labels,
authorize real-data ingestion, or establish comprehensive sensitive-content sanitization.

Every page rechecks source expiry and suppression. Signed cursors are short-lived,
query/route-bound and contain no cached results; deletion cannot be reversed by
continuation. Requests cannot initiate target traffic, DNS, downloads, enrichment,
arbitrary raw reads or writes. Inspection alone reconstructs a bound retained source
under the shared lock and exports its reviewed projection. One in-flight read, streamed body/time bounds, 5-second DB
statements, 10-second lock waits and 4 MiB output bounds limit local cost. Errors
omit inputs/SQL/credentials and access logs stay disabled. Phase 12 adds local restricted DB roles and resource controls; public authentication,
TLS and production process isolation remain unimplemented. See [API.md](docs/API.md).

## Geographic display boundary (Phase 8)

The local geographic explorer renders metadata as inert React text and converts
invisible controls/directional overrides to visible code-point tokens. Provenance
URLs are never active links/resources. MapLibre receives only geometry, source IDs
and controlled categories; clusters use textContent and a local worker/basemap.
No external tiles, glyphs, fonts, geocoder, telemetry or targets are requested.
The explicit operator demo seed is separate from the read API and unreachable from
UI actions. Tiny reviewed offline asset exceptions/licenses are in MAP_ASSETS.

Views hold only one result page; edits, hidden/pagehide and 60-second expiry clear
metadata, selected-place labels and map points. There is no persistent or previous-page cache. A visible
page remains read-time truth until refresh/clear, not a push-synchronized deletion
view. Every subsequent API read rechecks actual retention/suppression. Synthetic
input remains mandatory; escaping/allowlists do not sanitize embedded sensitive
content. Phase 9 adds the reviewed boundary below. No real input is authorized.

## Inspection display boundary (Phase 9)

`synthetic-preview-1` is specified in [INSPECTION.md](docs/INSPECTION.md). Inspection
requires exact endpoint/UUID/source digest, checks actual expiry and suppression
before and after projection inside the storage lock, and verifies selected derivation
identity and trace slices. Canonical evidence remains immutable; preview redaction
is ephemeral. Whole-observation removal, 30-day source retention, 90-day tombstones,
7-day backups and independently managed copies remain required.

Only complete reparsed allowlisted HTTP fields and supported unencoded UTF-8 bodies,
SSH version/software and bounded SMTP greetings can be displayed. All unreviewed
headers, SSH comments, unsupported/encoded formats and trace excerpts are withheld.
Recognized sensitive markers withhold the entire field/body before truncation.
These conservative checks cannot detect arbitrary secrets; this is not approval for
real input or public access. No raw download, hex or base64 fallback exists.

Bounded DER parsing exports subject/issuer/time/serial/algorithm assertions only;
verification remains not_performed even for parsed expired/self-signed certificates.
No extensions, resource links, trust/hostname/signature/revocation checks, AIA/OCSP/CRL
fetches or DNS. Parser warnings/errors omit peer text. All preview/control/bidi text
is inert in React, with no HTML/resource embedding or captured URL activation.
Timeline/inspection share the browser read lane and hidden/60-second clearing.

## Local worker control plane (Phase 10)

Read [DISTRIBUTED.md](docs/DISTRIBUTED.md) before operating the workers. This separate
loopback service authenticates two provisioned worker UUIDs with generated private
bearer credentials. Tokens remain outside Settings hashes, logs, PostgreSQL and backups.
Workers have no DB secret. The local OS/DB owner and authenticated worker implementation
remain trusted; bearer authentication is not a hostile-worker sandbox or public TLS.
No UI controls or read-API authentication changes. No real-input ingestion is authorized.

Enqueue requires enabled identity, --measure, --synthetic and explicit literal loopback.
Central one-use permits check pinned policy/exclusions/DB suppression for every socket,
including TLS. Global/prefix rates and socket slots are shared across workers/campaigns.
Lost grants are burned; issued attempts never automatically remeasure after failure.
Boot generations fence reordered registration; saved immutable UUID/digest results can
recover delivery-only authority. Observation/source/receipt commits share the storage lock.

Cancellation and DB suppression revoke future authority. Already-issued 250-ms permits
and active connections may precede the next heartbeat; no instantaneous remote socket
fence is claimed. Heartbeat/control failure cancels active I/O, normally within about
three seconds subject to scheduling. Existing standalone discovery still needs explicit
stop/config update; it does not consult worker leases. Phase 11 adds separate authored scheduling; see SCHEDULING.md.

A worker has one fsynced pending slot and bounded delivery retries; storage outage stops
new claims. Independently delete/quarantine pending.json/pending.stage on removal after
stopping workers; keep boot.json/credentials to preserve fencing. Offline copies cannot
receive deletion. Delivery expires after 24 hours, control metadata prunes after 90 days;
source/tombstone/backup policies remain 30/90/7 days. Restore cancels all historical
control jobs; keep the destination offline until restore and current suppression review
complete. No owner data/volumes/secrets are reset by acceptance tests.

## Reporting and response

This is currently a private research repository. Report issues privately to its
owner through an existing trusted channel. Do not post real device addresses,
captured secrets, or exploit instructions in public issues. A public security
contact and operator opt-out URL must be established before public deployment.
If a credential is accidentally committed, revoke/rotate it and remove it from
active use; merely deleting the current file does not remove Git history.

## Coverage and refresh boundary (Phase 11)

Offline planning accepts only bounded authored documentation/loopback universes.
Routed/unrouted/unknown labels and IPv6 seeds are fixture assertions, never downloaded
route truth or measurement authorization. Only explicit lab_loopback inputs can execute,
with --synthetic, --measure and enabled identity, at the exact literal loopback endpoints.
Logical shards and new refresh measurements share the original central socket permits.
The read API/UI imports no scheduler execution and has no new controls. UDP is deferred.

Schedule admission binds latest retained source identity, rejects unresolved issued
attempts and checks current suppressions under the pipeline lock. Source snapshots,
plans and schedule documents are private metadata; generated files stay ignored and
need independent removal. Control metadata, including prior-source summaries, retains
the explicit 90-day policy; raw sources remain 30 days, backups seven days.

Global stop persists across coordinator restart and cancels all existing work. Explicit
allow-new-work only reopens future admission. Suppression and matching job revocation
commit together. Restore sets global stop as well as cancelling historical jobs; keep
it offline through full verification and current suppression reapplication. DB outage
can prevent committing stop: terminate workers locally; normal heartbeat/control loss
already cancels active cooperative sockets. Existing 250-ms grants/in-flight traffic
prevent instantaneous fencing. Keep worker credentials/boot generations and separately
quarantine or delete pending copies. Exact commands/limits are in docs/SCHEDULING.md.

## Operational boundary (Phase 12)

[OPERATIONS.md](docs/OPERATIONS.md) is the deployment, credential, incident and
retention/restore runbook. Fixed-cardinality HTTP metrics and structured summaries
exclude endpoint/query/peer/operator/secret/exception values. Readiness exposes only
fixed dependency states, never connection details. Dashboard snapshots expose counts
only and never initiate measurement, reconcile authority or imply successful coverage.
The read browser guard remains non-secret and all listeners remain literal loopback.

Optional read/control DB accounts have explicit SELECT/limited DML grants and no
ownership/DDL/admin grants. They do not replace the owner or give workers DB secrets.
Same-OS-user access, DB PUBLIC privileges and cooperative workers remain trusted;
this is not production or hostile-user isolation. Credential staging/recovery preserves
owner state and worker boot generations. No automatic rotation/restart daemon exists.
Resource limits fail closed/backpressure; readiness is neither full source verification
nor proof that independent spools/backups were erased. Container logs omit statements,
parameters and ordinary errors; application access logs remain disabled.

Backup manifest 2 rejects expired/future/overlong age windows; operators must still
remove/quarantine files within seven days, sooner on removal. Legacy v1 requires
independent age review. Dumps/restores omit service ACLs and credentials; restores
cancel all historical work and set global stop before source verification, remain
offline through current suppression review, and require explicit new service grants.
Unencrypted local backups and independent offline copies remain limitations.
Cryptography is now 50.0.2 following the [dependency review](docs/DEPENDENCIES.md).
No real-input/public deployment authorization or comprehensive sanitizer is added.

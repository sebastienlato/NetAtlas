# Data contracts — schema version 2

Executable authority: `domain.py` (shared/legacy types), `evidence.py` (protocol
contracts), and `observation.py` (current envelope and version dispatch), under
`src/netatlas/`. Generate the current schema with `uv run --locked netatlas schema`.
No generated schema is committed. Models forbid extra fields, are frozen, and use
tuples for collections; future ingestion must validate untrusted envelopes and
impose a total request-size limit as well as the field bounds.

## Envelope and compatibility

Observation v2 preserves UUID, target/endpoint, scanner, effective config SHA-256,
aware start/finish timestamps, reachability outcome, optional service, network,
geography and stable error code. It adds optional `protocol_evidence`. Schema v2
is emitted by both protocol and connect-only discovery and the synthetic API/CLI
example. The API remains the existing `/api/v1/examples/observation` route; its
example body's explicit schema version is 2. This is not a new query API.

`domain.ObservationV1` preserves the previous wire contract. Use
`observation.observation_reader.validate_json(...)` for explicit discriminated v1/v2
reads. Readers reject missing/unknown schema versions, extra fields, v2 evidence
on v1, and silent coercion of v1 to v2. No historical spool is rewritten or upgraded.
The current `observation.Observation` requires version 2 when an explicit version
is supplied. Local Python imports must use this new module for the current model.

Targets retain canonical IP, campaign ID and source. Endpoint key is address,
transport and port; it is not device or ownership identity. Only `open` observations
may carry service/response evidence. Dates are aware and ordered; target and endpoint
must agree, and optional network prefixes must contain the endpoint. Collectors
emit no derived network/geographic fields; Phase 5 results are separate records.
Existing embedded fingerprint/classification
shapes remain legacy foundation placeholders. Phase 3 derives separate records;
it neither consumes those placeholders as evidence nor fills them into observations.

The original optional top-level `response` is retained for legacy-shaped synthetic
examples, but cannot coexist with `protocol_evidence`. New collectors put captures
inside exchanges only. `CapturedResponse` is canonical base64 with a 65,536-decoded-byte
ceiling, media type and conservative truncation flag. Raw bytes are never executable
content. Synthetic example `192.0.2.10` has fixed IDs/times and explicit documentation
provenance; it is neither a target nor a measured Internet service.

## ProtocolEvidence

| Field | Meaning |
| --- | --- |
| `strategy` | `greeting-http-tls-v1`, the versioned selection/interaction plan |
| `exchanges` | 1–2 ordered connection attempts, indexes starting at 1 |
| `received_bytes` | Cumulative socket payload read, including TLS records; at most 65,536 |
| `sent_bytes` | Cumulative reserved socket payload writes, including TLS; at most 16,384 |
| `retained_bytes` | Exact sum of decoded raw application captures and DER certificates; at most 65,536 and no more than received bytes |
| `termination` | finished, endpoint timeout, byte limit, connection limit, or stopped admission |

Each `Exchange` includes connection index, probe (`greeting-http`/`tls`), TCP outcome,
collection status, stable error code, `http_request_sent`, optional raw response,
HTTP/TLS/SSH/SMTP metadata, and optional ambiguous candidates. Typed application
metadata requires raw evidence. TLS metadata only belongs to the TLS attempt.
Failed connects cannot carry protocol evidence. At most one application protocol
is claimed per exchange; TLS may layer beneath it. A TCP-open observation remains
open even if its protocol handshake fails or the later connection is refused.

| Metadata | Bounded fields |
| --- | --- |
| HTTP | 1.0/1.1 version, 100–599 status, up to 32 ordered duplicate-preserving headers (name ≤256, value ≤2048), headers-complete flag, raw body offset, optional `target-ip` Host provenance |
| TLS | Negotiated version, cipher, secret bits, ALPN, up to 8 whole DER certificates in peer order, chain-truncated flag, `verification=not_performed`, null SNI |
| SSH | Identification protocol 2.0/1.99, software token and comments; full line ≤255 bytes |
| SMTP | Code 220, up to 32 printable greeting lines, `explicit-smtp-greeting` identification basis |

Metadata is still untrusted peer assertion. HTTP bodies and DER bytes are opaque;
no scripts, URLs, cookies or certificate identities are acted upon. There are no
product fingerprints, device classifications, vulnerability claims, or derived
confidence scores in collector output. A bare 220 remains `service.protocol=unknown`
with SMTP/FTP candidates. Port numbers alone never supply protocol evidence.
For limits, selection, statuses and exact accounting, see
[PROTOCOL_EVIDENCE.md](PROTOCOL_EVIDENCE.md).

## Configuration and manifests

Configuration is **version 3**, package **0.11.0**. Old explicit version-2 files fail
closed. To migrate a local file, change its version to 3, compare against
`config/default.toml`, and explicitly choose `measurement.protocol_evidence`. It
remains false by default; old partial files that omit a version retain connect-only
behavior. Config hashes change with schema/defaults and are never backfilled.

New spools use **manifest version 2** and observation schema version 2. Manifest v1
is historical data and is not modified. The v2 manifest preserves campaign UUID,
full non-secret effective settings and hash, pinned policy/registry versions/hash,
scope/ports/seed/order, lab marker, scanner/software/Python identity, timestamps,
status, completed outcome counts and exact JSONL SHA-256 (including line endings).
The preview includes the conditional interaction plan and traffic caps.

Endpoint `attempted = completed + incomplete`; completed equals row count and sum
of outcome counts. **`connection_attempted`** is the number of actual admitted socket
attempts across all endpoints, including incomplete work. It lies between attempted
and attempted times the active connection cap. The old `connect_completed` log event
name is retained for compatibility; it now means one completed endpoint observation,
not an individual protocol connection. Logs include no addresses, contacts, exception
text, headers, certificate identities or captured content.

Manifest status remains `running`, `completed`, `cancelled`, `deadline_exceeded`,
or `failed`. Graceful stops flush/fsync completed rows, retain the checksum and count
interrupted endpoints as incomplete; partial exchanges from cancelled endpoints are
not emitted as complete observations. Hard kill/disk failure/power loss can still
leave a running manifest or partial last row. Spool writes themselves do not provide database durability. Phase 4 adds a separate
synthetic-only ingest adapter; it preserves observation/campaign identities instead
of deduplicating measurements solely by raw content hash. See [STORAGE.md](STORAGE.md).

## Phase 3 derivation contracts

`derivations/models.py` defines bounded rule-pack schema **1**, derived-record schema
**1**, engine **fingerprints-1**, taxonomy **netatlas-categories-1**. These contracts
are separate from observations. A record contains source observation UUID, source
schema version and canonical SHA-256; pack ID/version/digest; engine/taxonomy version;
product/category states; stable diagnostic notes; and up to 128 candidates. Each
candidate carries rule ID/version, optional product/category, ordinal confidence,
and up to four precise byte references into original base64 captures. No raw content
or endpoint is duplicated. Source and pack snapshots are required to replay.

No random ID or processing clock appears in deterministic records. JSON defaults,
sorted keys and compact ASCII serialization define digest bytes; input lexical
formatting is excluded and arrays retain order. Operational run timestamps belong
in a later envelope. Same source/pack/engine yields identical records; changed pack
content changes its digest even if an author forgets a version bump. Unknown and
multiple product/category values are explicit. `--validate` verifies output by full
recomputation, not merely schema validation. See [FINGERPRINTS.md](FINGERPRINTS.md)
for the exact rule language, confidence semantics, taxonomy and I/O limits.

## Durable adapter (Phase 4)

Migrations 0001/0002 store original v1/v2 canonical digests and private envelope
JSONB with base64 values replaced by content hashes. `evidence_refs` preserves exact
pointers; reconstruction reinstates verified blob bytes and checks the original
source digest. This is an internal representation, not a wire-version change.
Independent pack/derivation JSONB and source/pack/engine/taxonomy keys preserve replay.
Typed endpoint/time/outcome columns support separate latest attempt/open/evidence
pointers. Ingestion, outbox, expiry and deletion semantics are defined in STORAGE.

## Phase 5 enrichment contracts

`enrichment/models.py` defines dataset/result schema **1**, engine **enrichment-1**.
Results link source UUID/schema/hash, dataset ID/version/canonical hash, explicit
UTC evaluation time, source attribution/license/version/checksum, ASN/city prefix
matches and stable place IDs. Unknown/stale/missing-radius semantics are explicit.
Optional observation network/geography fields remain legacy placeholders and are
neither used as enrichment evidence nor rewritten. See [ENRICHMENT.md](ENRICHMENT.md).

Migration **0003** persists independent bundle snapshots, gazetteer places and
source-linked results. WGS84 geography points support metre distances; split geometry
MultiPolygons preserve approximate boundaries. Removal cascades with observations;
shared datasets survive until unused. `verify` additionally reports `enrichments`
and validates the spatial projections as well as canonical replay. No query API
contract is introduced. Dataset validity is evaluated at the recorded clock;
current searches must check expiry again at their own query clock.

## Phase 6 local query contract

`search/models.py` defines query schema 1 independently of observation/enrichment
contracts. Migration 0004 adds indexes without modifying immutable documents.
`search/service.py` returns bounded private metadata and exact counts with resolved
query/source/version provenance. Current/history selection, actual retention versus
as_of clocks, dataset validity, text scope, geography uncertainty and facet/count
semantics are specified in [SEARCH.md](SEARCH.md). The local contract remains private;
Phase 7 adds separate typed transport responses, cursors and access/cost policy below.

## Phase 7 HTTP contract

Package 0.8.0 adds HTTP schema 1 without changing stored/domain contracts or migration
0004. `read_api/models.py` explicitly selects metadata fields; private search
dictionaries and source envelopes are not wire models. Query-bound signed keysets,
exact counts/uncertainty, generic errors and OpenAPI-derived TypeScript types are
documented in [API.md](API.md). No raw evidence is exposed. Phase 8 adds the geographic UI without changing
these schemas; package 0.9.0 updates only health/metadata and its generated digest.

## Phase 9 inspection projection

`inspection/models.py` defines the additive HTTP schema-1 inspection request/response
and versioned synthetic-preview-1 contract. Canonical source/derivation/enrichment
schemas remain unchanged. Exact measurement/derivation identities, checked selectors,
explicit preview/parse/truncation states and certificate verification=not_performed
are detailed in [INSPECTION.md](INSPECTION.md). No raw source serialization is exposed.

## Phase 10 control compatibility

Control envelope 1 and migration 0005 are independent of these contracts. The separate
authenticated loopback coordinator has no UI/read routes. Worker delivery preserves
original observation v2 UUID/digest and uses the existing storage lock and retention
policy; legacy v1 reads/ingestion remain unchanged. No source/read schema changed.
See [DISTRIBUTED.md](DISTRIBUTED.md).

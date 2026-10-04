# Data contracts — schema version 1

Executable authority: `src/netatlas/domain.py`. Generate JSON Schema with
`uv run --locked netatlas schema`. There is no independently maintained generated
schema file to drift. Models forbid unknown fields and field reassignment; tuple
collections prevent in-place mutation of nested lists. Validation is required at
every future ingest boundary. JSON is the interchange format; Python types are not
a cross-process serialization mechanism.

| Concept | Fields and meaning |
| --- | --- |
| Target | Canonical IP, source, campaign ID; selection/provenance rather than proof of eligibility |
| Endpoint | IP, port 1–65535, TCP/UDP transport; normalized key groups measurements |
| ScannerNode | Stable node ID, software version, optional vantage; not a machine secret/hostname |
| Observation | Schema version, UUID, target/endpoint, scanner, effective config digest, aware start/end timestamps, outcome, optional response/service/network/geo/error code |
| Protocol / Service | Identified application protocol, optional extension name, TLS layering, fingerprints, classifications; transport is separate |
| CapturedResponse | Canonical base64 bytes, media type, truncation flag; at most 65,536 decoded bytes per response |
| Fingerprint | Versioned rule, vendor/product/version, confidence 0–1, evidence references |
| Classification | Category, confidence, rule ID, evidence references; multiple candidates can coexist |
| Network | CIDR, optional ASN/organization, dataset source/version |
| GeoLocation | Optional country/region/city/coordinate pair/accuracy radius, dataset source/version |

The synthetic fixture uses reserved documentation address `192.0.2.10`, a fixed
UUID/time, and `synthetic-documentation-fixture` provenance. It is never a discovery
target or an assertion about an actual service. No precise location is invented.

Dates must be timezone-aware and ordered. Producers should emit UTC; offsets are
accepted and compared as instants. Source observation time is distinct from future
ingestion/derivation time, which storage will add. Endpoint and target addresses
must match; network prefixes must contain their endpoint. Only open observations
may carry response/service evidence. Timeout and error records describe attempts,
not definitive disappearance. Fields may remain unknown rather than inferred from
port numbers or IP address alone.

Version 1 is an early extensible foundation, not a permanent all-protocol schema.
Later protocol collectors will introduce typed metadata (headers, certificate chains,
greetings), multiple bounded exchanges, and evidence selectors through explicit
schema evolution and tests. Future derived records need their own version/time
and source observation IDs. Introducing incompatible fields requires a schema
version increment with documented ingestion compatibility/migration behavior;
`extra=forbid` deliberately rejects silent unknown additions.

Persistence will define ingestion IDs, content hashes, last-seen/current-service
projections, and partitioning. The observation UUID is ingestion identity; a raw
content hash alone must never collapse distinct timestamps/campaign observations.
IP+port is a service endpoint, not a reliable physical-device or ownership identity.
The model's 64 KiB raw cap does not alone bound the entire future API request;
ingestion must also enforce total envelope and collection-size limits.

## Phase 1 discovery output

Observation schema remains **1**. TCP discovery supplies no response or service.
`open` means a completed TCP connect; `closed` with `connection_refused` means an
explicit refusal. `timeout`/`connect_timeout` is ambiguous. Other failures use
`error` and stable `network_unreachable`, `local_permission_denied`, or `socket_error`
codes; raw exception strings are never persisted. Interrupted attempts emit no
observation and are counted as incomplete in their campaign manifest.

Each JSONL row links via target campaign UUID and effective-config SHA-256 to a
**manifest version 1** in the same directory. The manifest records observation schema
version, **config version 2**, full effective non-secret configuration, config hash,
policy and registry versions/hash, scope/ports/seed/order, lab marker, scanner ID,
software/Python versions, start/end times, final state and attempt/outcome counts.
Its final SHA-256 covers the exact UTF-8 JSONL bytes including line endings. Random
UUIDs identify campaigns and observations; rerunning a scope produces new identities.

Manifest `status`: `running`, `completed`, `cancelled`, `deadline_exceeded`, `failed`.
Final `attempted = completed + incomplete`; `completed` equals the JSONL row count
and sum of outcome counts. Denied targets are preview decisions, not attempts.
Reproduction means the same scope, eligibility and admission order under the pinned
runtime/policy/config; it does not imply identical network outcomes, completion
order, timestamps or IDs. See `docs/DISCOVERY.md` for file/cancellation limitations.

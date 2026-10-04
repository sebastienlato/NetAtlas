# Phase 3 — offline fingerprints and categories

Package 0.4.0 adds deterministic derivations without changing config v3,
observation/manifest v2, or discovery traffic. No network, database, ingestion,
search, geography, vulnerability assessment or public evidence UI is added.

## Run offline

Inspect the bundled `netatlas-core` pack (1.0.0):

```sh
uv run --locked netatlas fingerprint --inspect
```

Apply it to an existing local observation JSONL, then verify by replay:

```sh
uv run --locked netatlas fingerprint --input data/CAMPAIGN/observations.jsonl --output data/derived.jsonl
uv run --locked netatlas fingerprint --input data/CAMPAIGN/observations.jsonl --validate data/derived.jsonl
```

These commands never measure targets and need no operator identity, credential,
config file or network service. `--pack PATH` selects a local JSON pack for all
three modes. Input is one observation object per line, with explicit schema version.
Outputs must be new files under the working directory's ignored `data/`; an existing
nested parent must already exist. `data/` is created privately if absent. Final
symlinks/non-regular input files, a symlinked data root, and output paths resolving
outside data are rejected. No overwrite is permitted. Treat an existing parent as
operator-managed private storage. This is not protection against an adversarial
local account racing directory replacements.

A standalone synthetic smoke example (the result is intentionally unknown):

```sh
mkdir -p data
uv run --locked netatlas example | uv run --locked python -c 'import json,sys; print(json.dumps(json.load(sys.stdin)))' > data/example.jsonl
uv run --locked netatlas fingerprint --input data/example.jsonl --output data/example-derived.jsonl
uv run --locked netatlas fingerprint --input data/example.jsonl --validate data/example-derived.jsonl
```

Choose fresh output names when repeating. The apply/validate stdout contains only
validity, row count and pack digest. Errors return exit 2 with a generic message;
no paths, observation bytes, peer names or validation exception payloads are logged.
Inspection prints escaped rule JSON, never opens provenance URLs or captured links.
Output is mode 0600, staged in a temporary file, fsynced, then published with an
atomic no-clobber hard link. Ordinary failures remove temporary output and leave no
partial final file. No crash recovery or power-loss directory durability is claimed.
Input sources are never rewritten. Duplicates remain separate ordered rows; ingestion
and deduplication belong to Phase 4.

## Rule language and provenance

`derivations/models.py` defines rule-pack schema 1 and derivation schema 1.
Rules are declarative JSON: stable `rule_id`, semantic `version` (X.Y.Z), printable
ASCII description/provenance, optional product and category, confidence, and 1–4
AND conditions. At least one of product/category is required; unknown cannot be a
positive rule. Each condition has a fixed selector, literal value and one operator:

| Selector | Input and constraints |
| --- | --- |
| `http.server` | Trimmed Server value from a syntactically valid, complete header block; case-insensitive header name, case-sensitive value; duplicates retained |
| `http.body` | First 8192 bytes of the declared/available body; no informational/204/304 body; bytes beyond Content-Length excluded; skip all Content-Encoding/Transfer-Encoding bodies |
| `ssh.software` | Software token from a complete SSH 2.0/1.99 identification line; comments excluded |
| `smtp.greeting` | Each complete explicit SMTP greeting line's text after its first word (hostname); bare 220 remains ambiguous |

Operators are `equals`, `prefix`, `contains`, and `word`, all case-sensitive ASCII
literal byte operations. `word` uses ASCII letters/digits/underscore/hyphen as word
characters. No user-supplied regex, scripting, templates, imports, arbitrary field
paths, network queries, HTML parsing, decoding/decompression, or certificate parsing.
`equals` requires the complete selected field; `word` cannot infer a right boundary
at the end of an incomplete body. Present substrings/prefixes can support a candidate
in a truncated body. Missing/truncated evidence never supplies an absence predicate.

All conditions must match the same capture/application protocol. For duplicates or
repeated substrings, select the first satisfying field and first match in byte order
for each condition. Emit at most one candidate per rule per capture. Preserve all
matching rules and both captures; do not pick an arbitrary winner. Rule evaluation
order is sorted by ID, captures remain in original order, and notes are sorted.

The bundled pack has four authored assertion rules for three products:

- Exact `nginx` or `nginx/` prefix in Server, from the upstream
  [nginx header-filter source](https://github.com/nginx/nginx/blob/master/src/http/ngx_http_header_filter_module.c).
- `OpenSSH_` software prefix, from upstream
  [OpenSSH version definitions](https://github.com/openssh/openssh-portable/blob/master/version.h).
- `Postfix` word after the hostname in an explicit SMTP greeting, based on
  [Postfix smtpd_banner documentation](https://www.postfix.org/postconf.5.html#smtpd_banner).

References were reviewed 2026-10-04; they are attribution, never runtime downloads.
Only small authored literal patterns are included, not copied upstream source or a
commercial fingerprint database. Version strings are not parsed; these rules do not
infer operating systems, firmware versions, hardware, ownership or vulnerabilities.

Pack ID/version, taxonomy version, author/provenance text and exact normalized pack
SHA-256 identify a run. Keep a pack snapshot for later replay. Increment a rule's
version when its meaning changes, and the pack version for any published pack change;
never recycle an ID for a different meaning. The digest distinguishes accidental
same-version edits too. A checksum detects differences, not authorship or trust.

## Confidence and uncertainty

`asserted` means at least one literal marker matched. `corroborated` requires at
least two distinct evidence selectors in the same rule/capture. Both fields remain
controlled by the same peer, so corroboration is not independent verification.
These are ordinal evidence descriptions, not numerical probabilities, calibrated
accuracy or authenticated identity. No combined score or winning candidate is invented.

Product and category are independent optional outputs. Each dimension reports
`unknown`, `single`, or `multiple` based on distinct output values. Empty candidates
plus `no_rule_match` means insufficient supported evidence, not absence of a product.
Multiple values can be conflicting alternatives or coexisting service roles; retain
all candidates and `multiple_products` / `multiple_categories` notes for inspection.
No rule infers a category merely from HTTP, TLS, SSH, SMTP or a port number.

## Taxonomy: netatlas-categories-1

These stable IDs include service roles and possible device classes. They are not
mutually exclusive and never identify one physical device behind an address.

| ID | Meaning | Bundled core support |
| --- | --- | --- |
| `unknown` | Insufficient category evidence; represented by category_state unknown | Default result, never positive rule |
| `web_server` | Web-serving software role, possibly a proxy or embedded service | nginx assertion only |
| `camera_nvr` | Camera or network video recorder appliance | Unknown; synthetic engine coverage only |
| `router` | Routing/network appliance role | Unknown; synthetic engine coverage only |
| `nas` | Network-attached storage appliance | Unknown; synthetic engine coverage only |
| `printer` | Network printer or print appliance | Unknown; synthetic engine coverage only |
| `ssh_server` | Remote-login service role, not hardware/OS identity | OpenSSH assertion only |
| `vpn_appliance` | VPN gateway/appliance role | Unknown; synthetic engine coverage only |
| `mail_server` | Mail-service software role | Postfix assertion only |
| `database` | Database-serving role | Unknown; synthetic engine coverage only |
| `iot` | Other connected embedded-device class | Unknown; synthetic engine coverage only |
| `industrial` | Industrial monitoring/control device class | Unknown; synthetic engine coverage only |

Future category changes need a new taxonomy version and explicit mapping, not a
silent reinterpretation. A web role does not exclude a router/camera/NAS. Supporting
those devices needs reviewed evidence/rules within existing probe limits; this phase
adds no device commands, streams, database enumeration or industrial interactions.

## Records, compatibility and precise evidence

The pure engine accepts validated v1 and v2 observations. It reparses raw response
bytes using the shared I/O-free `protocol_syntax.py`; collector-facing exports stay
in `collectors/protocols.py`. That parser was moved without behavior changes.
It ignores typed metadata, `service` declarations, existing foundation fingerprints,
ports, TLS certificates and network/geographic fields as detection inputs. Reparsed
raw syntax prevents forged metadata from becoming a product assertion; raw bytes
themselves are still forgeable. v1 and v2 legacy top-level responses work; new v2
exchange captures work. v1 adds a `legacy_v1` note and is never silently upgraded.

Invalid envelope/base64/unknown schema versions fail the file; valid envelopes with
missing, unknown or malformed protocol bytes emit honest unknowns and stable notes.
HTTP incomplete/malformed headers supply no fields; complete headers can still match
when the body is truncated. TLS-only evidence supplies no product/category candidate.
Unknown protocols and gaps never trigger new network activity.

Every derived row links the original UUID, source schema version and normalized
observation SHA-256, plus engine version `fingerprints-1`, taxonomy and pack provenance.
Each candidate carries rule ID/version, optional product/category, confidence and
one reference per condition. A reference contains a JSON pointer to the source's
base64 field, zero-based decoded-byte `[start,end)` range, selector, condition index
and SHA-256 of exactly those bytes. No response excerpt, address, URL, cookie or
certificate is copied into derived records. Retain original source and pack securely
when inspection/replay is needed; selectors/hashes do not make source data public-safe.

Canonical bytes are validated Pydantic models dumped in JSON mode with defaults,
sorted object keys, compact separators and ASCII escaping. Source/pack digests hash
those bytes, not input whitespace/key order. Arrays remain ordered. The input JSONL
file itself is not normalized or rewritten. Deterministic output has no wall-clock
processing time or random ID; operational run timestamps belong to a future separate
run/ingestion envelope. A derivation identity can use source ID + source digest +
engine/taxonomy/pack digest. Exact input/pack yields byte-identical records. Validation
recomputes every row and compares all fields, offsets, hashes, labels and row order;
schema validation alone is not proof that evidence supports a record.

## Limits and synthetic validation

| Resource | Hard limit |
| --- | --- |
| Pack file / rules / conditions per rule | 128 KiB / 64 / 4 |
| Rule label or literal / ID / semantic version | 512 / 64 / 32 ASCII characters |
| Observation JSONL / rows / individual line | 16 MiB / 1024 / 1 MiB |
| JSON nesting | 32; duplicate keys rejected |
| Source captures | Existing observation limits: 2 exchanges, 65,536 retained bytes total |
| HTTP body inspected per capture | 8192 bytes |
| Candidates per observation | 128; 4 evidence references each |
| Derived JSONL | 32 MiB, same 1024 row and 1 MiB line limits |

Processing streams one bounded row at a time. Fixed syntax-parser regexes operate
only on bounded input; rules cannot supply regexes. Larger campaigns must be split
explicitly offline; this CLI is not the durable ingestion pipeline. macOS/Linux
regular files are supported, matching existing spool scope.

`tests/fixtures/fingerprints/corpus.json` contains 47 labeled synthetic cases with
expected rule/category outputs and truth notes. Test construction uses documentation
address 192.0.2.10 on an unconventional port. The separate `synthetic-pack.json`
uses fictional NetAtlasFixture markers for all 11 positive taxonomy IDs; it is
never selected by default and establishes engine coverage only. Cases cover positives,
negatives, ambiguity, conflicting classes, legacy input, missing/malformed/truncated
bytes, encoding, body-only decoys, hostname/comment decoys and hostile HTML.
A deliberately spoofed nginx banner still yields an asserted nginx candidate: a
known physical-identity false positive that cannot be solved by banner matching.
All expected behavior is tested; no real-world precision/recall estimate is claimed.

Additional tests cover trace slices/digests, metadata tampering, independent outputs,
cross-exchange isolation, body bounds, version/hash changes and replay, duplicate
headers, untrusted rules/JSON/file types/resource limits, no networking, private
atomic output, no-clobber and redacted CLI failures. See PROJECT_STATE for actual
check counts and final validation. No real observations or generated outputs are
committed, and no Internet measurement was performed.

# Phase 9 — service and evidence inspection

Package **0.10.0**, HTTP schema **1**, preview policy **synthetic-preview-1**.
Observation/derivation/enrichment schemas and Alembic **0004** remain unchanged.
Synthetic-only local ingestion is mandatory. No public service, raw download,
measurement, DNS, certificate validation, derivation execution or real-data permission
is introduced. The geographic explorer and its offline map remain available.

## Read contract and binding

`POST /api/v1/endpoints/{address}/{transport}/{port}/inspection` accepts:

```json
{"schema_version":1,"query":{"observation_id":"00000000-0000-0000-0000-000000000001","source_sha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","derivation_id":null}}
```

These are example identities, not an existing record. Take the exact source and
optional derivation identities from a current search/detail/history hit. The UUID,
canonical source digest and literal endpoint must all match. A requested derivation
must belong to that same source/digest and match its full canonical result hash.
Null means no derivation selected, not a request to pick an arbitrary newest pack.
Wrong source, endpoint, digest or derivation; missing, expired, removed or suppressed
records all yield generic 404. Malformed requests give 422; storage/blob integrity
failures give generic 503. No arbitrary pointer, path, URL or blob hash read is accepted.
There is no inspection cursor or independent preview/certificate download endpoint.

`storage/inspection.py` checks actual expiry and persistent CIDR suppression before
reconstructing the source with the existing verified blob adapter. Inspection requires
an existing private non-symlink blob directory and never creates it. Read, reconstruction,
trace checks and projection hold the shared transaction/advisory lock. A second
eligibility check after projection rejects expiry crossed during processing. Suppression
before physical cleanup already denies access. Original envelopes and blob content
are never returned or rewritten. Private scanner/contact metadata is omitted.

The response links measurement UUID, canonical digest, original schema, endpoint,
start/finish, outcome, expiry and actual retention-check time. Exchanges preserve
connection/probe/TCP/collection outcomes, protocol alternatives, request-sent marker
and independently bounded TLS assertions. Application fields are reparsed from raw
bytes using the existing pure syntax parser, not trusted from copied peer metadata.
Legacy v1/v2 top-level captures have a separate `legacy_capture`; exchange evidence
is never blended with another observation or connection.

Exact selected fingerprint results preserve all candidates, ordinal confidence,
product/category ambiguity, rule ID/version, pack ID/version/digest, engine/taxonomy,
source UUID/schema/digest and notes. Each reference retains its source JSON pointer,
condition index, selector, decoded-byte [start,end) and SHA-256. Every pointer/range/
slice hash is checked against the reconstructed source; mismatch fails the entire
inspection. This verifies linkage/integrity, not the rule's real-world truth. No
fingerprint rules are rerun by a request. Trace excerpts are withheld, so a body
rule cannot bypass preview policy. Preview offsets are not canonical byte offsets.
Enrichment identity and dataset provenance remain on the source's search/timeline
card; inspection does not select or synthesize another enrichment.

## Preview policy (version 1)

Bounds below are fixed rather than caller configurable. Changing semantics requires
policy version review. Sanitized display is an ephemeral projection separate from
immutable source truth, not a replacement evidence record or anonymized export.

| Item | Policy |
| --- | --- |
| Source | Existing 65,536 retained bytes total, at most two exchanges, eight certificates per TLS exchange; no enlargement of collection. |
| Text | Strict UTF-8 only. Body/greeting preview at most 2,048 original bytes; scalar fields at most 256 original bytes, stopping at a complete UTF-8 character. |
| Controls | Cc/Cf/Zl/Zp become visible `[U+XXXX]` tokens, including newlines, NUL, escape and bidi controls. Rendered text bounded to 16,384 characters per preview. |
| States | `text`, `redacted`, `unsupported`, `empty`; original/shown byte counts and display truncation remain explicit. Capture truncation is separate. |
| HTTP fields | Reparsed complete, nonmalformed headers only. Version/status plus ordered duplicate Server, Content-Type, Content-Length values; all other headers withheld, names/values omitted, count retained. At most 34 fields. |
| HTTP body | Only one Content-Type declaring text/plain or text/html, optionally UTF-8 charset. Content-Length/no-body status bounds honored. Any Content-Encoding or Transfer-Encoding, missing/duplicate/unreviewed type, malformed/incomplete headers or invalid UTF-8 means no body preview. |
| SSH | Version/software only; comments and preambles withheld. No raw identification-line fallback. |
| SMTP | Reply code plus bounded greeting text, subject to whole-value redaction. |
| Other formats | Unsupported/binary/JSON/XML/images/media/encoded bodies have no raw, hex or base64 fallback. No HTML/entity/chunk/compression decoding. |
| Certificates | DER parse only for whole captures; explicitly truncated certificates are not parsed. Six bounded assertion fields, SHA-256, byte size and parse state; no raw bytes, extensions, SAN collections or resource URLs. |

Before display truncation, the **entire candidate field or body** is checked for
case-insensitive sensitive markers: cookie, authorization/authenticate, bearer/basic,
password/passwd, secret, token, API key, session, credential, private key/PEM begin
and URL userinfo. NFKC normalization and removal of Cc/Cf characters additionally
catch basic control-separated/fullwidth forms. A match withholds the entire value;
no partial secret is retained in the preview. Unreviewed headers (including cookies,
authorization, authentication challenges, redirects and custom fields) are always
withheld independent of marker recognition. Redaction precedes truncation so a
marker after byte 2,048 still withholds the prefix. No sensitive values enter logs.

This intentionally conservative marker filter has false positives and cannot detect
arbitrary sensitive content, encodings, secret values without markers or all obfuscation.
Derived labels/provenance also remain untrusted. **No comprehensive automated sensitive-
content sanitization is claimed.** Only authored synthetic content is authorized.
Sensitive original content still requires the existing whole-observation removal
and separate handling of spools, outputs and backups. Never edit canonical evidence
in place to make it look sanitized. HTTP escaping is not anonymization.

## Certificate interpretation

The locked `cryptography` **48.0.1** dependency provides local DER parsing. It is
used only through [documented certificate parsing/accessors](https://cryptography.io/en/latest/x509/reference/),
not verification, trust stores or network APIs. Subject, issuer, serial, not-before,
not-after and signature algorithm OID are parsed assertions. DER parse failure,
unsupported algorithm, source truncation, field display truncation, and TLS chain
truncation are distinct. Parser warnings become generic parse failures, never
content-bearing logs. Parse success is **not** signature, hostname, validity,
revocation or trusted-identity validation. `verification=not_performed` is preserved.
Expired/self-signed fixture certificates can parse successfully. Extensions are not
traversed or displayed; AIA/OCSP/CRL/certificate links are never fetched or resolved.

## Browser behavior and inherited policy

Search cards offer exact observation inspection and an endpoint timeline. Timeline
uses the existing history route with selection=attempt, including failed/empty attempts,
20 rows per page and original-query continuation. It keeps only one page. Inspecting
an older evidence row remains explicit; a current negative attempt never supplies
an older row's protocol/category fields. Timeline cards retain enrichment linkage.

Inspection/timeline/search/places share one cancellable read lane and generation
guard. Switching views drops the previous result; no persistent/back-page cache,
automatic retry or download exists. Hidden/pagehide, filter changes, closing a view
and 60-second display expiry clear inspection/timeline data and abort pending work.
Every fresh inspection rechecks retained truth; a displayed view is not a push removal
notification. Abort may leave server work finishing; 429 requires explicit retry.

Every peer string is inert React text; captured HTML is shown only as literal text
inside a bounded preformatted area. No injected HTML, resource elements, captured
URL links, iframe, image/media embedding, redirect, scripts or external resources.
Controls are visible both server-side and in the UI. Keyboard focus moves after React commits the
new view's heading, native controls support the complete workflow, and long hashes/
text wrap on small screens. The original geographic/list view remains accessible.

The same loopback socket peer/Host/Origin guard, X-NetAtlas-Read header, omitted
credentials, no CORS/forwarded trust/access logs, same-origin client, 16-KiB body,
five-second body/SQL limits, ten-second lock wait, one in-flight read, four-MiB output
limit, escaped no-store/nosniff JSON and generic errors cover this route. Types are
generated from OpenAPI and checked for drift; they are not runtime JSON validation.

## Validation

`make check-db COMPOSE=docker-compose` passed with 312 Python tests, 26 web tests
and five production Chromium tests, including desktop/mobile Axe with no violations.
Screenshots were inspected; no comprehensive assistive-technology audit is claimed.
The suite includes offline/loopback, real PostgreSQL and accessibility acceptance. New tests cover sensitive markers
beyond the preview window; malformed/large/encoded/binary/duplicate-header inputs;
truncated/invalid/expired synthetic certificates; visible controls; exact trace
slice integrity; immutable replay; endpoint/source/digest/derivation mismatches;
v1/IPv6/negative attempts; suppression before cleanup; removal and actual expiry;
expiry during projection; blob errors; original timeline continuation; late cancelled
responses; hidden/60-second display clearing; real stored hostile HTML and certificate
assertions; zero external browser requests and desktop/mobile Axe checks.

The browser fixture adds one authored TLS observation to its disposable database,
with an ephemeral certificate/key created in memory. It never changes the operator
seed/database or commits generated keys, captures or browser artifacts. No Internet
measurement, real input, release, distributed workers or Phase 10 work is included.

# Phase 2 protocol evidence

This is bounded protocol recognition, not product fingerprinting, device
classification or vulnerability detection. No Internet campaign has been run.
All validation uses synthetic data and explicit loopback peers.

## Enable and preview

The CLI remains dry-run by default. Copy `config/default.toml` to ignored
`config/local.toml`, set `measurement.protocol_evidence = true`, and use the same
explicit scope/port flags described in [DISCOVERY.md](DISCOVERY.md). Measurement
still requires enabled operator identity **and** `--measure`. Without the protocol
opt-in, discovery only connects and closes, preserving Phase 1 behavior.

```sh
uv run --locked netatlas --config config/local.toml discover --lab-loopback --target 127.0.0.1 --port 8080
```

This preview opens no socket or spool. It includes strategy, conditional steps,
maximum connections per endpoint and campaign, sent/received/retained payload caps,
all rate/time settings, and config/policy hashes. A single synthetic fixture such as
`python -m http.server` on explicit loopback can be measured using `--measure` after
reviewing that preview. Do not substitute public services for implementation tests.

## Selection and traffic cost

`greeting-http-tls-v1` uses the same plan on **every port**:

1. Admit one TCP connection through the shared global/per-prefix pacer and policy
   check. Listen up to the greeting timeout for the first application bytes. Once
   any arrive, collect a bounded greeting without writing to it. Recognize strict
   HTTP/1.0–1.1 response syntax, SSH 2.0/1.99 identification, or SMTP 220 greeting
   syntax with an explicit SMTP/ESMTP token in text after the greeting's first word.
   A bare 220 (also used by FTP) stays ambiguous, with SMTP and FTP candidates.
   Unknown/binary/malformed greetings remain unknown; they trigger no active probe.
2. If the peer remains silent, send exactly one `GET / HTTP/1.1`, with literal
   target-IP-and-port Host, configured research User-Agent, and `Connection: close`.
   The same connection handles the response. No cookies, authentication, redirects,
   link/resource loading, compression decoding, URL inference or further request.
3. Only if the first connection was open, and its HTTP attempt (or immediate EOF)
   provided no recognizable protocol/candidates, admit one fresh TLS connection.
   Recheck eligibility after pacing, immediately before dialing. Collect one TLS
   handshake, then apply the same greeting/one-GET behavior inside that connection.
   Never retry or downgrade. A recognized first response ends selection even if
   malformed/incomplete. A byte cap ends selection. A first failed TCP connect ends
   selection. Configuring one connection omits the TLS attempt entirely.

Maximum cost is **two TCP connections per eligible endpoint**, not a connect-only
scan plus two more. Maximum HTTP requests is two (one plaintext and one encrypted);
maximum TLS handshakes is one. SSH and SMTP greeting collection sends **no protocol
commands**, client identification, key exchange, AUTH, EHLO, STARTTLS or mail. The
TLS handshake itself may exchange several records; there is no client certificate.
ALPN offers only `http/1.1`. No DNS, SNI, supplied hostnames or virtual-host enumeration
are supported. Host provenance is `target-ip` only when an HTTP request was sent.

For E eligible endpoints and C configured connections (1–2), planned connections
are at most E×C (hard scope maximum 32,768). Each endpoint shares a single cumulative
receive budget, send budget and retained-evidence budget across both connections;
there is no multiplier per collector. Therefore campaign payload read/send/retention
ceilings are E times their respective per-endpoint caps. The campaign deadline,
policy denials and early recognition commonly reduce actual traffic. The manifest
separates endpoint attempts from actual connection attempts, including interrupted
ones. Concurrent sockets never exceed the configured worker count.

## Bounds

| Control | Default | Hard maximum |
| --- | --- | --- |
| Connections per endpoint (protocol mode) | 2 | 2 |
| First-byte greeting wait, within interaction deadline | 0.5 s | 5 s |
| TCP connect deadline, each connection | 3 s | 30 s |
| Whole interaction deadline, each connection, including TLS and greeting wait | 5 s | 60 s |
| Endpoint deadline, starting at first admission | 15 s | 120 s |
| Campaign deadline, including all admission/queue waits | 300 s | 3600 s |
| Cumulative socket payload read, including TLS records | 65,536 B | 65,536 B |
| Cumulative socket payload sent, including TLS records | 8,192 B | 16,384 B |
| Cumulative retained raw application bytes plus DER certificates | receive setting | 65,536 B |
| HTTP header prefix / fields / name / value | 8192 B / 32 / 256 B / 2048 B | same |
| SSH identification / preceding lines | 255 B / 8 | same |
| SMTP greeting line / lines | 512 B / 32 | same |
| TLS certificates retained, in peer-supplied order | 8 | 8 |

The endpoint deadline includes **additional** connection admission waits, but not
waiting for its first admission. This avoids silently dropping queued endpoints
under conservative pacing. Timeout of a later admission leaves completed exchange
status intact and marks endpoint termination. Interaction timeouts are whole-operation
deadlines, not reset by a trickling peer. All configured time limits are finite.

Raw nonblocking sockets and `SSLObject`/`MemoryBIO` keep socket reads/writes explicitly
accounted, including encrypted handshake records. No asyncio reader prefetch or
TLS transport can bypass these caps. Read caps apply to bytes consumed by NetAtlas;
TCP/IP overhead, kernel buffers, retransmits and bytes a peer sends after closure
are not measurable/bounded by these application counters. Send bytes are reserved
before sending, so interrupted sends may conservatively overcount. TLS shutdown
closes the owned socket directly; it does not send an unbudgeted close-notify.

TLS certificate DER and application data share retention capacity; a certificate
is retained whole or omitted with `chain_truncated`. Raw TLS ciphertext is not
retained. All raw application/certificate evidence uses canonical base64. Typed
header/greeting strings are bounded but remain hostile data, never safe HTML/text
for direct terminal display. `response.truncated` conservatively means collection
may have stopped before further bytes; only a complete recognized exchange clears it.
Metadata may remain useful when a body/deadline truncates the exchange.

## Outcomes and limitations

TCP reachability and protocol results are separate. Any established connection
makes the endpoint observation `open`, including failed TLS, malformed responses,
interaction timeout or a refused second connection. When no connection established,
Phase 1 refusal/timeout/error semantics remain. Stable error codes omit raw exception
text. Each exchange records its probe, TCP outcome, HTTP-request marker, protocol
metadata/candidates, optional raw bytes, status and stable error code.

Exchange statuses: `complete`, `unknown`, `ambiguous`, `malformed`, `eof`,
`interaction_timeout`, `endpoint_timeout`, `byte_limit`, `transport_error`,
`tls_error`, `connect_failed`. Complete refers to collected greeting/response framing,
not a full SSH/SMTP session or application correctness. Endpoint termination is
`finished`, `endpoint_timeout`, `byte_limit`, `connection_limit`, or
`admission_stopped`. A timeout never means a service is closed.

TLS metadata contains negotiated version, cipher/secret bits, ALPN and bounded
unverified DER chain. Validation is **not performed**, including hostname, trust,
time validity, revocation and identity ownership. Self-signed/expired certificates
are preserved when the handshake succeeds. OpenSSL security/protocol defaults can
reject other invalid/obsolete peers before certificate extraction; those remain
TCP-open with TLS-error/timeout evidence, not invented certificates or a trust claim.
No separate certificate verification connection or external OCSP/AIA fetch occurs.

Coverage is deliberately incomplete: no SSH 1.x, SMTP without an explicit token,
STARTTLS, HTTP/2 or HTTP/3, redirect targets, named virtual hosts, authentication,
UDP, retries, or legacy TLS downgrade. An informational HTTP response is the captured
response; there is no subsequent final-response walk. Transfer/content encodings are
retained as raw bytes without chunk decoding/decompression; for responses without a
Content-Length, EOF completes capture, otherwise time/byte bounds apply. Greeting
and status syntax are assertions by the peer, not proof of honest server identity.
A slow greeting can miss the passive window and receive a harmless HTTP request.

Cancellation stops new admission, closes sockets, flushes completed endpoint
observations and fsyncs/finalizes the manifest. Interrupted endpoint attempts do not
emit fabricated timeout rows: they are incomplete in the manifest, while all their
connection starts remain counted. See [DISCOVERY.md](DISCOVERY.md) for the retained
single-spool lock and crash/power-loss limitations.

## Implementation and validation

`protocol_syntax.py` defines the shared I/O-free `Collector` interface and HTTP/SSH/SMTP
parsers; `collectors/protocols.py` preserves the collector-facing exports. `collectors/tls.py` adapts the active TLS handshake into typed metadata.
`collectors/io.py` owns bounded payload I/O; `collectors/runner.py` selects the plan
using discovery's admission callback. None depend on storage or the API. Domain
contracts in `evidence.py`/`observation.py` have no I/O. `discovery/engine.py` alone
coordinates policy, shared budgets, cancellation and spooling.

Tests cover fragmented greetings and response syntax, unconventional ports, bare-220
ambiguity, hostile/binary/oversized responses, duplicate headers, IPv6 and no DNS,
self-signed and expired certificates, TLS/HTTPS and TLS-wrapped greetings, wire and
retention bounds, all deadline layers, paced additional admission and opt-out denial,
connect failures, cancellation during greeting/TLS/HTTP, JSONL provenance and explicit
v1/v2 compatibility. Test keys/certificates are generated by the OpenSSL CLI in temp
directories, never committed. No new Python package or running service is required.

Protocol references: [HTTP semantics](https://www.rfc-editor.org/rfc/rfc9110.html),
[HTTP/1.1 framing](https://www.rfc-editor.org/rfc/rfc9112.html),
[SSH identification](https://www.rfc-editor.org/rfc/rfc4253.html#section-4.2),
[SMTP greetings](https://www.rfc-editor.org/rfc/rfc5321.html#section-4.2),
and [Python SSLObject/MemoryBIO](https://docs.python.org/3.14/library/ssl.html).

Phase 3 moved the syntax parsers without behavioral changes so offline derivations
can reuse them without depending on collector execution. See
[FINGERPRINTS.md](FINGERPRINTS.md). Collector output still contains no product or
device claims; all new candidates are independent versioned derived records.

## Phase 10 admission adapter

The worker runtime reuses the unchanged collector with a central one-use permit callback
for every connection, including the second TLS connection. A delayed/lost permit cannot
be retried into another measurement. Shared rates, occupied socket slots, heartbeat loss,
result replay and stop latency are defined in [DISTRIBUTED.md](DISTRIBUTED.md). The worker
adapter only executes explicit authored literal-loopback fixtures. Collector/domain
contracts and the two-connection protocol plan remain unchanged.

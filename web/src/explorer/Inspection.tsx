import type {
  CaptureView,
  FieldView,
  InspectionResponse,
  Preview,
} from "../api/schema";
import { categories, inert } from "./model";

function PreviewText({ value }: { value: Preview }) {
  return (
    <div className="preview">
      <p>
        {value.state} · {value.shown_bytes ?? 0} / {value.original_bytes} bytes
        {value.truncated && " · display truncated"}
      </p>
      {value.state === "text" && <pre>{inert(value.text ?? "")}</pre>}
      {value.state === "redacted" && <p>Content withheld by preview policy.</p>}
      {value.state === "unsupported" && (
        <p>Unsupported or unreviewed format; no raw fallback.</p>
      )}
    </div>
  );
}
function Fields({ fields }: { fields: readonly FieldView[] }) {
  return (
    <dl>
      {fields.map((f, i) => (
        // biome-ignore lint/suspicious/noArrayIndexKey: Immutable ordered fields preserve duplicate header occurrences.
        <div key={`${i}-${f.name}`}>
          <dt>{inert(f.name)}</dt>
          <dd>
            <PreviewText value={f.value} />
          </dd>
        </div>
      ))}
    </dl>
  );
}
function Capture({ data: c }: { data: CaptureView }) {
  return (
    <section aria-label="Capture preview" className="capture">
      <h3>{c.parse_state} capture</h3>
      <p className="hash">
        Pointer: {inert(c.pointer)} · SHA-256: {c.sha256}
      </p>
      <p>
        {c.byte_length} retained bytes · capture{" "}
        {c.capture_truncated ? "truncated" : "not marked truncated"}
        {c.body_start != null && ` · body starts at byte ${c.body_start}`}
      </p>
      <p>
        {c.withheld_headers ?? 0} unreviewed headers withheld. SSH
        comments/preambles are withheld.
      </p>
      <Fields fields={c.fields} />
      <h4>Bounded content preview</h4>
      <PreviewText value={c.preview} />
    </section>
  );
}
export function Inspection({
  data: d,
  onHistory,
  onClose,
}: {
  data: InspectionResponse;
  onHistory: () => void;
  onClose: () => void;
}) {
  const trace = d.derivation;
  return (
    <section className="inspection" aria-labelledby="inspection-title">
      <h2 id="inspection-title" tabIndex={-1}>
        Service & evidence inspection
      </h2>
      <p>
        <bdi>{inert(d.address)}</bdi> :{d.port} / {d.transport} · {d.outcome}
      </p>
      <button type="button" onClick={onHistory}>
        View endpoint timeline
      </button>{" "}
      <button type="button" onClick={onClose}>
        Close inspection
      </button>
      <p>
        One immutable observation. A failed or empty attempt does not erase
        earlier evidence.
      </p>
      <p className="hash">
        Observation: {d.observation_id} · source SHA-256: {d.source_sha256}
      </p>
      <p>
        Source schema {d.source_schema_version} · started {inert(d.started_at)}{" "}
        · finished {inert(d.finished_at)}
      </p>
      <p>
        Retention checked {inert(d.retention_checked_at)} · expires{" "}
        {inert(d.expires_at)}
      </p>
      <p>
        Preview policy: {d.preview_policy}. Synthetic input only. Known
        sensitive markers are withheld; this is not comprehensive
        sensitive-content sanitization. Previews are separate from canonical
        bytes.
      </p>
      {d.legacy_capture && <Capture data={d.legacy_capture} />}
      {d.exchanges.map((e) => (
        <section key={e.connection} aria-label={`Connection ${e.connection}`}>
          <h3>
            Connection {e.connection} · {e.probe}
          </h3>
          <p>
            TCP {e.tcp_outcome} · collection {e.status} · HTTP request{" "}
            {e.http_request_sent ? "sent" : "not sent"}
          </p>
          {!!e.candidates.length && (
            <p>Protocol alternatives: {e.candidates.join(" / ")}</p>
          )}
          <Fields fields={e.tls_fields} />
          {e.verification && (
            <p>
              TLS verification: not_performed. Trust, hostname, validity and
              revocation were not verified. Chain{" "}
              {e.chain_truncated ? "truncated" : "not marked truncated"}.
            </p>
          )}
          {e.certificates.map((c) => (
            <section
              key={c.pointer}
              className="certificate"
              aria-label="Certificate assertions"
            >
              <h4>Certificate · {c.parse_state.replaceAll("_", " ")}</h4>
              <p className="hash">
                Pointer: {c.pointer} · SHA-256: {c.sha256}
              </p>
              <p>
                {c.byte_length} bytes · capture{" "}
                {c.capture_truncated ? "truncated" : "not marked truncated"} ·
                verification: {c.verification}
              </p>
              <p>
                Parsed assertions are not cryptographic validation or trusted
                identity. Extensions and resource links are withheld.
              </p>
              <Fields fields={c.fields ?? []} />
            </section>
          ))}
          {e.capture && <Capture data={e.capture} />}
        </section>
      ))}
      {!d.legacy_capture && !d.exchanges.length && (
        <p>No captured protocol evidence in this observation.</p>
      )}
      <h3>Confidence & evidence trace</h3>
      <p>
        Asserted and corroborated are ordinal descriptions, not calibrated
        probabilities. Exposure proves neither trusted identity, safe software
        nor a vulnerability.
      </p>
      {trace ? (
        <>
          <p className="hash">
            Derivation: {d.derivation_id} · trace integrity: {d.trace_integrity}
          </p>
          <p>
            Pack {inert(trace.pack_id)} / {inert(trace.pack_version)} ·{" "}
            {trace.engine_version} · {trace.taxonomy_version}
          </p>
          <p className="hash">
            Pack SHA-256: {trace.pack_sha256} · source{" "}
            {trace.source_observation_id} / {trace.source_sha256}
          </p>
          <p>
            Products: {trace.product_state} · categories: {trace.category_state}{" "}
            · {trace.candidates.length} candidates; no winner selected.
          </p>
          <p>Notes: {trace.notes.join(", ") || "none"}</p>
          {trace.candidates.map((c) => (
            <details key={`${c.rule_id}-${c.evidence[0].pointer}`}>
              <summary>
                {inert(c.product ?? "Product unknown")} ·{" "}
                {c.category ? categories[c.category] : "Category unknown"} ·{" "}
                {c.confidence}
              </summary>
              <p>
                Rule {inert(c.rule_id)} / {inert(c.rule_version)}
              </p>
              <ul>
                {c.evidence.map((r) => (
                  <li key={r.condition_index} className="hash">
                    Condition {r.condition_index} · {r.selector} · {r.pointer} ·
                    decoded bytes [{r.start}, {r.end}) · SHA-256 {r.sha256}
                  </li>
                ))}
              </ul>
              <p>
                Exact ranges reference canonical bytes, not the escaped/redacted
                preview. Trace excerpts are withheld.
              </p>
            </details>
          ))}
        </>
      ) : (
        <p>
          No exact derivation was selected for this source. No new rules are
          executed by inspection.
        </p>
      )}
    </section>
  );
}

import type { DatasetMetadata, Hit, SearchResponse } from "../api/schema";
import { categories, inert } from "./model";

export function Dataset({
  data,
  hash,
}: {
  data: DatasetMetadata;
  hash: string;
}) {
  return (
    <details className="provenance">
      <summary>Dataset attribution & validity</summary>
      <p>
        {inert(data.id)} · version {inert(data.version)}
      </p>
      <p className="hash">SHA-256: {inert(hash)}</p>
      <p>
        Valid from {inert(data.valid_from)} until {inert(data.expires_at)}{" "}
        (exclusive).
      </p>
      {data.origins.map((o) => (
        <div key={o.id} className="origin">
          <strong>{inert(o.attribution)}</strong>
          <p>
            {inert(o.id)} · {inert(o.version)} · {inert(o.license)}
          </p>
          <p>{inert(o.modifications)}</p>
          <p className="hash">Source SHA-256: {inert(o.source_sha256)}</p>
          <p>Source: {inert(o.source_url)}</p>
          <p>License: {inert(o.license_url)}</p>
        </div>
      ))}
    </details>
  );
}
export function Provenance({ response: r }: { response: SearchResponse }) {
  return (
    <>
      <details className="provenance">
        <summary>Selection & count interpretation</summary>
        <p>
          Selected retained observations, never physical devices or Internet
          prevalence. Current source selection happens before filters; an older
          matching source is not substituted.
        </p>
        <p>
          Mode: {r.selection.mode} · selection: {r.selection.selection} ·
          cutoff: {inert(r.selection.as_of ?? "unknown")}
        </p>
        <p>
          Retention checked: {inert(r.retention_checked_at)} · dataset checked:{" "}
          {inert(r.dataset_checked_at)}
        </p>
        <p>
          Pages are live views, not snapshots. Writes, derivations, expiry and
          removal can change results. Only this page is retained in memory;
          hidden or 60-second-old views are cleared.
        </p>
        <p>
          Pack: {inert(r.pack?.pack_id ?? "unavailable")} ·{" "}
          {inert(r.pack?.version ?? "unknown")}
        </p>
        <p className="hash">
          Pack SHA-256: {inert(r.selection.pack_sha256 ?? "unknown")}
        </p>
        <p>{inert(r.pack?.provenance ?? "No selected pack snapshot")}</p>
        <p>
          {r.selection.fingerprint_engine} · {r.selection.taxonomy} ·{" "}
          {r.selection.enrichment_engine}
        </p>
      </details>
      {r.dataset && (
        <Dataset
          data={r.dataset}
          hash={r.selection.dataset_sha256 ?? "unknown"}
        />
      )}
    </>
  );
}
export function Result({
  hit: h,
  onFocus,
  onInspect,
  onHistory,
}: {
  hit: Hit;
  onFocus?: () => void;
  onInspect: () => void;
  onHistory: () => void;
}) {
  return (
    <article
      className="result-card"
      id={`hit-${h.id}`}
      tabIndex={-1}
      aria-label={`${h.address} port ${h.port}`}
    >
      <div className="result-top">
        <h3>
          <bdi>{inert(h.address)}</bdi>
          <span>
            :{h.port} / {h.transport}
          </span>
        </h3>
        <span className={`badge ${h.outcome === "open" ? "green" : ""}`}>
          {h.outcome}
        </span>
      </div>
      <p className="products">
        {h.products.length
          ? h.products.map(inert).join(" · ")
          : "Product unknown"}
      </p>
      <p>
        {h.categories.length
          ? h.categories.map((c) => categories[c]).join(" · ")
          : "Category unknown"}
        {h.category_state === "multiple" && " · multiple candidates; no winner"}
      </p>
      <p>
        {h.place
          ? `${inert(h.place.name)} · ${inert(h.place.country_code)} · ${inert(h.place.id)}`
          : "Place unknown"}{" "}
        · geography {h.geography_state.replaceAll("_", " ")}
      </p>
      <p>
        Accuracy radius:{" "}
        {h.city?.accuracy_radius_km == null
          ? "unknown"
          : `${h.city.accuracy_radius_km} km (dataset reported)`}
      </p>
      <p>
        {h.network
          ? `${h.network.asns.map((n) => `AS${n}`).join(" / ")} · ${inert(h.network.prefix)}`
          : "ASN unknown"}
      </p>
      <p className="muted">
        {h.fresh ? "Fresh" : "Stale"} relative to query cutoff ·{" "}
        {inert(h.finished_at)} · {h.candidate_count} candidates
      </p>
      {onFocus && h.geography_state === "known" && h.place?.point && (
        <button type="button" className="text-button" onClick={onFocus}>
          Locate approximate point
        </button>
      )}
      <button type="button" onClick={onInspect}>
        Inspect this observation
      </button>{" "}
      <button type="button" onClick={onHistory}>
        View endpoint timeline
      </button>
      <details>
        <summary>Observation provenance</summary>
        <p className="hash">
          Source: {inert(h.id)} · SHA-256: {inert(h.source_sha256)}
        </p>
        <p className="hash">
          Fingerprint: {inert(h.derivation_id ?? "unknown")} · enrichment:{" "}
          {inert(h.enrichment_id ?? "disabled or unknown")}
        </p>
        <p>
          City matched prefix: {inert(h.city?.prefix ?? "unknown")} · radius
          basis: {h.city?.radius_basis ?? "unknown"}
        </p>
        <p>
          ASN source: {inert(h.network?.origin ?? "unknown")} · city source:{" "}
          {inert(h.city?.origin ?? "unknown")}
        </p>
        <p>
          {h.place?.point
            ? `Representative point: ${h.place.point[1]}, ${h.place.point[0]}`
            : "Representative point unknown"}
          . Approximate area context, never a precise person or device.
        </p>
      </details>
    </article>
  );
}

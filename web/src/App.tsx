import {
  type FormEvent,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";
import { type Endpoint, readEndpoint, readQuery } from "./api/client";
import type {
  Category,
  EndpointQuery,
  Hit,
  InspectionResponse,
  PlaceSummary,
  PlacesQuery,
  PlacesResponse,
  SearchQuery,
  SearchResponse,
} from "./api/schema";
import { Inspection } from "./explorer/Inspection";
import { ResultMap } from "./explorer/Map";
import { Dataset, Provenance, Result } from "./explorer/Metadata";
import {
  categories,
  features,
  inert,
  message,
  placeFilter,
  placeLabel,
  ReadLane,
} from "./explorer/model";

const initial = {
  dataset: "",
  pack: "",
  text: "",
  category: "",
  network: "",
  asn: "",
  country: "",
  selection: "attempt",
  mode: "current",
  freshness: "any",
  geography: "any",
  limit: "50",
};
type Fields = typeof initial;
const emptyHits: readonly Hit[] = [];

export function App() {
  const [fields, setFields] = useState<Fields>(initial);
  const [placeName, setPlaceName] = useState("");
  const [kind, setKind] = useState("");
  const [chosen, setChosen] = useState<PlaceSummary | null>(null);
  const [boundary, setBoundary] = useState(false);
  const [places, setPlaces] = useState<PlacesResponse | null>(null);
  const [result, setResult] = useState<SearchResponse | null>(null);
  const [inspection, setInspection] = useState<InspectionResponse | null>(null);
  const [timeline, setTimeline] = useState<{
    endpoint: Endpoint;
    query: EndpointQuery;
    response: SearchResponse;
  } | null>(null);
  const [focus, setFocus] = useState<Hit | null>(null);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState(
    "Choose filters, then search the retained synthetic observations.",
  );
  const [error, setError] = useState("");
  const [page, setPage] = useState(1);
  const lane = useRef(new ReadLane());
  const generation = useRef(0);
  const original = useRef<SearchQuery | null>(null);
  const originalPlaces = useRef<PlacesQuery | null>(null);
  const heading = useRef<HTMLHeadingElement>(null);

  const invalidate = useCallback(
    (text = "Filters changed. Run a new search.", clearPlace = false) => {
      generation.current++;
      lane.current.cancel();
      setBusy(false);
      setResult(null);
      setPlaces(null);
      setFocus(null);
      setInspection(null);
      setTimeline(null);
      if (clearPlace) {
        setChosen(null);
        setBoundary(false);
      }
      setError("");
      setNotice(text);
      original.current = null;
      originalPlaces.current = null;
    },
    [],
  );
  useEffect(() => {
    const clearHidden = (event: Event) => {
      if (event.type === "pagehide" || document.visibilityState === "hidden")
        invalidate(
          "View and selected place cleared while hidden. Re-select a place or search again.",
          true,
        );
    };
    window.addEventListener("pagehide", clearHidden);
    document.addEventListener("visibilitychange", clearHidden);
    return () => {
      generation.current++;
      lane.current.cancel();
      window.removeEventListener("pagehide", clearHidden);
      document.removeEventListener("visibilitychange", clearHidden);
    };
  }, [invalidate]);
  useEffect(() => {
    if (!result && !places && !chosen && !inspection && !timeline) return;
    const timer = setTimeout(
      () =>
        invalidate(
          "View and selected place expired after 60 seconds. Re-select a place or search again.",
          true,
        ),
      60000,
    );
    return () => clearTimeout(timer);
  }, [result, places, chosen, inspection, timeline, invalidate]);

  function change(name: keyof Fields, value: string) {
    invalidate();
    setFields((old) => ({
      ...old,
      [name]: value,
      ...(name === "dataset" && !value
        ? { country: "", asn: "", geography: "any" }
        : {}),
    }));
    if (name === "dataset" || name === "country") {
      setChosen(null);
      setBoundary(false);
    }
  }
  async function run<T>(
    work: (signal: AbortSignal) => Promise<T>,
    accept: (value: T) => void,
    label: string,
  ) {
    const id = ++generation.current;
    setResult(null);
    setPlaces(null);
    setFocus(null);
    setInspection(null);
    setTimeline(null);
    setError("");
    setBusy(true);
    setNotice(label);
    try {
      const value = await lane.current.run(work);
      if (id !== generation.current) return;
      accept(value);
      setNotice("Read complete. This is a live retained-data view.");
    } catch (e) {
      if (id === generation.current) {
        setError(message(e));
        setNotice("");
      }
    } finally {
      if (id === generation.current) setBusy(false);
    }
  }
  function query(): SearchQuery {
    return {
      dataset_sha256: fields.dataset.trim() || null,
      pack_sha256: fields.pack.trim() || null,
      text: fields.text.trim() || null,
      category: (fields.category as Category) || null,
      network: fields.network.trim() || null,
      asn: fields.asn ? Number(fields.asn) : null,
      country: fields.country.trim().toUpperCase() || null,
      selection: fields.selection as SearchQuery["selection"],
      mode: fields.mode as SearchQuery["mode"],
      freshness: fields.freshness as SearchQuery["freshness"],
      geography: fields.geography as SearchQuery["geography"],
      limit: Number(fields.limit),
      facet_limit: 20,
      offset: 0,
      ...(chosen ? placeFilter(chosen, boundary) : {}),
    };
  }
  function search(event?: FormEvent, continuation = false) {
    event?.preventDefault();
    const q = continuation && original.current ? original.current : query();
    const cursor = continuation ? result?.next_cursor : null;
    const nextPage = continuation ? page + 1 : 1;
    original.current = q;
    void run(
      (signal) =>
        readQuery(
          "search",
          { schema_version: 1, query: q, cursor },
          { signal },
        ),
      (value) => {
        setResult(value);
        setPage(nextPage);
        requestAnimationFrame(() => heading.current?.focus());
      },
      "Loading observations…",
    );
  }
  function findPlaces(event?: FormEvent, continuation = false) {
    event?.preventDefault();
    if (!fields.dataset.trim()) {
      setError("Choose an exact dataset SHA-256 before finding places.");
      return;
    }
    const q: PlacesQuery =
      continuation && originalPlaces.current
        ? originalPlaces.current
        : {
            dataset_sha256: fields.dataset.trim(),
            name: placeName.trim() || null,
            kind: (kind as PlacesQuery["kind"]) || null,
            country: fields.country.trim().toUpperCase() || null,
            limit: 50,
          };
    const cursor = continuation ? places?.next_cursor : null;
    originalPlaces.current = q;
    void run(
      (signal) =>
        readQuery(
          "places",
          { schema_version: 1, query: q, cursor },
          { signal },
        ),
      setPlaces,
      "Finding exact place names…",
    );
  }
  function endpointQuery(): EndpointQuery {
    return {
      selection: "attempt",
      pack_sha256: fields.pack.trim() || null,
      dataset_sha256: fields.dataset.trim() || null,
      limit: 20,
    };
  }
  function history(endpoint: Endpoint, continuation = false) {
    const q = continuation && timeline ? timeline.query : endpointQuery();
    const cursor = continuation ? timeline?.response.next_cursor : null;
    void run(
      (signal) =>
        readEndpoint(
          "endpointHistory",
          endpoint,
          { schema_version: 1, query: q, cursor },
          { signal },
        ),
      (value) => {
        setTimeline({ endpoint, query: q, response: value });
        requestAnimationFrame(() =>
          document.getElementById("timeline-title")?.focus(),
        );
      },
      "Reading retained endpoint timeline…",
    );
  }
  function inspectHit(hit: Hit) {
    void run(
      (signal) =>
        readEndpoint(
          "endpointInspection",
          hit,
          {
            schema_version: 1,
            query: {
              observation_id: hit.id,
              source_sha256: hit.source_sha256,
              derivation_id: hit.derivation_id,
            },
          },
          { signal },
        ),
      (value) => {
        setInspection(value);
        requestAnimationFrame(() =>
          document.getElementById("inspection-title")?.focus(),
        );
      },
      "Reading bounded evidence…",
    );
  }
  const hits = result?.hits ?? emptyHits;
  const mapped = features(hits).features.length;
  function selectHit(id: string) {
    document.getElementById(`hit-${id}`)?.focus();
    document.getElementById(`hit-${id}`)?.scrollIntoView({ block: "nearest" });
  }

  return (
    <div className="app-shell">
      <a
        className="skip"
        href={
          inspection
            ? "#inspection-title"
            : timeline
              ? "#timeline-title"
              : "#results"
        }
      >
        Skip to {inspection ? "inspection" : timeline ? "timeline" : "results"}
      </a>
      <header>
        <a className="brand" href="/" aria-label="NetAtlas home">
          <span aria-hidden="true">◎</span> NetAtlas
        </a>
        <span className="project-tag">INTERNET OBSERVATORY</span>
        <span className="local-badge">LOCAL / SYNTHETIC ONLY</span>
      </header>
      <main>
        <section className="intro">
          <div>
            <p className="eyebrow">GEOGRAPHIC EXPLORER / PHASE 9</p>
            <h1>Exposure, in context.</h1>
            <p>Explore retained service observations by place and category.</p>
          </div>
          <p className="intro-note">
            Approximate geography.
            <br />
            Traceable sources.
            <br />
            No scans from this interface.
          </p>
        </section>
        <div className="explorer-grid">
          <aside className="filters" aria-label="Search filters">
            <form onSubmit={(e) => search(e)}>
              <h2>Explore observations</h2>
              <label>
                Dataset SHA-256
                <input
                  name="dataset"
                  value={fields.dataset}
                  onChange={(e) => change("dataset", e.target.value)}
                  pattern="[a-f0-9]{64}"
                  maxLength={64}
                  placeholder="Exact hash from local seed output"
                  spellCheck={false}
                />
              </label>
              <p className="hint">
                Blank disables geography and ASN enrichment. No newest dataset
                is chosen automatically.
              </p>
              <label>
                Product labels
                <input
                  name="text"
                  value={fields.text}
                  onChange={(e) => change("text", e.target.value)}
                  maxLength={256}
                  placeholder="e.g. nginx"
                />
              </label>
              <p className="hint">
                All simple tokens must match product labels.
              </p>
              <label>
                Category
                <select
                  aria-label="Category"
                  value={fields.category}
                  onChange={(e) => change("category", e.target.value)}
                >
                  <option value="">All categories</option>
                  {Object.entries(categories).map(([id, label]) => (
                    <option key={id} value={id}>
                      {label}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Country code
                <input
                  value={fields.country}
                  onChange={(e) => change("country", e.target.value)}
                  maxLength={2}
                  pattern="[A-Za-z]{2}"
                  placeholder="e.g. FJ"
                  disabled={!fields.dataset}
                />
              </label>
              <label>
                Current source
                <select
                  value={fields.selection}
                  onChange={(e) => change("selection", e.target.value)}
                >
                  <option value="attempt">Last attempt</option>
                  <option value="open">Last open</option>
                  <option value="evidence">Last nonempty evidence</option>
                </select>
              </label>
              {chosen && (
                <div className="chosen">
                  <strong>Selected place</strong>
                  <p>{placeLabel(chosen)}</p>
                  <label>
                    <input
                      type="checkbox"
                      checked={boundary}
                      disabled={!chosen.has_boundary}
                      onChange={(e) => {
                        invalidate();
                        setBoundary(e.target.checked);
                      }}
                    />{" "}
                    Match points within boundary
                  </label>
                  <p className="hint">
                    {boundary
                      ? `${chosen.boundary_kind} boundary; points, not accuracy disks.`
                      : chosen.kind === "country"
                        ? "Dataset country-code association; not verified membership."
                        : "Exact place-ID association; no inferred region membership."}
                  </p>
                  <button
                    type="button"
                    className="text-button"
                    onClick={() => {
                      invalidate();
                      setChosen(null);
                      setBoundary(false);
                    }}
                  >
                    Clear selected place
                  </button>
                </div>
              )}
              <details className="advanced">
                <summary>Network, freshness & selection</summary>
                <label>
                  Literal IP or CIDR
                  <input
                    value={fields.network}
                    maxLength={64}
                    onChange={(e) => change("network", e.target.value)}
                    placeholder="192.0.2.0/24"
                  />
                </label>
                <label>
                  ASN
                  <input
                    type="number"
                    min="1"
                    max="4294967295"
                    value={fields.asn}
                    disabled={!fields.dataset}
                    onChange={(e) => change("asn", e.target.value)}
                  />
                </label>
                <label>
                  Observation mode
                  <select
                    value={fields.mode}
                    onChange={(e) => change("mode", e.target.value)}
                  >
                    <option value="current">Current per endpoint</option>
                    <option value="history">All retained observations</option>
                  </select>
                </label>
                <label>
                  Freshness
                  <select
                    value={fields.freshness}
                    onChange={(e) => change("freshness", e.target.value)}
                  >
                    <option value="any">Any age</option>
                    <option value="fresh">Fresh (within 24 hours)</option>
                    <option value="stale">Stale (older than 24 hours)</option>
                  </select>
                </label>
                <label>
                  Geography state
                  <select
                    value={fields.geography}
                    disabled={!fields.dataset}
                    onChange={(e) => change("geography", e.target.value)}
                  >
                    <option value="any">Any state</option>
                    <option value="known">Known point</option>
                    <option value="unknown">Unknown point</option>
                    <option value="stale">Stale dataset</option>
                    <option value="not_yet_valid">Future dataset</option>
                  </select>
                </label>
                <label>
                  Fingerprint pack SHA-256
                  <input
                    value={fields.pack}
                    onChange={(e) => change("pack", e.target.value)}
                    maxLength={64}
                    pattern="[a-f0-9]{64}"
                    placeholder="Blank uses core pack"
                  />
                </label>
                <label>
                  Page size
                  <select
                    value={fields.limit}
                    onChange={(e) => change("limit", e.target.value)}
                  >
                    {[5, 20, 50, 100, 200].map((n) => (
                      <option key={n}>{n}</option>
                    ))}
                  </select>
                </label>
              </details>
              <button className="primary" type="submit" disabled={busy}>
                Search observations <span aria-hidden="true">→</span>
              </button>
            </form>
            <form className="place-search" onSubmit={(e) => findPlaces(e)}>
              <h2>Find a place</h2>
              <label>
                Exact place name
                <input
                  value={placeName}
                  maxLength={256}
                  onChange={(e) => {
                    invalidate();
                    setPlaceName(e.target.value);
                  }}
                  placeholder="Suva, Fiji, Example Harbor…"
                />
              </label>
              <label>
                Place kind
                <select
                  value={kind}
                  onChange={(e) => {
                    invalidate();
                    setKind(e.target.value);
                  }}
                >
                  <option value="">Country, region or city</option>
                  <option value="country">Country</option>
                  <option value="region">Region</option>
                  <option value="city">City</option>
                </select>
              </label>
              <p className="hint">
                Exact name, ignoring case. Blank lists places. Uses the dataset
                and country above; entries are not observation counts.
              </p>
              <button type="submit" disabled={busy || !fields.dataset}>
                Find places
              </button>
            </form>
          </aside>
          <div className="workspace">
            <div className="status-line" role="status" aria-live="polite">
              {notice}
            </div>
            {busy && (
              <button
                type="button"
                onClick={() =>
                  invalidate("Read cancelled. You can start another search.")
                }
              >
                Cancel read
              </button>
            )}
            {error && (
              <div className="error" role="alert">
                <p>{error}</p>
                <button type="button" onClick={() => search()}>
                  Restart search
                </button>
                <button
                  type="button"
                  onClick={() => findPlaces()}
                  disabled={!fields.dataset}
                >
                  Retry place lookup
                </button>
              </div>
            )}
            {places && (
              <section className="place-results" aria-label="Place matches">
                <h2>
                  {places.total} gazetteer matches · dataset{" "}
                  {places.dataset_state.replaceAll("_", " ")}
                </h2>
                {!places.places.length && (
                  <p>
                    {places.dataset_state === "valid"
                      ? "No places match. Try an exact name or remove the name filter."
                      : "This dataset is stale or not yet valid; no places are available."}
                  </p>
                )}
                <ul>
                  {places.places.map((p) => (
                    <li key={p.id}>
                      <button
                        type="button"
                        onClick={() => {
                          invalidate(
                            "Place selected. Search observations to apply it.",
                          );
                          setChosen(p);
                          setBoundary(p.kind === "region" && p.has_boundary);
                        }}
                      >
                        {placeLabel(p)}
                      </button>
                    </li>
                  ))}
                </ul>
                <p>
                  Showing {places.places.length} entries on this page. Names are
                  not identities.
                </p>
                {places.next_cursor && (
                  <button
                    type="button"
                    onClick={() => findPlaces(undefined, true)}
                  >
                    Next places page
                  </button>
                )}
                <Dataset data={places.dataset} hash={places.dataset_sha256} />
              </section>
            )}
            {inspection && (
              <Inspection
                data={inspection}
                onHistory={() => history(inspection)}
                onClose={() =>
                  invalidate("Inspection cleared. Run a fresh search.", true)
                }
              />
            )}
            {timeline && (
              <section className="inspection" aria-labelledby="timeline-title">
                <h2 id="timeline-title" tabIndex={-1}>
                  Endpoint timeline
                </h2>
                <p>
                  {timeline.endpoint.address} :{timeline.endpoint.port} /{" "}
                  {timeline.endpoint.transport}
                </p>
                <p>
                  All retained attempts, newest first. Negative and empty
                  attempts remain separate from earlier evidence. Showing{" "}
                  {timeline.response.hits.length} of{" "}
                  {timeline.response.counts.observations} observations.
                </p>
                {!timeline.response.hits.length && (
                  <p>No retained observations for this endpoint.</p>
                )}
                {timeline.response.hits.map((hit) => (
                  <Result
                    key={hit.id}
                    hit={hit}
                    onInspect={() => inspectHit(hit)}
                    onHistory={() => history(hit)}
                  />
                ))}
                {timeline.response.next_cursor && (
                  <button
                    type="button"
                    onClick={() => history(timeline.endpoint, true)}
                  >
                    Next timeline page
                  </button>
                )}
                {timeline.response.page_limit_reached && (
                  <p>10,000-hit traversal limit reached.</p>
                )}
                <button
                  type="button"
                  onClick={() => history(timeline.endpoint)}
                >
                  Refresh timeline
                </button>{" "}
                <button
                  type="button"
                  onClick={() =>
                    invalidate("Timeline cleared. Run a fresh search.", true)
                  }
                >
                  Close timeline
                </button>
                <Provenance response={timeline.response} />
              </section>
            )}
            {!inspection && !timeline && (
              <>
                <ResultMap hits={hits} focus={focus} onSelect={selectHit} />
                <div className="map-scope">
                  <strong>
                    {mapped} mapped / {hits.length} displayed observations
                  </strong>
                  <span>
                    Page {page} only · clusters count displayed observations ·{" "}
                    {hits.length - mapped} without usable points
                  </span>
                </div>
                <p className="map-legend">
                  <span className="legend web" /> Web{" "}
                  <span className="legend ssh" /> SSH{" "}
                  <span className="legend mail" /> Mail{" "}
                  <span className="legend multi" /> Multiple{" "}
                  <span className="legend unknown" /> Unknown{" "}
                  <span className="legend other" /> Other categories
                </p>
                <p className="uncertainty">
                  Points represent approximate areas, never precise people or
                  devices. Missing accuracy radii are unknown. Area filters test
                  representative points, not uncertainty-disk overlap.
                </p>
                <section
                  id="results"
                  aria-labelledby="results-title"
                  aria-busy={busy}
                >
                  <div className="results-heading">
                    <h2 ref={heading} tabIndex={-1} id="results-title">
                      {result ? "Search results" : "Observation results"}
                    </h2>
                    {result && (
                      <span>
                        PAGE {page} / {hits.length} SHOWN
                      </span>
                    )}
                  </div>
                  {result ? (
                    <>
                      <div className="counts">
                        <div>
                          <strong>{result.counts.endpoints}</strong>
                          <span>Endpoint keys</span>
                        </div>
                        <div>
                          <strong>{result.counts.observations}</strong>
                          <span>Source observations</span>
                        </div>
                        <div>
                          <strong>{result.counts.candidates}</strong>
                          <span>All selected candidates</span>
                        </div>
                      </div>
                      <p className="hint">
                        Totals cover all matches. Map and list show only this
                        page. Counts describe retained synthetic observations.
                      </p>
                      {!!result.facets.length && (
                        <details className="facets">
                          <summary>Categories & network counts</summary>
                          <p>
                            Post-filter counts include each facet's own filter.
                            Multiple values and history can exceed totals.
                          </p>
                          {[
                            "category",
                            "asn",
                            "country",
                            "prefix",
                            "geography",
                          ].map((kind) => {
                            const rows = result.facets.filter(
                              (f) => f.kind === kind,
                            );
                            if (!rows.length) return null;
                            return (
                              <div key={kind}>
                                <h3>{kind}</h3>
                                <p>
                                  Showing {rows.length} of{" "}
                                  {rows[0].total_buckets} buckets
                                  {rows.length < rows[0].total_buckets
                                    ? " · truncated"
                                    : ""}
                                </p>
                                <ul>
                                  {rows.map((f) => (
                                    <li key={f.value}>
                                      {inert(f.value)}: {f.endpoints} endpoints
                                      / {f.observations} observations
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            );
                          })}
                        </details>
                      )}
                      {!hits.length && (
                        <div className="empty">
                          <h3>No matching observations</h3>
                          <p>
                            Try fewer filters or a different current source.
                            Unknown geography does not trigger a lookup.
                          </p>
                        </div>
                      )}
                      {hits.map((hit) => (
                        <Result
                          key={hit.id}
                          hit={hit}
                          onInspect={() => inspectHit(hit)}
                          onHistory={() => history(hit)}
                          onFocus={() => {
                            setFocus(hit);
                            document
                              .querySelector(".map-panel")
                              ?.scrollIntoView({ block: "center" });
                          }}
                        />
                      ))}
                      <div className="pagination">
                        <button type="button" onClick={() => search()}>
                          Refresh / first page
                        </button>
                        {result.next_cursor && (
                          <button
                            type="button"
                            onClick={() => search(undefined, true)}
                          >
                            Next results page
                          </button>
                        )}
                      </div>
                      {result.page_limit_reached && (
                        <p role="status">
                          The 10,000-hit traversal limit was reached. Narrow the
                          filters to inspect more observations.
                        </p>
                      )}
                      <Provenance response={result} />
                    </>
                  ) : (
                    <div className="empty">
                      <h3>
                        {busy
                          ? "Reading local observations…"
                          : "Your search starts here"}
                      </h3>
                      <p>
                        Choose a dataset hash to explore places, or search
                        without one for unenriched results. The offline Fiji
                        basemap is available even without a database.
                      </p>
                      <p>
                        For the authored offline demo, run{" "}
                        <code>make demo</code> locally and paste its dataset
                        hash. No Internet access or paid map service is needed
                        after setup.
                      </p>
                    </div>
                  )}
                </section>
              </>
            )}
          </div>
        </div>
      </main>
      <footer>
        <span>
          NetAtlas / University thesis project ·{" "}
          <a href="/maplibre-LICENSE.txt">MapLibre license notices</a>
        </span>
        <span>Synthetic local research · No Internet prevalence claim</span>
      </footer>
    </div>
  );
}

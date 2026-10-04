import { useEffect, useState } from "react";

type ApiState = "checking" | "connected" | "unavailable";

export function App() {
  const [apiState, setApiState] = useState<ApiState>("checking");

  useEffect(() => {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 5000);
    let active = true;
    fetch("/healthz", { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error("API unavailable");
        const health: unknown = await response.json();
        if (
          typeof health !== "object" ||
          health === null ||
          !("status" in health) ||
          health.status !== "ok"
        ) {
          throw new Error("Unexpected health response");
        }
        if (active) setApiState("connected");
      })
      .catch(() => {
        if (active) setApiState("unavailable");
      })
      .finally(() => clearTimeout(timer));
    return () => {
      active = false;
      clearTimeout(timer);
      controller.abort();
    };
  }, []);

  return (
    <div className="app-shell">
      <header>
        <a href="/" className="brand">
          <span aria-hidden="true">◎</span> NetAtlas
        </a>
        <span className="project-tag">INTERNET OBSERVATORY</span>
        <span className={`connection ${apiState}`} role="status">
          <span aria-hidden="true">●</span>{" "}
          {apiState === "connected"
            ? "Local API connected"
            : apiState === "checking"
              ? "Connecting to local API…"
              : "Local API unavailable"}
        </span>
      </header>
      <main>
        <section className="intro" aria-labelledby="page-title">
          <p className="eyebrow">GLOBAL INTERNET EXPOSURE / RESEARCH PROJECT</p>
          <h1 id="page-title">
            A clearer view of
            <br />
            <em>the connected world.</em>
          </h1>
          <p className="lede">
            An independent observatory for understanding the services exposed
            across the Internet. Built for traceable measurements, geographic
            exploration, and research.
          </p>
          <div className="phase-label">
            <span className="dot" /> Phase 1 · Bounded discovery
          </div>
        </section>

        <section className="workspace" aria-labelledby="workspace-title">
          <div className="orbital" aria-hidden="true">
            <div className="globe">
              <div className="meridian" />
              <div className="equator" />
              <div className="latitude top" />
              <div className="latitude bottom" />
            </div>
            <span className="coordinate">
              INDEPENDENT MEASUREMENT · OPEN STANDARDS
            </span>
          </div>
          <div className="workspace-copy">
            <p className="eyebrow">THE FOUNDATION IS IN PLACE</p>
            <h2 id="workspace-title">
              An atlas starts
              <br />
              with observations.
            </h2>
            <p>
              Bounded TCP discovery is available through the local CLI. Service
              analysis and geographic search will arrive in later development
              phases.
            </p>
            <p className="empty-note">
              This preview shows no measured data and cannot start scans.
            </p>
            {apiState === "connected" ? (
              <a className="action" href="/api/v1/examples/observation">
                View a synthetic observation <span aria-hidden="true">↗</span>
              </a>
            ) : (
              <p className="api-hint">
                Start the local API to explore the example observation.
              </p>
            )}
          </div>
        </section>

        <section className="principles" aria-label="Project principles">
          <article>
            <span className="number">01</span>
            <h3>Independent discovery</h3>
            <p>
              Our own observations, with no commercial device-search dependency.
            </p>
          </article>
          <article>
            <span className="number">02</span>
            <h3>Evidence first</h3>
            <p>
              Versioned records will connect every classification to the
              response behind it.
            </p>
          </article>
          <article>
            <span className="number">03</span>
            <h3>Geographic context</h3>
            <p>
              Explore networks and services by place, with location uncertainty
              made visible.
            </p>
          </article>
        </section>
      </main>
      <footer>
        <span>NetAtlas / University thesis project</span>
        <span>Foundation preview · No measured data</span>
      </footer>
    </div>
  );
}

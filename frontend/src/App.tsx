import { useLayoutEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";

import { scanUrl } from "./api";
import type { ScanResponse, ScanState } from "./types";
import "./App.css";

type UiStatus = "idle" | "loading" | "done" | "error";

const SAMPLE_URLS = [
  "https://github.com/login",
  "https://wordpress.com/log-in/",
  "https://accounts.google.com/signin?hl=en-GB",
  "https://www.wikipedia.org/",
];

const THEME_STORAGE_KEY = "auth-scan-theme";

function readInitialTheme(): "light" | "dark" {
  try {
    const saved = localStorage.getItem(THEME_STORAGE_KEY);
    if (saved === "light" || saved === "dark") return saved;
  } catch {
    /* ignore */
  }
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function App() {
  const [theme, setTheme] = useState<"light" | "dark">(() =>
    typeof window === "undefined" ? "light" : readInitialTheme(),
  );
  const [url, setUrl] = useState("https://github.com/login");
  const [debugEnabled, setDebugEnabled] = useState(true);
  const [status, setStatus] = useState<UiStatus>("idle");
  const [errorMessage, setErrorMessage] = useState("");
  const [result, setResult] = useState<ScanResponse | null>(null);
  const [lastScannedAt, setLastScannedAt] = useState<Date | null>(null);

  const canSubmit = useMemo(() => {
    const candidate = url.trim();
    if (!candidate) return false;
    try {
      const parsed = new URL(candidate);
      return parsed.protocol === "http:" || parsed.protocol === "https:";
    } catch {
      return false;
    }
  }, [url]);

  useLayoutEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    try {
      localStorage.setItem(THEME_STORAGE_KEY, theme);
    } catch {
      /* ignore */
    }
  }, [theme]);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canSubmit) return;

    setStatus("loading");
    setErrorMessage("");
    setResult(null);

    try {
      const payload = await scanUrl(url.trim(), { debug: debugEnabled });
      setResult(payload);
      setStatus("done");
      setLastScannedAt(new Date());
    } catch (error) {
      setStatus("error");
      setErrorMessage(error instanceof Error ? error.message : "Unexpected error while scanning.");
    }
  }

  return (
    <main className="page">
      <div className="top-bar">
        <button
          type="button"
          className="theme-toggle"
          onClick={() => setTheme((t) => (t === "dark" ? "light" : "dark"))}
          aria-label={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
        >
          <span className="theme-toggle__icon" aria-hidden>
            {theme === "dark" ? "◐" : "◑"}
          </span>
          {theme === "dark" ? "Light" : "Dark"}
        </button>
      </div>

      <section className="card">
        <header className="header">
          <h1>Auth Snippet Discovery</h1>
          <p>
            Scan any public URL and extract the most relevant authentication HTML snippet with explainable detection
            signals.
          </p>
        </header>

        <form className="scan-form" onSubmit={onSubmit}>
          <label htmlFor="url-input">Website URL</label>
          <div className="input-row">
            <input
              id="url-input"
              name="url"
              type="url"
              value={url}
              onChange={(event) => setUrl(event.target.value)}
              placeholder="https://example.com/login"
              autoComplete="off"
              required
            />
            <button type="submit" disabled={!canSubmit || status === "loading"}>
              {status === "loading" ? "Scanning..." : "Scan"}
            </button>
          </div>

          <div className="form-footer">
            <label className="toggle">
              <input
                type="checkbox"
                checked={debugEnabled}
                onChange={(event) => setDebugEnabled(event.target.checked)}
              />
              Include debug diagnostics
            </label>

            <div className="samples">
              {SAMPLE_URLS.map((sample) => (
                <button key={sample} type="button" onClick={() => setUrl(sample)}>
                  {new URL(sample).hostname}
                </button>
              ))}
            </div>
          </div>
        </form>
      </section>

      {status === "error" && (
        <section className="card error-card">
          <h2>Scan failed</h2>
          <p>{errorMessage}</p>
        </section>
      )}

      {result && (
        <section className="card result-card">
          <div className="result-header">
            <div>
              <h2>Result</h2>
              <p className="muted">{lastScannedAt ? `Scanned at ${lastScannedAt.toLocaleString()}` : null}</p>
            </div>
            <StateBadge state={result.state} />
          </div>

          <dl className="metadata-grid">
            <Metadata label="Input URL" value={result.input_url} />
            <Metadata label="Source URL" value={result.source} />
            <Metadata label="Found" value={String(result.found)} />
            <Metadata label="Confidence" value={result.confidence.toFixed(2)} />
            <Metadata label="Message" value={result.message} />
          </dl>

          <section>
            <h3>Detection signals</h3>
            {result.detection_signals.length ? (
              <ul className="signal-list">
                {result.detection_signals.map((signal) => (
                  <li key={signal}>{signal}</li>
                ))}
              </ul>
            ) : (
              <p className="muted">No detection signals were emitted for this scan.</p>
            )}
          </section>

          <section>
            <div className="section-header">
              <h3>Authentication HTML snippet</h3>
              {result.html_snippet ? (
                <button type="button" onClick={() => navigator.clipboard.writeText(result.html_snippet ?? "")}>
                  Copy
                </button>
              ) : null}
            </div>
            {result.html_snippet ? (
              <pre>{result.html_snippet}</pre>
            ) : (
              <p className="muted">No auth snippet available for this scan state.</p>
            )}
          </section>

          {result.debug ? (
            <section>
              <h3>Debug diagnostics</h3>
              <pre>{JSON.stringify(result.debug, null, 2)}</pre>
            </section>
          ) : null}
        </section>
      )}
    </main>
  );
}

function StateBadge({ state }: { state: ScanState }) {
  return <span className={`badge badge-${state}`}>{state}</span>;
}

function Metadata({ label, value }: { label: string; value: string }) {
  return (
    <div className="metadata">
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

export default App;

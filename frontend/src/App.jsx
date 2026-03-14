import { useState, useEffect, useCallback } from "react";
import { createJob, getJob, listJobs, getJobResult } from "./api";
import "./App.css";

function App() {
  const [jobs, setJobs] = useState([]);
  const [selectedSources, setSelectedSources] = useState({ weather: false, news: false });
  const [city, setCity] = useState("London");
  const [topic, setTopic] = useState("technology");
  const [loading, setLoading] = useState(false);
  const [activeResult, setActiveResult] = useState(null);
  const [pollingIds, setPollingIds] = useState(new Set());

  const refreshJobs = useCallback(async () => {
    try {
      const data = await listJobs();
      setJobs(data);
    } catch (err) {
      console.error("Failed to load jobs:", err);
    }
  }, []);

  useEffect(() => {
    refreshJobs();
  }, [refreshJobs]);

  useEffect(() => {
    if (pollingIds.size === 0) return;

    const interval = setInterval(async () => {
      const nextIds = new Set();
      for (const jobId of pollingIds) {
        try {
          const job = await getJob(jobId);
          if (job.status === "PENDING" || job.status === "PROCESSING") {
            nextIds.add(jobId);
          }
        } catch {
          nextIds.delete(jobId);
        }
      }
      setPollingIds(nextIds);
      refreshJobs();
    }, 2000);

    return () => clearInterval(interval);
  }, [pollingIds, refreshJobs]);

  const toggleSource = (source) => {
    setSelectedSources((prev) => ({ ...prev, [source]: !prev[source] }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const sources = Object.entries(selectedSources)
      .filter(([, v]) => v)
      .map(([k]) => k);
    if (sources.length === 0) return;

    setLoading(true);
    try {
      const parameters = { city, topic };
      const job = await createJob(sources, parameters);
      setPollingIds((prev) => new Set([...prev, job.id]));
      await refreshJobs();
    } catch (err) {
      console.error("Failed to create job:", err);
      alert(err.response?.data?.detail || "Failed to create job");
    } finally {
      setLoading(false);
    }
  };

  const handleViewResult = async (jobId) => {
    setLoading(true);
    setActiveResult(null);
    try {
      const result = await getJobResult(jobId);
      setActiveResult(result);
    } catch (err) {
      console.error("Failed to fetch result:", err);
      alert(err.response?.data?.detail || "Failed to fetch result");
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (str) => {
    if (!str) return "-";
    const d = new Date(str);
    return d.toLocaleString();
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>Async Data Aggregator</h1>
      </header>

      <section className="card">
        <h2>Create aggregation job</h2>
        <form onSubmit={handleSubmit} className="job-form">
          <div className="form-group">
            <label>Sources</label>
            <div className="form-row checkbox-row">
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={selectedSources.weather}
                  onChange={() => toggleSource("weather")}
                />
                Weather
              </label>
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={selectedSources.news}
                  onChange={() => toggleSource("news")}
                />
                News
              </label>
            </div>
          </div>
          <div className="form-row">
            <div className="form-group">
              <label htmlFor="city">City</label>
              <input
                id="city"
                type="text"
                value={city}
                onChange={(e) => setCity(e.target.value)}
                placeholder="e.g. London"
              />
            </div>
            <div className="form-group">
              <label htmlFor="topic">Topic</label>
              <input
                id="topic"
                type="text"
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                placeholder="e.g. technology"
              />
            </div>
          </div>
          <button type="submit" disabled={loading || (!selectedSources.weather && !selectedSources.news)}>
            {loading ? "Creating…" : "Create Job"}
          </button>
        </form>
      </section>

      <section className="card">
        <h2>Jobs</h2>
        <table className="jobs-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Sources</th>
              <th>Status</th>
              <th>Created</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {jobs.length === 0 ? (
              <tr>
                <td colSpan={5}>No jobs yet. Create one above.</td>
              </tr>
            ) : (
              jobs.map((job) => (
                <tr key={job.id}>
                  <td className="mono">{job.id.slice(0, 8)}…</td>
                  <td>{job.sources?.join(", ") || "-"}</td>
                  <td>
                    <span className={`status-badge status-${job.status?.toLowerCase()}`}>
                      {job.status}
                    </span>
                  </td>
                  <td>{formatDate(job.created_at)}</td>
                  <td>
                    {job.status === "COMPLETED" && (
                      <button
                        className="btn-sm"
                        onClick={() => handleViewResult(job.id)}
                        disabled={loading}
                      >
                        View Result
                      </button>
                    )}
                    {(job.status === "PENDING" || job.status === "PROCESSING") && (
                      <span className="spinner" aria-hidden />
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </section>

      {activeResult && (
        <section className="card result-section">
          <h2>Result</h2>
          {activeResult.results?.weather && (
            <div className="result-block">
              <h3 className="result-header">Weather</h3>
              <div className="stat-grid">
                <div className="stat">
                  <span className="stat-label">Temperature</span>
                  <span className="stat-value">
                    {activeResult.results.weather.main?.temp ?? "-"}°C
                  </span>
                </div>
                <div className="stat">
                  <span className="stat-label">Humidity</span>
                  <span className="stat-value">
                    {activeResult.results.weather.main?.humidity ?? "-"}%
                  </span>
                </div>
                <div className="stat">
                  <span className="stat-label">Wind</span>
                  <span className="stat-value">
                    {activeResult.results.weather.wind?.speed ?? "-"} m/s
                  </span>
                </div>
                <div className="stat">
                  <span className="stat-label">Description</span>
                  <span className="stat-value">
                    {activeResult.results.weather.weather?.[0]?.description ?? "-"}
                  </span>
                </div>
              </div>
            </div>
          )}
          {activeResult.results?.news && (
            <div className="result-block">
              <h3 className="result-header">News</h3>
              <ul className="article-list">
                {(activeResult.results.news.articles || []).map((article, i) => (
                  <li key={i}>
                    <a href={article.url} target="_blank" rel="noopener noreferrer">
                      {article.title}
                    </a>
                    <span className="article-source">
                      {article.source?.name || "Unknown"}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {activeResult.errors?.length > 0 && (
            <p className="result-errors">Errors: {activeResult.errors.join("; ")}</p>
          )}
          <details className="raw-json">
            <summary>View Raw JSON</summary>
            <pre>{JSON.stringify(activeResult, null, 2)}</pre>
          </details>
        </section>
      )}
    </div>
  );
}

export default App;

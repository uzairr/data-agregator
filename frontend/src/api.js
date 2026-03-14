import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "http://localhost:8000",
  headers: {
    "Content-Type": "application/json",
  },
});

/**
 * Create a new aggregation job.
 * @param {string[]} sources - Data sources (e.g. ["weather", "news"])
 * @param {object} parameters - Parameters like { city, topic }
 * @returns {Promise<object>} Created job
 */
export async function createJob(sources, parameters = {}) {
  const { data } = await api.post("/api/jobs", { sources, parameters });
  return data;
}

/**
 * Get a job by ID.
 * @param {string} jobId
 * @returns {Promise<object>} Job details
 */
export async function getJob(jobId) {
  const { data } = await api.get(`/api/jobs/${jobId}`);
  return data;
}

/**
 * List jobs, ordered by created_at desc.
 * @returns {Promise<object[]>} List of jobs
 */
export async function listJobs() {
  const { data } = await api.get("/api/jobs");
  return data;
}

/**
 * Get the aggregation result for a completed job.
 * @param {string} jobId
 * @returns {Promise<object>} Result payload (results.weather, results.news, etc.)
 */
export async function getJobResult(jobId) {
  const { data } = await api.get(`/api/jobs/${jobId}/result`);
  return data;
}

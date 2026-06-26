/**
 * Thin API client for the ReelForge backend.
 *
 * Auto-detects the backend base URL:
 *  - If served from the same origin as the backend (e.g. reverse-proxied), uses relative paths.
 *  - Otherwise defaults to http://<same-hostname>:8000 (the default docker-compose backend port).
 * Override by setting window.REELFORGE_API_BASE before this script loads.
 */
const API_BASE = (() => {
  if (window.REELFORGE_API_BASE) return window.REELFORGE_API_BASE;
  const { protocol, hostname, port } = window.location;
  // If frontend is already on 8000, assume same-origin API (e.g. served by FastAPI itself).
  if (port === "8000") return "";
  return `${protocol}//${hostname}:8000`;
})();

const Api = {
  base: API_BASE,

  async health() {
    const res = await fetch(`${API_BASE}/api/health`);
    if (!res.ok) throw new Error("Backend health check failed");
    return res.json();
  },

  async getPlatforms() {
    const res = await fetch(`${API_BASE}/api/platforms`);
    if (!res.ok) throw new Error("Failed to load platforms");
    return res.json();
  },

  async generate(payload) {
    const res = await fetch(`${API_BASE}/api/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to start generation");
    }
    return res.json(); // { job_id }
  },

  async getJob(jobId) {
    const res = await fetch(`${API_BASE}/api/jobs/${jobId}`);
    if (!res.ok) throw new Error("Failed to fetch job status");
    return res.json();
  },

  async cancelJob(jobId) {
    const res = await fetch(`${API_BASE}/api/jobs/${jobId}`, { method: "DELETE" });
    return res.ok;
  },

  downloadVideoUrl(jobId) {
    return `${API_BASE}/api/download/${jobId}`;
  },

  downloadThumbnailUrl(jobId) {
    return `${API_BASE}/api/thumbnail/${jobId}`;
  },
};

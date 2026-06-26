/**
 * ReelForge frontend app logic.
 * Handles: platform chip selection, advanced options panel, job submission,
 * polling for progress, and rendering the final result.
 */

const STATIC_PLATFORMS = {
  instagram_reel: { w: 1080, h: 1920, max_seconds: 90, label: "Instagram Reel" },
  youtube_short: { w: 1080, h: 1920, max_seconds: 60, label: "YouTube Shorts" },
  tiktok: { w: 1080, h: 1920, max_seconds: 180, label: "TikTok" },
  youtube_long: { w: 1920, h: 1080, max_seconds: 1200, label: "YouTube (Long)" },
  facebook: { w: 1280, h: 720, max_seconds: 240, label: "Facebook" },
};

const STAGE_ORDER = ["planning", "sourcing", "voicing", "captioning", "scoring", "rendering", "thumbnail"];
const STAGE_LABELS = {
  queued: "Queued",
  planning: "Writing script",
  sourcing: "Sourcing footage",
  voicing: "Recording voiceover",
  captioning: "Generating captions",
  scoring: "Selecting music",
  rendering: "Rendering video",
  thumbnail: "Generating thumbnail",
  done: "Done",
  failed: "Failed",
};

let selectedPlatform = "instagram_reel";
let pollTimer = null;
let currentJobId = null;

const el = (id) => document.getElementById(id);

function renderPlatformChips(platforms) {
  const container = el("platformChips");
  container.innerHTML = "";
  Object.entries(platforms).forEach(([key, spec]) => {
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = "chip";
    chip.dataset.platform = key;
    chip.setAttribute("aria-pressed", key === selectedPlatform ? "true" : "false");
    chip.textContent = spec.label || key;
    chip.addEventListener("click", () => {
      selectedPlatform = key;
      container.querySelectorAll(".chip").forEach((c) => {
        c.setAttribute("aria-pressed", c.dataset.platform === key ? "true" : "false");
      });
    });
    container.appendChild(chip);
  });
}

function renderPlatformsGrid(platforms) {
  const grid = el("platformsGrid");
  if (!grid) return;
  grid.innerHTML = "";
  Object.entries(platforms).forEach(([key, spec]) => {
    const ratio = spec.w === spec.h ? "1:1" : spec.w > spec.h ? "16:9" : "9:16";
    const minutes = spec.max_seconds >= 60 ? `${Math.round(spec.max_seconds / 60)} min` : `${spec.max_seconds}s`;
    const card = document.createElement("div");
    card.className = "platform-card";
    card.innerHTML = `
      <span class="platform-card__ratio">${ratio}</span>
      <h3>${spec.label || key}</h3>
      <p>${spec.w}\u00d7${spec.h} \u00b7 up to ${minutes}</p>
    `;
    grid.appendChild(card);
  });
}

async function initPlatforms() {
  try {
    const platforms = await Api.getPlatforms();
    renderPlatformChips(platforms);
    renderPlatformsGrid(platforms);
  } catch {
    renderPlatformChips(STATIC_PLATFORMS);
    // leave the static HTML fallback grid in place
  }
}

async function checkBackend() {
  const footerStatus = el("apiStatusFooter");
  try {
    await Api.health();
    footerStatus.textContent = "backend online";
    footerStatus.classList.add("is-ok");
  } catch {
    footerStatus.textContent = "backend unreachable \u2014 check it's running, or update Settings \u2192 API base URL";
    footerStatus.classList.add("is-down");
  }
}

function setupOptionsToggle() {
  const toggle = el("optionsToggle");
  const panel = el("optionsPanel");
  toggle.addEventListener("click", () => {
    const isOpen = panel.hidden === false;
    panel.hidden = isOpen;
    toggle.setAttribute("aria-expanded", String(!isOpen));
  });
}

function buildPayload() {
  const prompt = el("prompt").value.trim();
  const duration = el("optDuration").value;
  return {
    prompt,
    platform: selectedPlatform,
    duration_seconds: duration ? parseInt(duration, 10) : null,
    tone: el("optTone").value,
    add_captions: el("optCaptions").checked,
    add_voiceover: el("optVoiceover").checked,
    add_music: el("optMusic").checked,
    add_thumbnail: el("optThumbnail").checked,
  };
}

function showPanel(panelId) {
  ["renderStatus", "resultBlock", "errorBlock"].forEach((id) => {
    const node = el(id);
    if (node) node.hidden = id !== panelId;
  });
}

function updateStageTrack(status) {
  const spans = el("stageTrack").querySelectorAll("span");
  const currentIndex = STAGE_ORDER.indexOf(status);
  spans.forEach((span) => {
    const stageIndex = STAGE_ORDER.indexOf(span.dataset.stage);
    span.classList.remove("is-active", "is-done");
    if (status === "done") {
      span.classList.add("is-done");
    } else if (stageIndex < currentIndex) {
      span.classList.add("is-done");
    } else if (stageIndex === currentIndex) {
      span.classList.add("is-active");
    }
  });
}

function updateProgressUI(job) {
  el("stageLabel").textContent = STAGE_LABELS[job.status] || job.status;
  el("pctLabel").textContent = job.progress ?? 0;
  el("scrubberFill").style.width = `${job.progress ?? 0}%`;
  el("scrubberPlayhead").style.left = `${job.progress ?? 0}%`;
  el("statusMessage").textContent = job.message || "Working...";
  updateStageTrack(job.status);
}

function renderResult(job) {
  el("renderStatus").hidden = true;
  el("resultBlock").hidden = false;
  el("errorBlock").hidden = true;

  const video = el("resultVideo");
  video.src = Api.downloadVideoUrl(job.job_id);
  video.load();

  el("resultTitle").textContent = (job.plan && job.plan.title) || "Your video";
  el("resultCaption").textContent = (job.plan && job.plan.suggested_caption) || "";

  const tagsContainer = el("resultTags");
  tagsContainer.innerHTML = "";
  ((job.plan && job.plan.suggested_hashtags) || []).forEach((tag) => {
    const span = document.createElement("span");
    span.textContent = tag;
    tagsContainer.appendChild(span);
  });

  const downloadVideoBtn = el("downloadVideoBtn");
  downloadVideoBtn.href = Api.downloadVideoUrl(job.job_id);

  const downloadThumbBtn = el("downloadThumbBtn");
  if (job.thumbnail_path) {
    downloadThumbBtn.href = Api.downloadThumbnailUrl(job.job_id);
    downloadThumbBtn.hidden = false;
  } else {
    downloadThumbBtn.hidden = true;
  }
}

function renderError(job) {
  el("renderStatus").hidden = true;
  el("resultBlock").hidden = true;
  el("errorBlock").hidden = false;
  el("errorDetail").textContent =
    job && job.error && job.error !== "cancelled"
      ? `Details: ${job.error}`
      : "This can happen with very long prompts or heavy server load. Try again, or shorten your prompt.";
}

function resetSubmitButton() {
  const btn = el("submitBtn");
  btn.disabled = false;
  btn.querySelector("span").textContent = "Generate video";
}

async function pollJob(jobId) {
  try {
    const job = await Api.getJob(jobId);
    updateProgressUI(job);

    if (job.status === "done") {
      clearInterval(pollTimer);
      resetSubmitButton();
      renderResult(job);
    } else if (job.status === "failed") {
      clearInterval(pollTimer);
      resetSubmitButton();
      renderError(job);
    }
  } catch (e) {
    clearInterval(pollTimer);
    resetSubmitButton();
    renderError({ error: e.message });
  }
}

async function handleSubmit(e) {
  e.preventDefault();
  const payload = buildPayload();

  if (!payload.prompt || payload.prompt.length < 3) {
    el("prompt").focus();
    return;
  }

  const btn = el("submitBtn");
  btn.disabled = true;
  btn.querySelector("span").textContent = "Starting...";

  el("renderPanel").hidden = false;
  showPanel("renderStatus");
  el("statusMessage").textContent = "Queued \u2014 starting up\u2026";
  el("pctLabel").textContent = "0";
  el("scrubberFill").style.width = "0%";
  el("scrubberPlayhead").style.left = "0%";
  updateStageTrack("queued");

  el("renderPanel").scrollIntoView({ behavior: "smooth", block: "start" });

  try {
    const result = await Api.generate(payload);
    currentJobId = result.job_id;
    if (pollTimer) clearInterval(pollTimer);
    pollJob(currentJobId);
    pollTimer = setInterval(() => pollJob(currentJobId), 1800);
  } catch (err) {
    resetSubmitButton();
    renderError({ error: err.message });
    showPanel("errorBlock");
  }
}

function setupNewVideoButton() {
  el("newVideoBtn").addEventListener("click", () => {
    el("renderPanel").hidden = true;
    el("prompt").value = "";
    el("prompt").focus();
    window.scrollTo({ top: 0, behavior: "smooth" });
  });
}

function setupRetryButton() {
  el("retryBtn").addEventListener("click", () => {
    el("composer").requestSubmit();
  });
}

document.addEventListener("DOMContentLoaded", () => {
  initPlatforms();
  checkBackend();
  setupOptionsToggle();
  setupNewVideoButton();
  setupRetryButton();
  el("composer").addEventListener("submit", handleSubmit);
});

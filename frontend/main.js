const API_BASE = "http://localhost:8000";

const profListEl = document.getElementById("profList");
const detailEl = document.getElementById("detail");
const searchEl = document.getElementById("search");
const sidebarEl = document.getElementById("sidebar");
const toggleBtn = document.getElementById("toggleSidebar");
const copyBtn = document.getElementById("copyBtn");
const draftEl = document.getElementById("draft");

let professors = [];
let filtered = [];
let activeId = null;

toggleBtn.addEventListener("click", () => {
  sidebarEl.classList.toggle("open");
});

copyBtn.addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(draftEl.value || "");
    copyBtn.textContent = "Copied!";
    setTimeout(() => (copyBtn.textContent = "Copy to clipboard"), 1600);
  } catch (err) {
    copyBtn.textContent = "Copy failed";
  }
});

searchEl.addEventListener("input", (e) => {
  const term = e.target.value.toLowerCase();
  filtered = professors.filter(
    (p) =>
      p.name.toLowerCase().includes(term) ||
      (p.institution || "").toLowerCase().includes(term)
  );
  renderList();
});

async function loadProfessors() {
  try {
    const res = await fetch(`${API_BASE}/professors`);
    professors = await res.json();
    filtered = professors;
    renderList();
  } catch (err) {
    detailEl.innerHTML = `<p style="color:#b91c1c;">Failed to load data. Start the backend (uvicorn backend.app.main:app --reload).</p>`;
  }
}

function renderList() {
  profListEl.innerHTML = "";
  filtered.forEach((p) => {
    const div = document.createElement("div");
    div.className = "professor";
    div.innerHTML = `
      <strong>${p.name}</strong>
      <small>${p.institution}</small>
      <div class="tags">${(p.tags || [])
        .map((t) => `<span class="tag">${t}</span>`)
        .join("")}</div>
    `;
    div.addEventListener("click", () => selectProfessor(p.id));
    profListEl.appendChild(div);
  });
  if (!filtered.length) {
    profListEl.innerHTML = "<p style='padding:12px;color:#5f6b7a;'>No matches</p>";
  }
}

async function selectProfessor(id) {
  activeId = id;
  detailEl.innerHTML = "<p>Loading...</p>";
  try {
    const res = await fetch(`${API_BASE}/professors/${id}`);
    if (!res.ok) throw new Error("Not found");
    const p = await res.json();
    renderDetail(p);
  } catch (err) {
    detailEl.innerHTML = `<p style="color:#b91c1c;">Failed to load professor details.</p>`;
  }
}

function renderDetail(p) {
  const pubHtml = (p.publications || [])
    .map(
      (pub) => `
      <div class="pub">
        <div class="pub-title">${pub.link ? `<a href="${pub.link}" target="_blank" rel="noopener">${pub.title}</a>` : pub.title}</div>
        <div class="pub-meta">${pub.published_on || "Unknown date"}</div>
        <div>${(pub.co_authors || [])
          .map((c) => `<span class="co-authors">${c}</span>`)
          .join("")}</div>
      </div>
    `
    )
    .join("");

  const collabHtml = (p.collaborators || [])
    .map(
      (c) => `<div class="chip">${c.name}${c.affiliation ? ` — ${c.affiliation}` : ""}</div>`
    )
    .join("");

  detailEl.innerHTML = `
    <div class="section">
      <h3>${p.name}</h3>
      <p style="margin:4px 0;color:#5f6b7a;">${p.institution}</p>
      <p style="margin:4px 0;">${p.email ? `<a href="mailto:${p.email}">${p.email}</a>` : "No email available"}</p>
      <div class="tags">${(p.top_tags || [])
        .map((t) => `<span class="tag">${t}</span>`)
        .join("")}</div>
    </div>
    <div class="section">
      <h3>Recent Publications</h3>
      ${pubHtml || "<p>No publications available.</p>"}
    </div>
    <div class="section">
      <h3>Collaborators</h3>
      ${collabHtml || "<p>No collaborators listed.</p>"}
    </div>
  `;
}

loadProfessors();

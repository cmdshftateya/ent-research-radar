const API_BASE = "http://localhost:8000";

const profListEl = document.getElementById("profList");
const detailEl = document.getElementById("detail");
const searchEl = document.getElementById("search");
const sidebarEl = document.getElementById("sidebar");
const toggleBtn = document.getElementById("toggleSidebar");
const copyBtn = document.getElementById("copyBtn");
const draftEl = document.getElementById("draft");
const pageSizeEl = document.getElementById("pageSize");
const paginationEl = document.getElementById("pagination");
const closeBtn = document.getElementById("closeSidebar");

let professors = [];
let filtered = [];
let activeId = null;
let pageSize = Number(pageSizeEl?.value) || 10;
let currentPage = 1;
let lastLoadedDetail = null;

toggleBtn.setAttribute("aria-expanded", "false");

const boilerplate = buildDraft();
if (draftEl && !draftEl.value) {
  draftEl.value = boilerplate;
}

function setDrawer(open) {
  sidebarEl.classList.toggle("open", open);
  document.body.classList.toggle("drawer-open", open);
  toggleBtn.setAttribute("aria-expanded", open);
}

toggleBtn.addEventListener("click", () => {
  setDrawer(!sidebarEl.classList.contains("open"));
});

if (closeBtn) {
  closeBtn.addEventListener("click", () => setDrawer(false));
}

document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") setDrawer(false);
});

document.addEventListener("click", (e) => {
  if (!sidebarEl.classList.contains("open")) return;
  const target = e.target;
  if (!sidebarEl.contains(target) && !toggleBtn.contains(target)) {
    setDrawer(false);
  }
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
  currentPage = 1;
  renderList();
});

if (pageSizeEl) {
  pageSizeEl.addEventListener("change", (e) => {
    pageSize = Number(e.target.value) || 10;
    currentPage = 1;
    renderList();
  });
}

async function loadProfessors() {
  try {
    const res = await fetch(`${API_BASE}/professors`);
    professors = await res.json();
    filtered = professors;
    currentPage = 1;
    renderList();
  } catch (err) {
    detailEl.innerHTML = `<p style="color:#b91c1c;">Failed to load data. Start the backend (uvicorn backend.app.main:app --reload).</p>`;
  }
}

function renderList() {
  const totalPages = filtered.length ? Math.ceil(filtered.length / pageSize) : 0;
  if (totalPages && currentPage > totalPages) currentPage = totalPages;
  const startIdx = totalPages ? (currentPage - 1) * pageSize : 0;
  const visible = filtered.slice(startIdx, startIdx + pageSize);

  profListEl.innerHTML = "";
  visible.forEach((p) => {
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

  renderPagination(totalPages);
}

function renderPagination(totalPages) {
  if (!paginationEl) return;
  paginationEl.innerHTML = "";
  if (!filtered.length) return;

  const start = (currentPage - 1) * pageSize + 1;
  const end = Math.min(currentPage * pageSize, filtered.length);

  const meta = document.createElement("div");
  meta.className = "meta";
  meta.innerHTML = `<span class="page-range">${start}–${end}</span> of ${filtered.length}`;

  const controls = document.createElement("div");
  controls.style.display = "flex";
  controls.style.gap = "8px";

  const prevBtn = document.createElement("button");
  prevBtn.className = "page-btn";
  prevBtn.textContent = "Prev";
  prevBtn.disabled = currentPage === 1;
  prevBtn.addEventListener("click", () => {
    if (currentPage > 1) {
      currentPage -= 1;
      renderList();
    }
  });

  const nextBtn = document.createElement("button");
  nextBtn.className = "page-btn";
  nextBtn.textContent = "Next";
  nextBtn.disabled = currentPage >= totalPages;
  nextBtn.addEventListener("click", () => {
    if (currentPage < totalPages) {
      currentPage += 1;
      renderList();
    }
  });

  controls.appendChild(prevBtn);
  controls.appendChild(nextBtn);

  paginationEl.appendChild(meta);
  paginationEl.appendChild(controls);
}

async function selectProfessor(id) {
  activeId = id;
  detailEl.innerHTML = "<p>Loading...</p>";
  try {
    const res = await fetch(`${API_BASE}/professors/${id}`);
    if (!res.ok) throw new Error("Not found");
    const p = await res.json();
    lastLoadedDetail = p;
    renderDetail(p);
    updateDraft(p);
  } catch (err) {
    detailEl.innerHTML = `<p style="color:#b91c1c;">Failed to load professor details.</p>`;
  }
}

function renderDetail(p) {
  const aboutHtml = p.biography
    ? `<p>${p.biography}</p>`
    : "<p style=\"color:#5f6b7a;\">No biography available.</p>";

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

  const profileLink = p.profile_url
    ? `<a class="profile-link" href="${p.profile_url}" target="_blank" rel="noopener noreferrer">Open faculty profile ↗</a>`
    : "";

  detailEl.innerHTML = `
    <div class="section">
      <h3>${p.name}</h3>
      <p style="margin:4px 0;color:#5f6b7a;">${p.institution}</p>
      <p style="margin:4px 0;">${p.email ? `<a href="mailto:${p.email}">${p.email}</a>` : "No email available"}</p>
      ${profileLink ? `<div style="margin:8px 0 4px 0;">${profileLink}</div>` : ""}
      <div class="tags">${(p.top_tags || [])
        .map((t) => `<span class="tag">${t}</span>`)
        .join("")}</div>
    </div>
    <div class="section">
      <h3>About</h3>
      ${aboutHtml}
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

function buildDraft(p = null) {
  const name = p?.name || "there";
  const greetingName = name.split(" ").slice(-1)[0];
  const institution = p?.institution ? ` at ${p.institution}` : "";
  const tags = (p?.top_tags || []).slice(0, 3).join(", ");
  const interests = tags ? `I have been following your work on ${tags}. ` : "";
  const latest = p?.publications?.[0];
  const recentLine = latest
    ? `Your recent paper "${latest.title}" (${latest.published_on || "n.d."}) caught my eye.`
    : "";
  const bioLine = p?.biography
    ? ` I enjoyed reading about ${p.biography.slice(0, 160)}${
        p.biography.length > 160 ? "..." : "."
      }`
    : "";

  return `Hi Dr. ${greetingName},

My name is [Your Name], and I am researching otolaryngology partnerships${institution}. ${interests}${recentLine}${bioLine}

I would appreciate the opportunity to learn more about your current projects and explore how I might contribute. Are you available for a brief call over the next two weeks?

Thank you for your time,
[Your Name]
[Your Affiliation]
`;
}

function updateDraft(p) {
  if (!draftEl) return;
  draftEl.value = buildDraft(p);
}

if (draftEl) {
  draftEl.addEventListener("input", () => {
    draftEl.dataset.userEdited = "true";
  });
}

loadProfessors();

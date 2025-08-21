function getClientProfile() {
  return {
    labels: [] // or try ["mobility", "fall risk", "dressing"]
  };
}

let RetrieveImages = () => {
  const keywordToSearch = document.getElementById("keywordToSearch").value.trim();

  const profile = getClientProfile();
  const profile_labels = (profile?.labels || []).map(l => l.text).filter(Boolean);

  fetch("/imageretrieval", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      keyword: keywordToSearch,
      profile_labels // only labels
    })
  })
  .then(r => r.json())
  .then(data => {
    console.log("🔍 JSON received from server:", data);

    const keywordsMap = data.keywords || {};
    const keywordList = Object.keys(keywordsMap).filter(
      k => Array.isArray(keywordsMap[k]) && keywordsMap[k].length > 0
    );

    if (keywordList.length === 0) {
      document.getElementById("system_response").innerHTML = `<p>No results.</p>`;
      return;
    }

    const allKeywords = ["All", ...keywordList];
    let active = "All";

    let html = `
      <div class="kw-bar">
        ${allKeywords.map(k => `
          <button class="kw-btn${k === active ? " active" : ""}"
                  type="button"
                  data-key="${k}"
                  aria-pressed="${k === active ? "true" : "false"}"
                  title="Show images for ‘${k}’">${k}</button>
        `).join("")}
      </div>
      <div id="kw-gallery" class="image-grid"></div>
    `;

    const container = document.getElementById("system_response");
    container.innerHTML = html;

    const encodePath = (path) => {
      let finalPath = path;
      if (!finalPath.startsWith("Prototype Master/")) {
        finalPath = "Prototype Master/" + finalPath;
      }
      return finalPath.split(/[/\\]/).map(encodeURIComponent).join('/');
    };

    const renderImages = (kw) => {
      let paths = [];
      if (kw === "All") {
        const seen = new Set();
        for (const k of keywordList) {
          for (const p of (keywordsMap[k] || [])) {
            if (!seen.has(p)) { seen.add(p); paths.push(p); }
          }
        }
      } else {
        paths = keywordsMap[kw] || [];
      }

      const grid = document.getElementById("kw-gallery");
      grid.innerHTML = paths.map(path => {
        const encodedPath = encodePath(path);
        return `
          <div class="image-item">
            <img src="/static/images/${encodedPath}"
                 alt="${path}"
                 title="Click to copy image"
                 onclick="copyImageBitmapToClipboard(this)">
            <p class="image-caption">${path}</p>
          </div>
        `;
      }).join("");
    };

    renderImages(active);

    const bar = container.querySelector(".kw-bar");
    bar.addEventListener("click", (e) => {
      const btn = e.target.closest(".kw-btn");
      if (!btn) return;
      const next = btn.dataset.key;
      if (!next || next === active) return;

      bar.querySelectorAll(".kw-btn").forEach(b => {
        const isActive = (b === btn);
        b.classList.toggle("active", isActive);
        b.setAttribute("aria-pressed", isActive ? "true" : "false");
      });

      active = next;
      renderImages(active);
    });
  })
  .catch(err => {
    console.error("Image fetch error:", err);
    document.getElementById("system_response").innerText = "❌ Failed to retrieve images.";
  });
};




document.addEventListener("DOMContentLoaded", () => {
  const STORAGE_KEY = "client_profile_v1";

  // --- elements
  const nameEl   = document.getElementById("client-name");
  const avatarEl = document.getElementById("client-avatar");
  const panelEl  = document.getElementById("chip-panel");
  const addBtn   = document.getElementById("add-chip-btn");
  const avatarBtn= document.getElementById("edit-avatar-btn");
  const keywordInput = document.getElementById("keywordToSearch"); // if present

  // --- initial data (fallback if nothing stored)
  const initial = {
    // seed from DOM so your HTML defaults are preserved on first run
    name: (nameEl?.textContent || "Unnamed").trim(),
    avatar: "https://www.perfocal.com/blog/content/images/size/w1920/2021/01/Perfocal_17-11-2019_TYWFAQ_100_standard-3.jpg",
    labels: []
  };

  // --- state
  let state = load() || initial;

  // --- render
  function render() {
    if (nameEl)   nameEl.textContent = state.name || "Unnamed";
    if (avatarEl) avatarEl.src = state.avatar || "https://www.perfocal.com/blog/content/images/size/w1920/2021/01/Perfocal_17-11-2019_TYWFAQ_100_standard-3.jpg";
    if (panelEl)  panelEl.innerHTML = (state.labels || []).map((l, idx) => chipHTML(l, idx)).join("");
    // annotate list
    panelEl?.setAttribute("aria-label", "Client labels");
  }

  function chipHTML(label, idx) {
    const base = label.style === "filled" ? "chip chip--filled" : "chip chip--outline";
    const textEsc = escapeHtml(label.text);
    return `
      <div class="${base}" role="listitem" data-idx="${idx}" tabindex="0" title="Alt+Click to toggle filled/outline, Double‑click to rename">
        <span class="chip__text">${textEsc}</span>
        <button class="chip__close" type="button" aria-label="Remove ${textEsc}">×</button>
      </div>
    `;
  }

  // --- helpers
  function save() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  }
  function load() {
    try {
      const s = localStorage.getItem(STORAGE_KEY);
      return s ? JSON.parse(s) : null;
    } catch { return null; }
  }
  function escapeHtml(s) {
    return String(s ?? "")
      .replace(/&/g,"&amp;").replace(/</g,"&lt;")
      .replace(/>/g,"&gt;").replace(/"/g,"&quot;")
      .replace(/'/g,"&#039;");
  }

  // --- events

  // Add label
  addBtn?.addEventListener("click", () => {
    const text = prompt("New label:");
    if (!text || !text.trim()) return;
    state.labels.push({ text: text.trim(), style: "filled" });
    save(); render();
  });

  // Change avatar (URL)
  avatarBtn?.addEventListener("click", () => {
    const url = prompt("Paste image URL for client photo:", state.avatar || "");
    if (!url || !url.trim()) return;
    state.avatar = url.trim();
    save(); render();
  });

  // Chip actions: remove, click-to-search, alt+click toggle, dblclick rename
  panelEl?.addEventListener("click", (e) => {
    const chip = e.target.closest(".chip");
    if (!chip) return;
    const idx = Number(chip.dataset.idx);
    if (Number.isNaN(idx)) return;

    // Remove
    if (e.target.closest(".chip__close")) {
      state.labels.splice(idx, 1);
      save(); render();
      return;
    }

    // Plain click → set search box and run search (optional)
    const txt = state.labels[idx]?.text;
    if (txt && keywordInput && typeof RetrieveImages === "function" && !e.altKey) {
      keywordInput.value = txt;
      RetrieveImages();
    }
  });

  // Alt+click toggles filled/outline (keeps middle click as an alt path)
  panelEl?.addEventListener("mousedown", (e) => {
    const chip = e.target.closest(".chip");
    if (!chip) return;
    const idx = Number(chip.dataset.idx);
    if (Number.isNaN(idx)) return;

    if (e.altKey || e.button === 1) {
      e.preventDefault();
      const cur = state.labels[idx];
      cur.style = cur.style === "filled" ? "outline" : "filled";
      save(); render();
    }
  });

  // Double‑click to rename
  panelEl?.addEventListener("dblclick", (e) => {
    const chip = e.target.closest(".chip");
    if (!chip) return;
    const idx = Number(chip.dataset.idx);
    const current = state.labels[idx]?.text || "";
    const next = prompt("Edit label:", current);
    if (next == null) return; // cancelled
    const trimmed = next.trim();
    if (trimmed) state.labels[idx].text = trimmed;
    save(); render();
  });

  // Name field: prevent line breaks / rich paste, save on input
  nameEl?.addEventListener("beforeinput", (e) => {
    if (e.inputType === "insertLineBreak") e.preventDefault();
  });
  nameEl?.addEventListener("paste", (e) => {
    e.preventDefault();
    const text = (e.clipboardData || window.clipboardData).getData("text/plain") || "";
    document.execCommand("insertText", false, text.replace(/\r?\n|\r/g, " "));
  });
  nameEl?.addEventListener("input", () => {
    state.name = (nameEl.textContent || "").trim();
    save();
  });
  nameEl?.addEventListener("blur", () => {
    state.name = (nameEl.textContent || "Unnamed").trim();
    save();
  });

  // init
  render();
});



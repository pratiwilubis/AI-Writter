// Story Memory - logika tampilan.
// Semua data cerita disimpan lewat server.py ke file story.json.

const $ = (selector) => document.querySelector(selector);

let story = {
  title: "Ceritaku",
  bible: "",
  chapters: [{ title: "Bab 1", text: "", summary: "" }],
};
let current = 0;
let saveTimer = null;

// ---------- util ----------

function setStatus(text, kind = "") {
  const el = $("#status");
  el.textContent = text;
  el.className = "status " + kind;
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  let data = {};
  try {
    data = await response.json();
  } catch (_) {
    /* abaikan */
  }
  if (!response.ok) {
    throw new Error(data.error || "Terjadi kesalahan (" + response.status + ")");
  }
  return data;
}

function scheduleSave() {
  setStatus("Menyimpan...", "busy");
  clearTimeout(saveTimer);
  saveTimer = setTimeout(saveNow, 600);
}

async function saveNow() {
  clearTimeout(saveTimer);
  try {
    await api("/api/story", { method: "POST", body: JSON.stringify(story) });
    setStatus("Tersimpan");
  } catch (err) {
    setStatus("Gagal menyimpan", "error");
    console.error(err);
  }
}

function selectedModel() {
  return $("#modelSelect").value || undefined;
}

// ---------- tampilan ----------

function renderChapterList() {
  const list = $("#chapterList");
  list.innerHTML = "";
  story.chapters.forEach((chapter, index) => {
    const li = document.createElement("li");
    li.textContent = chapter.title || "Bab " + (index + 1);
    if (chapter.summary && chapter.summary.trim()) {
      const tag = document.createElement("span");
      tag.className = "tag";
      tag.textContent = "diringkas";
      li.appendChild(tag);
    }
    if (index === current) li.classList.add("active");
    li.addEventListener("click", () => selectChapter(index));
    list.appendChild(li);
  });
}

function renderEditor() {
  const chapter = story.chapters[current];
  $("#storyTitle").value = story.title || "";
  $("#bible").value = story.bible || "";
  $("#chapterTitle").value = chapter.title || "";
  $("#chapterText").value = chapter.text || "";
  $("#summary").value = chapter.summary || "";
}

function selectChapter(index) {
  current = index;
  hidePreview();
  renderChapterList();
  renderEditor();
}

// ---------- hasil AI (preview) ----------

function showPreview(text) {
  $("#previewText").value = text;
  $("#preview").classList.remove("hidden");
}

function hidePreview() {
  $("#preview").classList.add("hidden");
  $("#previewText").value = "";
}

async function askAI() {
  const button = $("#writeBtn");
  const retry = $("#retryBtn");
  button.disabled = true;
  retry.disabled = true;
  setStatus("AI sedang menulis...", "busy");
  try {
    await saveNow(); // pastikan server memegang versi terbaru
    const data = await api("/api/write", {
      method: "POST",
      body: JSON.stringify({
        chapter: current,
        instruction: $("#instruction").value,
        model: selectedModel(),
      }),
    });
    showPreview(data.text);
    setStatus("Selesai");
  } catch (err) {
    setStatus(err.message, "error");
  } finally {
    button.disabled = false;
    retry.disabled = false;
  }
}

function acceptPreview() {
  const addition = $("#previewText").value.trim();
  if (!addition) return;
  const chapter = story.chapters[current];
  const separator = chapter.text && !chapter.text.endsWith("\n") ? "\n\n" : "";
  chapter.text = (chapter.text || "") + separator + addition + "\n";
  $("#chapterText").value = chapter.text;
  $("#instruction").value = "";
  hidePreview();
  scheduleSave();
}

async function summarize() {
  const button = $("#summarizeBtn");
  button.disabled = true;
  setStatus("AI sedang merangkum...", "busy");
  try {
    await saveNow();
    const data = await api("/api/summarize", {
      method: "POST",
      body: JSON.stringify({ chapter: current, model: selectedModel() }),
    });
    story.chapters[current].summary = data.summary;
    $("#summary").value = data.summary;
    renderChapterList();
    scheduleSave();
    setStatus("Ringkasan dibuat");
  } catch (err) {
    setStatus(err.message, "error");
  } finally {
    button.disabled = false;
  }
}

// ---------- bab ----------

function addChapter() {
  story.chapters.push({
    title: "Bab " + (story.chapters.length + 1),
    text: "",
    summary: "",
  });
  selectChapter(story.chapters.length - 1);
  scheduleSave();
}

function deleteChapter() {
  if (story.chapters.length === 1) {
    alert("Minimal harus ada satu bab.");
    return;
  }
  const name = story.chapters[current].title || "bab ini";
  if (!confirm('Hapus "' + name + '"? Ini tidak bisa dibatalkan.')) return;
  story.chapters.splice(current, 1);
  current = Math.max(0, current - 1);
  selectChapter(current);
  scheduleSave();
}

// ---------- model ----------

async function loadModels() {
  const select = $("#modelSelect");
  try {
    const data = await api("/api/models");
    select.innerHTML = "";
    if (data.models.length === 0) {
      select.innerHTML = "<option value=''>(belum ada model)</option>";
      setStatus("Belum ada model di Ollama. Lihat README.", "error");
      return;
    }
    data.models.forEach((name) => {
      const option = document.createElement("option");
      option.value = name;
      option.textContent = name;
      select.appendChild(option);
    });
    if (data.models.includes(data.default)) select.value = data.default;
  } catch (err) {
    select.innerHTML = "<option value=''>(Ollama tidak terdeteksi)</option>";
    setStatus(err.message, "error");
  }
}

// ---------- mulai ----------

function bindEvents() {
  $("#storyTitle").addEventListener("input", (e) => {
    story.title = e.target.value;
    scheduleSave();
  });
  $("#bible").addEventListener("input", (e) => {
    story.bible = e.target.value;
    scheduleSave();
  });
  $("#chapterTitle").addEventListener("input", (e) => {
    story.chapters[current].title = e.target.value;
    renderChapterList();
    scheduleSave();
  });
  $("#chapterText").addEventListener("input", (e) => {
    story.chapters[current].text = e.target.value;
    scheduleSave();
  });
  $("#summary").addEventListener("input", (e) => {
    story.chapters[current].summary = e.target.value;
    renderChapterList();
    scheduleSave();
  });

  $("#addChapter").addEventListener("click", addChapter);
  $("#deleteChapter").addEventListener("click", deleteChapter);
  $("#writeBtn").addEventListener("click", askAI);
  $("#retryBtn").addEventListener("click", askAI);
  $("#acceptBtn").addEventListener("click", acceptPreview);
  $("#discardBtn").addEventListener("click", hidePreview);
  $("#summarizeBtn").addEventListener("click", summarize);
  $("#instruction").addEventListener("keydown", (e) => {
    if (e.key === "Enter") askAI();
  });
}

async function init() {
  bindEvents();
  if (location.protocol === "file:") {
    setStatus("Buka lewat http://localhost:8000 (jalankan python server.py), bukan klik dua kali file ini.", "error");
    return;
  }
  try {
    story = await api("/api/story");
    if (!story.chapters || story.chapters.length === 0) {
      story.chapters = [{ title: "Bab 1", text: "", summary: "" }];
    }
  } catch (err) {
    setStatus(err.message, "error");
  }
  current = 0;
  renderChapterList();
  renderEditor();
  loadModels();
}

init();

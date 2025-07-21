const editor = document.getElementById("editor");
const fileInput = document.getElementById("fileInput");

// Generate or retrieve a note ID from the URL hash
if (!location.hash) {
  const id = crypto.randomUUID();
  location.hash = id;
}
const noteId = location.hash.substring(1); // strip '#'

// Load existing content
const savedNote = localStorage.getItem("note-" + noteId);
if (savedNote !== null) editor.value = savedNote;

// Save on input
editor.addEventListener("input", () => {
  localStorage.setItem("note-" + noteId, editor.value);
});

// Save to file
function saveFile() {
  const blob = new Blob([editor.value], { type: "text/plain" });
  const link = document.createElement("a");
  link.download = "note.txt";
  link.href = URL.createObjectURL(blob);
  link.click();
}

// Load from file
function loadFile() {
  fileInput.click();
}

fileInput.addEventListener("change", () => {
  const file = fileInput.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = (e) => {
    editor.value = e.target.result;
    localStorage.setItem("note-" + noteId, editor.value);
  };
  reader.readAsText(file);
});

// Dark mode
function applyDarkMode(mode) {
  document.body.classList.toggle("dark", mode === "dark");
}

function toggleDarkMode() {
  const current =
    localStorage.getItem("pref-theme") === "dark" ? "light" : "dark";
  localStorage.setItem("pref-theme", current);
  applyDarkMode(current);
}

// Load saved dark mode preference
applyDarkMode(localStorage.getItem("pref-theme") || "light");

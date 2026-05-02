/* ─── Jack AI — Frontend App ─────────────────────────────────────────────── */

// Detect API URL (useful for cloud deployment)
const API = window.location.origin.includes("localhost") || window.location.origin.includes("127.0.0.1") 
  ? "http://localhost:8000" 
  : window.location.origin;

// ─── State ───────────────────────────────────────────────────────────────────
let state = {
  users: [],
  activeUser: null,
  isRecording: false,
  mediaRecorder: null,
  audioChunks: [],
  selectedEmoji: "🧑",
  silenceTimer: null,
  currentAudio: null,
  theme: localStorage.getItem("jack-theme") || "dark"
};

// ─── DOM refs ────────────────────────────────────────────────────────────────
const $ = (id) => document.getElementById(id);
const userList       = $("userList");
const interestsPanel = $("interestsPanel");
const interestsList  = $("interestsList");
const messages       = $("messages");
const textInput      = $("textInput");
const btnSend        = $("btnSend");
const btnMic         = $("btnMic");
const btnAddUser     = $("btnAddUser");
const btnCancel      = $("btnCancel");
const btnCreate      = $("btnCreate");
const btnEndSession  = $("btnEndSession");
const modalOverlay   = $("modalOverlay");
const menuToggle     = $("menuToggle");
const sidebar        = $("sidebar");
const statusDot      = $("statusDot");
const statusText     = $("statusText");
const activeAvatar   = $("activeAvatar");
const activeName     = $("activeName");
const activeSub      = $("activeSub");
const emojiPicker    = $("emojiPicker");

// ─── Init ─────────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", async () => {
  initTheme();
  await loadUsers();
  
  // Per-device session: Auto-select last user
  const lastUserId = localStorage.getItem("last-user-id");
  if (lastUserId && state.users.length) {
    const lastUser = state.users.find(u => u.id === lastUserId);
    if (lastUser) selectUser(lastUser);
  }

  bindEvents();
});

// ─── Load Users ───────────────────────────────────────────────────────────────
async function loadUsers() {
  try {
    setStatus("Loading...", "busy");
    const res = await fetch(`${API}/api/users`);
    state.users = await res.json();
    renderUserList();
    setStatus("Ready", "idle");
  } catch (e) {
    setStatus("Server offline", "error");
    renderUserList(); // still render empty state
  }
}

function renderUserList() {
  userList.innerHTML = "";
  if (!state.users.length) {
    userList.innerHTML = `<p style="font-size:12px;color:var(--text-3);padding:4px 0">No one added yet — add a person below!</p>`;
    return;
  }
  state.users.forEach((u) => {
    const card = document.createElement("div");
    card.className = "user-card" + (state.activeUser?.id === u.id ? " active" : "");
    card.id = `user-${u.id}`;
    card.innerHTML = `
      <div class="user-avatar">${u.avatar_emoji}</div>
      <div class="user-info">
        <div class="user-card-name">${u.name}</div>
        <div class="user-card-sub">${u.age}y · ${u.gender} · ${u.interests_count} interests</div>
      </div>
    `;
    card.addEventListener("click", () => selectUser(u));
    userList.appendChild(card);
  });
}

// ─── Select Active User ───────────────────────────────────────────────────────
function selectUser(user) {
  state.activeUser = user;
  localStorage.setItem("last-user-id", user.id); // Save for next time on this device
  
  document.querySelectorAll(".user-card").forEach((c) => c.classList.remove("active"));
  const card = $(`user-${user.id}`);
  if (card) card.classList.add("active");

  // Update header
  activeAvatar.textContent = user.avatar_emoji;
  activeName.textContent   = user.name;
  activeSub.textContent    = `${user.age}-year-old ${user.gender} · ${user.language}`;

  // Load history
  loadChatHistory(user.id);
  
  // Load + show interests
  loadInterests(user.id);

  // Close sidebar on mobile
  sidebar.classList.remove("open");
}

// ─── Load Chat History ────────────────────────────────────────────────────────
async function loadChatHistory(userId) {
  try {
    messages.innerHTML = "";
    const res = await fetch(`${API}/api/chat/history/${userId}`);
    const history = await res.json();
    
    if (history.length === 0) {
      appendJackMessage(
        `Hey ${state.activeUser.name}! 👋 I'm Jack, I'm so happy to chat with you. What's on your mind?`,
        null
      );
    } else {
      history.forEach(msg => {
        if (msg.role === "user") {
          appendUserMessage(msg.content);
        } else {
          appendJackMessage(msg.content, null);
        }
      });
    }
  } catch (e) {
    console.error("Failed to load history", e);
  }
}

// ─── Load & Render Interests ─────────────────────────────────────────────────
async function loadInterests(userId) {
  try {
    const res  = await fetch(`${API}/api/interests/${userId}`);
    const data = await res.json();
    const list = data.interests || [];

    if (!list.length) {
      interestsPanel.style.display = "none";
      return;
    }
    interestsPanel.style.display = "flex";
    interestsList.innerHTML = "";

    list.slice(0, 8).forEach((item) => {
      const pct = Math.round((item.intensity || 0) * 100);
      const row = document.createElement("div");
      row.className = "interest-item";
      row.innerHTML = `
        <span style="max-width:90px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${item.topic}">${item.topic}</span>
        <div class="interest-bar-wrap">
          <div class="interest-bar" style="width:${pct}%"></div>
        </div>
        <span class="interest-score">${pct}%</span>
      `;
      interestsList.appendChild(row);
    });

    // Show news badges for interests with fresh news
    list.filter((i) => i.latest_news).slice(0, 2).forEach((i) => {
      appendNewsBadge(`📰 ${i.topic}: ${i.latest_news}`);
    });
  } catch (e) {
    interestsPanel.style.display = "none";
  }
}

// ─── Chat ─────────────────────────────────────────────────────────────────────
async function sendMessage(text) {
  if (!text.trim()) return;
  if (!state.activeUser) { showNoUserWarning(); return; }

  appendUserMessage(text);
  textInput.value = "";

  const typingEl = appendTypingIndicator();
  setStatus("Jack is thinking...", "busy");

  try {
    const res = await fetch(`${API}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: state.activeUser.id,
        message: text,
        return_audio: true,
      }),
    });
    const data = await res.json();
    typingEl.remove();

    appendJackMessage(data.reply, data.audio_url);

    // Refresh interests after chat (non-blocking)
    loadInterests(state.activeUser.id);

    setStatus("Ready", "idle");

    // Auto-play audio
    if (data.audio_url) {
      playAudio(`${API}${data.audio_url}`);
    }

    // Reset silence timer for session-end detection (30s)
    resetSilenceTimer();

  } catch (e) {
    typingEl.remove();
    appendJackMessage("Hmm, I had a little hiccup. Try again in a sec! 😅", null);
    setStatus("Error", "error");
    setTimeout(() => setStatus("Ready", "idle"), 3000);
  }
}

// ─── Audio Recording ──────────────────────────────────────────────────────────
async function startRecording() {
  if (!state.activeUser) { showNoUserWarning(); return; }
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    state.audioChunks  = [];
    state.mediaRecorder = new MediaRecorder(stream, { mimeType: "audio/webm" });

    state.mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) state.audioChunks.push(e.data);
    };

    state.mediaRecorder.onstop = async () => {
      stream.getTracks().forEach((t) => t.stop());
      const blob = new Blob(state.audioChunks, { type: "audio/webm" });
      await transcribeAndSend(blob);
    };

    state.mediaRecorder.start();
    state.isRecording = true;
    btnMic.classList.add("recording");
    btnMic.querySelector(".mic-icon").textContent = "⏹";
    setStatus("Listening...", "busy");
  } catch (e) {
    appendJackMessage("I couldn't access your mic. Please allow microphone permission! 🎤", null);
  }
}

function stopRecording() {
  if (state.mediaRecorder && state.isRecording) {
    state.mediaRecorder.stop();
    state.isRecording = false;
    btnMic.classList.remove("recording");
    btnMic.querySelector(".mic-icon").textContent = "🎤";
    setStatus("Processing...", "busy");
  }
}

async function transcribeAndSend(blob) {
  // Send audio blob to browser's Web Speech API (client-side STT)
  // For now we use Web Speech API — later we can swap to Whisper via backend
  const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
  recognition.lang  = state.activeUser?.language === "hi" ? "hi-IN" : "en-IN";
  recognition.continuous = false;
  recognition.interimResults = false;

  // Replay blob to recognition (hack for recorded audio)
  // Better approach: send blob to /api/transcribe endpoint (Whisper)
  // For Sprint 1 we use live recognition instead
  setStatus("Ready", "idle");
  appendJackMessage("(Mic transcription: use the live mic button — hold to record, release to send)", null);
}

// ─── Live Speech Recognition (Web Speech API) ────────────────────────────────
let recognition = null;

function startSpeechRecognition() {
  if (!state.activeUser) { showNoUserWarning(); return; }

  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    appendJackMessage("Your browser doesn't support speech recognition. Please type instead!", null);
    return;
  }

  recognition = new SpeechRecognition();
  recognition.lang = state.activeUser?.language === "hi" ? "hi-IN" : "en-IN";
  recognition.continuous      = false;
  recognition.interimResults  = false;
  recognition.maxAlternatives = 1;

  recognition.onresult = (e) => {
    const transcript = e.results[0][0].transcript;
    sendMessage(transcript);
  };

  recognition.onerror = (e) => {
    setStatus("Ready", "idle");
    btnMic.classList.remove("recording");
    btnMic.querySelector(".mic-icon").textContent = "🎤";
    if (e.error !== "no-speech") {
      appendJackMessage("I didn't catch that — try again! 🎤", null);
    }
  };

  recognition.onend = () => {
    state.isRecording = false;
    btnMic.classList.remove("recording");
    btnMic.querySelector(".mic-icon").textContent = "🎤";
    setStatus("Ready", "idle");
  };

  recognition.start();
  state.isRecording = true;
  btnMic.classList.add("recording");
  btnMic.querySelector(".mic-icon").textContent = "⏹";
  setStatus("Listening...", "busy");
}

function stopSpeechRecognition() {
  if (recognition) {
    recognition.stop();
    recognition = null;
  }
}

// ─── Audio Playback ───────────────────────────────────────────────────────────
function playAudio(url) {
  if (state.currentAudio) {
    state.currentAudio.pause();
    state.currentAudio = null;
  }
  const audio = new Audio(url);
  state.currentAudio = audio;
  audio.play().catch(() => {}); // autoplay may be blocked
}

// ─── Session End ──────────────────────────────────────────────────────────────
function resetSilenceTimer() {
  clearTimeout(state.silenceTimer);
  // After 5 minutes of no messages, auto-end session (background memory write)
  state.silenceTimer = setTimeout(() => {
    if (state.activeUser) endSession(true);
  }, 5 * 60 * 1000);
}

async function endSession(auto = false) {
  if (!state.activeUser) return;
  try {
    await fetch(`${API}/api/session/end`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: state.activeUser.id }),
    });
    if (!auto) {
      appendJackMessage("Session saved! I'll remember everything we talked about. 💾", null);
      loadInterests(state.activeUser.id);
    }
  } catch (e) {}
}

// ─── Render Helpers ───────────────────────────────────────────────────────────
function appendUserMessage(text) {
  const el = document.createElement("div");
  el.className = "msg user";
  el.innerHTML = `
    <div class="msg-avatar">${state.activeUser?.avatar_emoji || "👤"}</div>
    <div class="msg-bubble">${escHtml(text)}</div>
  `;
  messages.appendChild(el);
  scrollBottom();
}

function appendJackMessage(text, audioUrl) {
  const el = document.createElement("div");
  el.className = "msg jack";
  const playBtn = audioUrl
    ? `<div class="play-btn" onclick="playAudio('${API}${audioUrl}')">▶ Play voice</div>`
    : "";
  el.innerHTML = `
    <div class="msg-avatar">🤖</div>
    <div class="msg-bubble">${escHtml(text)}${playBtn}</div>
  `;
  messages.appendChild(el);
  scrollBottom();
}

function appendTypingIndicator() {
  const el = document.createElement("div");
  el.className = "msg jack typing-indicator";
  el.innerHTML = `
    <div class="msg-avatar">🤖</div>
    <div class="msg-bubble">
      <div class="typing-dot"></div>
      <div class="typing-dot"></div>
      <div class="typing-dot"></div>
    </div>
  `;
  messages.appendChild(el);
  scrollBottom();
  return el;
}

function appendNewsBadge(text) {
  const el = document.createElement("div");
  el.className = "news-badge";
  el.textContent = text;
  messages.appendChild(el);
  scrollBottom();
}

function showNoUserWarning() {
  appendJackMessage("Hey! Please select or add a person from the sidebar first 👈", null);
}

function scrollBottom() {
  messages.scrollTop = messages.scrollHeight;
}

// ─── Theme ────────────────────────────────────────────────────────────────────
function initTheme() {
  if (state.theme === "light") {
    document.body.classList.add("light-theme");
  }
}

function toggleTheme() {
  state.theme = state.theme === "dark" ? "light" : "dark";
  document.body.classList.toggle("light-theme");
  localStorage.setItem("jack-theme", state.theme);
}

function escHtml(text) {
  return text
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/\n/g, "<br>");
}

// ─── Status ───────────────────────────────────────────────────────────────────
function setStatus(text, mode = "idle") {
  statusText.textContent = text;
  statusDot.className    = "status-dot" + (mode !== "idle" ? ` ${mode}` : "");
}

// ─── Add User Modal ───────────────────────────────────────────────────────────
function openModal() {
  modalOverlay.classList.add("open");
  $("inputName").focus();
}

function closeModal() {
  modalOverlay.classList.remove("open");
  $("inputName").value = "";
  $("inputAge").value  = "";
  state.selectedEmoji  = "🧑";
  document.querySelectorAll(".emoji-picker span").forEach((s) => s.classList.remove("selected"));
}

async function createUser() {
  const name   = $("inputName").value.trim();
  const age    = parseInt($("inputAge").value);
  const gender = $("inputGender").value;
  const lang   = $("inputLanguage").value;

  if (!name || !age) {
    $("inputName").style.borderColor = name ? "" : "var(--red)";
    $("inputAge").style.borderColor  = age  ? "" : "var(--red)";
    return;
  }

  btnCreate.textContent = "Adding...";
  btnCreate.disabled    = true;

  try {
    const res = await fetch(`${API}/api/users`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name, age, gender,
        language: lang,
        avatar_emoji: state.selectedEmoji,
      }),
    });
    const data = await res.json();
    closeModal();
    await loadUsers();
    // Auto-select the new user
    const newUser = state.users.find((u) => u.id === data.id);
    if (newUser) selectUser(newUser);
  } catch (e) {
    appendJackMessage("Couldn't create the user — is the server running?", null);
  } finally {
    btnCreate.textContent = "Add to Jack ✨";
    btnCreate.disabled    = false;
  }
}

// ─── Event Bindings ───────────────────────────────────────────────────────────
function bindEvents() {
  // Send text
  btnSend.addEventListener("click", () => sendMessage(textInput.value));
  textInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(textInput.value);
    }
  });

  // Mic — click to toggle
  btnMic.addEventListener("click", () => {
    if (state.isRecording) {
      stopSpeechRecognition();
    } else {
      startSpeechRecognition();
    }
  });

  // Add user
  btnAddUser.addEventListener("click", openModal);
  btnCancel.addEventListener("click", closeModal);
  modalOverlay.addEventListener("click", (e) => { if (e.target === modalOverlay) closeModal(); });
  btnCreate.addEventListener("click", createUser);
  $("inputName").addEventListener("keydown", (e) => { if (e.key === "Enter") $("inputAge").focus(); });
  $("inputAge").addEventListener("keydown",  (e) => { if (e.key === "Enter") createUser(); });

  // Emoji picker
  emojiPicker.querySelectorAll("span").forEach((span) => {
    span.addEventListener("click", () => {
      emojiPicker.querySelectorAll("span").forEach((s) => s.classList.remove("selected"));
      span.classList.add("selected");
      state.selectedEmoji = span.dataset.emoji;
    });
  });

  // End session
  btnEndSession.addEventListener("click", () => endSession(false));

  // Theme toggle
  $("themeToggleBtn").addEventListener("click", toggleTheme);

  // Mobile sidebar toggle
  menuToggle.addEventListener("click", () => sidebar.classList.toggle("open"));

  // Close sidebar when clicking outside on mobile
  document.addEventListener("click", (e) => {
    if (window.innerWidth <= 680 && !sidebar.contains(e.target) && e.target !== menuToggle) {
      sidebar.classList.remove("open");
    }
  });
}

// Expose playAudio globally for inline onclick handlers
window.playAudio = playAudio;

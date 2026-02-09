/**
 * MediScope Frontend Application
 * Enhanced error handling and user feedback
 */

// DOM Elements
const elements = {
  healthStatus: document.getElementById("health-status"),
  chatWindow: document.getElementById("chat-window"),
  clearChat: document.getElementById("clear-chat"),
  sendBtn: document.getElementById("send-btn"),
  userMessage: document.getElementById("user-message"),
  imageInput: document.getElementById("image-input"),
  imageQuestion: document.getElementById("image-question"),
  analyzeImage: document.getElementById("analyze-image"),
  imageInsights: document.getElementById("image-insights"),
  safetyNotice: document.getElementById("safety-notice"),
  playTts: document.getElementById("play-tts"),
  recordBtn: document.getElementById("record-btn"),
  stopBtn: document.getElementById("stop-btn"),
  audioInput: document.getElementById("audio-input"),
  transcribeAudio: document.getElementById("transcribe-audio"),
};

// Application state
const state = {
  lastAssistantMessage: "",
  imageText: "",
  imageAnswer: "",
  recorder: null,
  recordedChunks: [],
  isProcessing: false,
};

/**
 * Display error message to user
 */
function showError(message, context = "") {
  const fullMessage = context ? `${context}: ${message}` : message;
  console.error(fullMessage);
  
  const errorBubble = document.createElement("div");
  errorBubble.className = "chat-bubble assistant error";
  errorBubble.textContent = `❌ ${message}`;
  elements.chatWindow.appendChild(errorBubble);
  elements.chatWindow.scrollTop = elements.chatWindow.scrollHeight;
}

/**
 * Display success message
 */
function showSuccess(message) {
  console.log(message);
  elements.safetyNotice.textContent = `✓ ${message}`;
  elements.safetyNotice.style.color = "#22c55e";
  
  // Reset color after 3 seconds
  setTimeout(() => {
    elements.safetyNotice.style.color = "";
  }, 3000);
}

/**
 * Display loading indicator
 */
function showLoading(target, message = "Processing...") {
  if (target) {
    target.textContent = `⏳ ${message}`;
    target.classList.add("loading");
  }
}

/**
 * Hide loading indicator
 */
function hideLoading(target) {
  if (target) {
    target.classList.remove("loading");
  }
}

/**
 * Append message to chat
 */
function appendMessage(text, type = "assistant") {
  const bubble = document.createElement("div");
  bubble.className = `chat-bubble ${type}`;
  bubble.textContent = text;
  elements.chatWindow.appendChild(bubble);
  elements.chatWindow.scrollTop = elements.chatWindow.scrollHeight;
}

/**
 * Make API request with error handling
 */
async function apiRequest(url, options = {}) {
  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        ...options.headers,
      },
    });

    if (!response.ok) {
      let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
      
      try {
        const errorData = await response.json();
        errorMessage = errorData.message || errorMessage;
      } catch (e) {
        // Failed to parse error JSON, use default message
      }
      
      throw new Error(errorMessage);
    }

    return response;
  } catch (error) {
    if (error.name === "TypeError" && error.message.includes("fetch")) {
      throw new Error("Network error. Please check your connection.");
    }
    throw error;
  }
}

/**
 * Check API health
 */
async function checkHealth() {
  try {
    const response = await apiRequest("/api/health");
    const payload = await response.json();
    
    elements.healthStatus.textContent = `API ${payload.status} (v${payload.version})`;
    elements.healthStatus.style.color = "#22c55e";
    
    console.log("Health check successful:", payload);
  } catch (error) {
    elements.healthStatus.textContent = "API offline";
    elements.healthStatus.style.color = "#ef4444";
    console.error("Health check failed:", error);
  }
}

/**
 * Analyze image
 */
async function analyzeImageRequest() {
  if (state.isProcessing) {
    showError("Please wait for the current operation to complete");
    return;
  }

  if (!elements.imageInput.files.length) {
    elements.imageInsights.textContent = "❌ Please select an image first.";
    return;
  }

  const file = elements.imageInput.files[0];
  
  // Validate file size (20MB max)
  const maxSize = 20 * 1024 * 1024;
  if (file.size > maxSize) {
    elements.imageInsights.textContent = `❌ Image too large (${(file.size / 1024 / 1024).toFixed(2)}MB). Max size is 20MB.`;
    return;
  }

  // Validate file type
  if (!file.type.startsWith("image/")) {
    elements.imageInsights.textContent = "❌ Please select a valid image file.";
    return;
  }

  state.isProcessing = true;
  showLoading(elements.imageInsights, "Analyzing image...");
  elements.analyzeImage.disabled = true;

  try {
    const form = new FormData();
    form.append("file", file);
    
    if (elements.imageQuestion.value.trim()) {
      form.append("question", elements.imageQuestion.value.trim());
    }

    const response = await apiRequest("/api/vision", {
      method: "POST",
      body: form,
    });

    const payload = await response.json();
    state.imageText = payload.ocr_text || "";
    state.imageAnswer = payload.answer || "";

    const summaryParts = [];
    if (state.imageText) {
      summaryParts.push(`📄 OCR: ${state.imageText}`);
    }
    if (state.imageAnswer) {
      summaryParts.push(`💬 Answer: ${state.imageAnswer}`);
    }

    if (summaryParts.length > 0) {
      elements.imageInsights.textContent = summaryParts.join("\n\n");
      showSuccess("Image analyzed successfully");
    } else {
      elements.imageInsights.textContent = "No insights extracted from image.";
    }
  } catch (error) {
    elements.imageInsights.textContent = `❌ ${error.message}`;
    showError(error.message, "Image analysis failed");
  } finally {
    state.isProcessing = false;
    hideLoading(elements.imageInsights);
    elements.analyzeImage.disabled = false;
  }
}

/**
 * Send chat message
 */
async function sendChat() {
  const message = elements.userMessage.value.trim();
  
  if (!message) {
    showError("Please enter a message");
    return;
  }

  if (state.isProcessing) {
    showError("Please wait for the current operation to complete");
    return;
  }

  if (message.length > 10000) {
    showError("Message is too long (max 10000 characters)");
    return;
  }

  state.isProcessing = true;
  appendMessage(message, "user");
  elements.userMessage.value = "";
  elements.sendBtn.disabled = true;

  try {
    const response = await apiRequest("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message,
        image_text: state.imageText || null,
        image_answer: state.imageAnswer || null,
      }),
    });

    const payload = await response.json();
    state.lastAssistantMessage = payload.message || "";
    
    if (!state.lastAssistantMessage) {
      throw new Error("Empty response from assistant");
    }

    appendMessage(state.lastAssistantMessage, "assistant");

    // Display safety notices
    const notices = [];
    if (payload.urgent_notice) {
      notices.push(`⚠️ ${payload.urgent_notice}`);
    }
    if (payload.disclaimer) {
      notices.push(payload.disclaimer);
    }
    
    if (notices.length > 0) {
      elements.safetyNotice.textContent = notices.join("\n\n");
      if (payload.red_flag) {
        elements.safetyNotice.style.color = "#ef4444";
        elements.safetyNotice.style.fontWeight = "bold";
      }
    }

    // Clear image context after use
    if (state.imageText || state.imageAnswer) {
      state.imageText = "";
      state.imageAnswer = "";
      elements.imageInsights.textContent = "Image context used in chat.";
      showSuccess("Message sent with image context");
    }
  } catch (error) {
    showError(error.message, "Chat failed");
    appendMessage(`Failed to get response: ${error.message}`, "assistant");
  } finally {
    state.isProcessing = false;
    elements.sendBtn.disabled = false;
  }
}

/**
 * Play TTS
 */
async function playResponseTts() {
  if (!state.lastAssistantMessage) {
    showError("No response to synthesize yet");
    return;
  }

  if (state.isProcessing) {
    showError("Please wait for the current operation to complete");
    return;
  }

  state.isProcessing = true;
  elements.playTts.disabled = true;
  showLoading(elements.safetyNotice, "Synthesizing speech...");

  try {
    const response = await apiRequest("/api/tts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: state.lastAssistantMessage }),
    });

    const audioBlob = await response.blob();
    const url = URL.createObjectURL(audioBlob);
    const audio = new Audio(url);
    
    audio.onerror = () => {
      showError("Failed to play audio");
    };
    
    audio.onended = () => {
      URL.revokeObjectURL(url);
      showSuccess("Audio playback complete");
    };
    
    await audio.play();
  } catch (error) {
    showError(error.message, "TTS failed");
  } finally {
    state.isProcessing = false;
    elements.playTts.disabled = false;
    hideLoading(elements.safetyNotice);
  }
}

/**
 * Transcribe audio file
 */
async function transcribeAudioFile(file) {
  if (!file) {
    showError("No audio file selected");
    return;
  }

  if (state.isProcessing) {
    showError("Please wait for the current operation to complete");
    return;
  }

  // Validate file size (20MB max)
  const maxSize = 20 * 1024 * 1024;
  if (file.size > maxSize) {
    showError(`Audio too large (${(file.size / 1024 / 1024).toFixed(2)}MB). Max size is 20MB.`);
    return;
  }

  // Validate file type
  if (!file.type.startsWith("audio/")) {
    showError("Please select a valid audio file");
    return;
  }

  state.isProcessing = true;
  showLoading(elements.safetyNotice, "Transcribing audio...");

  try {
    const form = new FormData();
    form.append("file", file);

    const response = await apiRequest("/api/stt", {
      method: "POST",
      body: form,
    });

    const payload = await response.json();
    elements.userMessage.value = payload.text || "";
    showSuccess("Audio transcribed successfully");
  } catch (error) {
    showError(error.message, "Transcription failed");
  } finally {
    state.isProcessing = false;
    hideLoading(elements.safetyNotice);
  }
}

/**
 * Start recording
 */
async function startRecording() {
  if (state.isProcessing) {
    showError("Please wait for the current operation to complete");
    return;
  }

  try {
    state.recordedChunks = [];
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    
    state.recorder = new MediaRecorder(stream);
    
    state.recorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        state.recordedChunks.push(event.data);
      }
    };
    
    state.recorder.onstop = async () => {
      // Stop all tracks
      stream.getTracks().forEach(track => track.stop());
      
      const blob = new Blob(state.recordedChunks, { type: "audio/webm" });
      await transcribeAudioFile(blob);
    };
    
    state.recorder.start();
    elements.recordBtn.disabled = true;
    elements.stopBtn.disabled = false;
    showSuccess("Recording started");
  } catch (error) {
    showError(`Microphone access denied or unavailable: ${error.message}`);
  }
}

/**
 * Stop recording
 */
function stopRecording() {
  if (state.recorder && state.recorder.state !== "inactive") {
    state.recorder.stop();
    showSuccess("Recording stopped");
  }
  elements.recordBtn.disabled = false;
  elements.stopBtn.disabled = true;
}

/**
 * Clear chat
 */
function clearChatHistory() {
  elements.chatWindow.innerHTML = "";
  elements.safetyNotice.textContent = "No safety notices.";
  elements.safetyNotice.style.color = "";
  elements.safetyNotice.style.fontWeight = "";
  state.lastAssistantMessage = "";
  state.imageText = "";
  state.imageAnswer = "";
  showSuccess("Chat cleared");
}

// Event Listeners
elements.clearChat.addEventListener("click", clearChatHistory);

elements.sendBtn.addEventListener("click", sendChat);

elements.userMessage.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    sendChat();
  }
});

elements.analyzeImage.addEventListener("click", analyzeImageRequest);

elements.playTts.addEventListener("click", playResponseTts);

elements.recordBtn.addEventListener("click", startRecording);

elements.stopBtn.addEventListener("click", stopRecording);

elements.transcribeAudio.addEventListener("click", () => {
  const file = elements.audioInput.files[0];
  if (file) {
    transcribeAudioFile(file);
  } else {
    showError("Please select an audio file first");
  }
});

// Initialize
checkHealth();

// Periodic health check (every 30 seconds)
setInterval(checkHealth, 30000);

// Log application start
console.log("MediScope application initialized");

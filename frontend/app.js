// App State
let ws = null;
let currentWorkspace = "";
let activeModel = "";
let downloadCheckingIntervals = {};
let systemStatsInterval = null;
let conversationHistory = [];
let isGenerating = false;
let currentPromptText = "";
let currentSessionId = crypto.randomUUID();
let allSessions = [];

// DOM Elements
const connectionDot = document.getElementById("connection-dot");
const connectionText = document.getElementById("connection-text");
const workspaceInput = document.getElementById("workspace-input");
const updateWorkspaceBtn = document.getElementById("update-workspace-btn");
const workspaceDisplay = document.getElementById("workspace-display");
const modelSelector = document.getElementById("model-selector");
const recommendedModelsList = document.getElementById("recommended-models-list");
const customModelInput = document.getElementById("custom-model-input");
const downloadModelBtn = document.getElementById("download-model-btn");
const tempSlider = document.getElementById("temp-slider");
const tempVal = document.getElementById("temp-val");
const cpuStat = document.getElementById("cpu-stat");
const cpuBar = document.getElementById("cpu-bar");
const ramStat = document.getElementById("ram-stat");
const ramBar = document.getElementById("ram-bar");
const statsCoresDisplay = document.getElementById("stats-cores-display");
const activeModelHeader = document.getElementById("active-model-header");
// clearChatBtn removed
const chatHistory = document.getElementById("chat-history");
const welcomeScreen = document.getElementById("welcome-screen");
const agentProgressBar = document.getElementById("agent-progress-bar");
const agentProgressText = document.getElementById("agent-progress-text");
const chatInput = document.getElementById("chat-input");
const sendBtn = document.getElementById("send-btn");
const stopBtn = document.getElementById("stop-btn");
const micBtn = document.getElementById("mic-btn");
const siriBtn = document.getElementById("siri-btn");
const gmailEmailInput = document.getElementById("gmail-email-input");
const gmailPasswordInput = document.getElementById("gmail-password-input");
const saveGmailBtn = document.getElementById("save-gmail-btn");
const gmailDisplay = document.getElementById("gmail-display");

// New UI Elements
const settingsBtn = document.getElementById("settings-btn");
const settingsModal = document.getElementById("settings-modal");
const closeModalBtn = document.getElementById("close-modal-btn");
const newChatBtn = document.getElementById("new-chat-btn");
const workspaceChatNav = document.getElementById("workspace-chat-nav");

// 1. Initialize
document.addEventListener("DOMContentLoaded", () => {
    loadWorkspace();
    loadGmailConfig();
    loadModels();
    loadSessions();
    loadProjectOverview();
    connectWebSocket();
    startSystemStatsLoop();
    setupEventListeners();
});

// 2. Event Listeners
function setupEventListeners() {
    // Settings Modal
    settingsBtn.addEventListener("click", () => {
        settingsModal.classList.remove("hidden");
    });
    
    closeModalBtn.addEventListener("click", () => {
        settingsModal.classList.add("hidden");
    });
    
    // Close modal when clicking outside
    settingsModal.addEventListener("click", (e) => {
        if (e.target === settingsModal) {
            settingsModal.classList.add("hidden");
        }
    });

    // New Chat Button
    newChatBtn.addEventListener("click", () => {
        currentSessionId = crypto.randomUUID();
        conversationHistory = [];
        chatHistory.innerHTML = "";
        chatHistory.appendChild(welcomeScreen);
        welcomeScreen.style.display = "flex";
        activeModelHeader.textContent = activeModel ? `Active Model: ${activeModel}` : "No active model loaded.";
        document.getElementById('chat-input').value = "";
        renderSessionsList();
    });

    // Refresh Overview
    const refreshOverviewBtn = document.getElementById("refresh-overview-btn");
    if (refreshOverviewBtn) {
        refreshOverviewBtn.addEventListener("click", loadProjectOverview);
    }

    // Workspace
    updateWorkspaceBtn.addEventListener("click", updateWorkspace);
    workspaceInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") updateWorkspace();
    });

    // Gmail
    saveGmailBtn.addEventListener("click", saveGmailConfig);

    // Model Selector Change
    modelSelector.addEventListener("change", (e) => {
        const selected = e.target.value;
        if (selected) {
            activeModel = selected;
            activeModelHeader.textContent = `Active Model: ${activeModel}`;
            updateInputState();
            
            // Highlight card
            document.querySelectorAll(".model-card").forEach(card => {
                if (card.dataset.modelId === selected) {
                    card.classList.add("active-card");
                } else {
                    card.classList.remove("active-card");
                }
            });
        } else {
            activeModel = "";
            activeModelHeader.textContent = "No active model loaded. Download/select a model in the sidebar.";
            updateInputState();
        }
    });

    // Custom Download
    downloadModelBtn.addEventListener("click", () => {
        const repoId = customModelInput.value.trim();
        if (repoId) {
            triggerDownload(repoId);
            customModelInput.value = "";
        }
    });

    // Temperature Slider
    tempSlider.addEventListener("input", (e) => {
        tempVal.textContent = e.target.value;
    });

    // Send Message
    sendBtn.addEventListener("click", sendMessage);
    stopBtn.addEventListener("click", stopAgent);

    // Mic Button
    micBtn.addEventListener("click", toggleDictation);
    
    // Siri Mode Button
    let siriModeEnabled = false;
    siriBtn.addEventListener("click", () => {
        siriModeEnabled = !siriModeEnabled;
        if (siriModeEnabled) {
            siriBtn.classList.remove("siri-off");
            siriBtn.classList.add("siri-on");
        } else {
            siriBtn.classList.remove("siri-on");
            siriBtn.classList.add("siri-off");
            // Stop any active speech
            fetch('/api/stop-speak', { method: 'POST' }).catch(e => console.error(e));
        }
    });

    chatInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // Suggestions Clicking
    document.querySelectorAll(".suggestion-card").forEach(card => {
        card.addEventListener("click", () => {
            const prompt = card.dataset.prompt;
            chatInput.value = prompt;
            chatInput.focus();
            // Automatically adjust height
            chatInput.style.height = 'auto';
            chatInput.style.height = chatInput.scrollHeight + 'px';
        });
    });

    // Auto-expand textarea
    chatInput.addEventListener("input", function() {
        this.style.height = 'auto';
        this.style.height = this.scrollHeight + 'px';
    });

    // Clear Chat logic moved to newChatBtn
}

// 3. API Requests

async function stopAgent() {
    try {
        await fetch("/api/stop", { method: "POST" });
        await fetch("/api/stop-speak", { method: "POST" });
        stopBtn.classList.add("hidden");
    } catch (e) {
        console.error("Failed to stop agent", e);
    }
}

async function loadWorkspace() {
    try {
        const res = await fetch("/api/workspace");
        const data = await res.json();
        currentWorkspace = data.path;
        workspaceInput.value = currentWorkspace;
        workspaceDisplay.textContent = `Active: ${currentWorkspace}`;
    } catch (e) {
        console.error("Failed to load workspace", e);
        workspaceDisplay.textContent = "Active: Error loading";
    }
}

async function updateWorkspace() {
    const path = workspaceInput.value.trim();
    if (!path) return;
    try {
        const res = await fetch("/api/workspace", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ path })
        });
        const data = await res.json();
        currentWorkspace = data.path;
        workspaceDisplay.textContent = `Active: ${currentWorkspace}`;
        addSystemNotification(`Workspace updated to: ${currentWorkspace}`);
    } catch (e) {
        alert("Failed to update workspace path: " + e.message);
    }
}

async function loadGmailConfig() {
    try {
        const res = await fetch("/api/gmail-config");
        const data = await res.json();
        if (data.email) {
            gmailEmailInput.value = data.email;
            gmailDisplay.textContent = `Gmail: ${data.email} ✓`;
            gmailDisplay.style.color = "var(--color-success)";
        } else {
            gmailDisplay.textContent = "Gmail: Not configured";
            gmailDisplay.style.color = "var(--text-muted)";
        }
    } catch (e) {
        console.error("Failed to load Gmail config", e);
        gmailDisplay.textContent = "Gmail: Error loading";
    }
}

async function saveGmailConfig() {
    const emailAddr = gmailEmailInput.value.trim();
    const appPassword = gmailPasswordInput.value.trim();
    if (!emailAddr || !appPassword) {
        alert("Please enter both your Gmail address and App Password.");
        return;
    }
    try {
        const res = await fetch("/api/gmail-config", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email: emailAddr, app_password: appPassword })
        });
        const data = await res.json();
        if (data.status === "success") {
            gmailDisplay.textContent = `Gmail: ${data.email} ✓`;
            gmailDisplay.style.color = "var(--color-success)";
            gmailPasswordInput.value = "";
            addSystemNotification(`Gmail credentials saved for ${data.email}`);
        } else {
            alert("Failed to save Gmail config: " + JSON.stringify(data));
        }
    } catch (e) {
        alert("Failed to save Gmail config: " + e.message);
    }
}

async function loadModels() {
    try {
        const res = await fetch("/api/models");
        const data = await res.json();
        
        // Clear selector
        modelSelector.innerHTML = '<option value="">-- Select a local model --</option>';
        recommendedModelsList.innerHTML = "";
        
        const models = data.models;
        activeModel = data.active_model || "";
        
        // Auto-select first downloaded model if none is active
        if (!activeModel) {
            const firstDownloaded = models.find(m => m.downloaded);
            if (firstDownloaded) {
                activeModel = firstDownloaded.id;
            }
        }
        
        if (activeModel) {
            activeModelHeader.textContent = `Active Model: ${activeModel}`;
        }
        
        models.forEach(model => {
            // Populate selector if downloaded
            if (model.downloaded) {
                const opt = document.createElement("option");
                opt.value = model.id;
                opt.textContent = model.name;
                opt.selected = (model.id === activeModel);
                modelSelector.appendChild(opt);
            }
            
            // Build Model Cards in sidebar
            const card = document.createElement("div");
            card.className = `model-card ${model.id === activeModel ? 'active-card' : ''}`;
            card.dataset.modelId = model.id;
            
            let actionBtnHTML = "";
            let statusLabelHTML = "";
            
            if (model.downloaded) {
                statusLabelHTML = '<span class="download-status-label downloaded">Downloaded ✓</span>';
                actionBtnHTML = `<button class="btn-small select-model-btn" onclick="selectModel('${model.id}')">Select</button>`;
            } else {
                statusLabelHTML = '<span class="download-status-label">Not downloaded</span>';
                actionBtnHTML = `<button class="btn-small download-action-btn" data-model-id="${model.id}" onclick="triggerDownload('${model.id}')">Download</button>`;
            }
            
            card.innerHTML = `
                <div class="model-card-info">
                    <div class="model-card-name">${model.name}</div>
                    <div class="model-card-size">${model.size}</div>
                </div>
                <div class="model-card-desc">${model.description}</div>
                <div class="model-action-row">
                    ${statusLabelHTML}
                    ${actionBtnHTML}
                </div>
            `;
            
            recommendedModelsList.appendChild(card);
        });
        
        modelSelector.value = activeModel;
        updateInputState();
    } catch (e) {
        console.error("Failed to load models list", e);
        recommendedModelsList.innerHTML = '<div class="info-note" style="color:var(--color-error)">Failed to load models.</div>';
    }
}

function selectModel(modelId) {
    modelSelector.value = modelId;
    modelSelector.dispatchEvent(new Event('change'));
}

async function triggerDownload(modelId) {
    // Disable download buttons
    const btn = document.querySelector(`.download-action-btn[data-model-id="${modelId}"]`);
    if (btn) {
        btn.textContent = "Downloading...";
        btn.disabled = true;
        btn.classList.add("downloading-btn");
    }
    
    try {
        const res = await fetch("/api/download", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ model_id: modelId })
        });
        const data = await res.json();
        
        addSystemNotification(`Download request started for ${modelId}`);
        pollDownloadStatus(modelId);
    } catch (e) {
        alert("Failed to start download: " + e.message);
        loadModels(); // reset UI
    }
}

function pollDownloadStatus(modelId) {
    if (downloadCheckingIntervals[modelId]) return;
    
    // Periodically query endpoint for progress
    downloadCheckingIntervals[modelId] = setInterval(async () => {
        try {
            const res = await fetch(`/api/download/status?model_id=${encodeURIComponent(modelId)}`);
            const data = await res.json();
            
            const card = document.querySelector(`.model-card[data-model-id="${modelId}"]`);
            const label = card ? card.querySelector(".download-status-label") : null;
            const btn = card ? card.querySelector(".btn-small") : null;
            
            if (data.status === "downloading") {
                if (label) label.textContent = `Downloading (${data.progress}%)`;
                if (btn) {
                    btn.textContent = "Downloading...";
                    btn.disabled = true;
                    btn.className = "btn-small downloading-btn";
                }
            } else if (data.status === "completed") {
                clearInterval(downloadCheckingIntervals[modelId]);
                delete downloadCheckingIntervals[modelId];
                addSystemNotification(`Model download completed successfully: ${modelId}`);
                loadModels(); // reload lists to update states
            } else if (data.status === "failed") {
                clearInterval(downloadCheckingIntervals[modelId]);
                delete downloadCheckingIntervals[modelId];
                alert(`Download failed for ${modelId}: ${data.error}`);
                loadModels();
            }
        } catch (e) {
            console.error("Error polling download status", e);
        }
    }, 3000);
}

function startSystemStatsLoop() {
    systemStatsInterval = setInterval(async () => {
        try {
            const res = await fetch("/api/system-stats");
            const data = await res.json();
            
            cpuStat.textContent = `${data.cpu_load}%`;
            cpuBar.style.width = `${Math.min(data.cpu_load, 100)}%`;
            
            ramStat.textContent = `${data.ram_used_pct}%`;
            ramBar.style.width = `${data.ram_used_pct}%`;
            
            statsCoresDisplay.textContent = `Cores detected: ${data.cores} | CPU Mode: Metal GPU`;
        } catch (e) {
            console.error("Failed to fetch system stats", e);
        }
    }, 5000);
}

// 4. WebSocket Communication

function connectWebSocket() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}/api/ws`;
    
    ws = new WebSocket(wsUrl);
    
    ws.onopen = () => {
        connectionDot.className = "status-dot connected";
        connectionText.textContent = "Connected (Local)";
        updateInputState();
    };
    
    ws.onclose = () => {
        connectionDot.className = "status-dot disconnected";
        connectionText.textContent = "Disconnected (Retrying...)";
        updateInputState();
        // Reconnect in 3s
        setTimeout(connectWebSocket, 3000);
    };
    
    ws.onerror = (e) => {
        console.error("WS Error", e);
    };
    
    ws.onmessage = handleWebSocketMessage;
}

function updateInputState() {
    const connected = (ws && ws.readyState === WebSocket.OPEN);
    const modelReady = (activeModel !== "");
    const disabled = !connected || !modelReady || isGenerating;
    
    chatInput.disabled = disabled;
    sendBtn.disabled = disabled;
    
    if (isGenerating) {
        sendBtn.classList.add("hidden");
        stopBtn.classList.remove("hidden");
    } else {
        sendBtn.classList.remove("hidden");
        stopBtn.classList.add("hidden");
    }
    
    if (disabled) {
        if (!connected) {
            chatInput.placeholder = "Disconnected from backend server...";
        } else if (!modelReady) {
            chatInput.placeholder = "Select or download a model first...";
        } else {
            chatInput.placeholder = "Agent is working...";
        }
    } else {
        chatInput.placeholder = "Ask anything... (Shift+Enter for new line)";
    }
}

// 5. Chat Interaction
let recognition = null;
let isRecording = false;

function toggleDictation() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        chatInput.focus();
        alert("To use Voice Dictation on your Mac, simply press the 'Microphone' key (F5) or double-tap the 'Fn' key while typing in the chat box! Your Mac has a powerful, offline dictation engine built right in.");
        return;
    }
    
    if (isRecording) {
        if (recognition) recognition.stop();
        return;
    }
    
    try {
        recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = 'en-US';
        
        recognition.onstart = () => {
            isRecording = true;
            micBtn.classList.add("recording");
            chatInput.placeholder = "Listening...";
        };
        
        recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            chatInput.value = (chatInput.value + " " + transcript).trim();
            chatInput.dispatchEvent(new Event('input'));
        };
        
        recognition.onerror = (event) => {
            console.error("Speech recognition error:", event.error);
            stopDictationUI();
            if (event.error === 'not-allowed') {
                alert("Microphone permission denied. To use Voice Dictation, please allow microphone access in your System Settings, or press the 'Microphone' key (F5) / 'Fn' key twice.");
            }
        };
        
        recognition.onend = () => {
            stopDictationUI();
        };
        
        recognition.start();
    } catch (e) {
        console.error("Failed to initialize Speech Recognition:", e);
        chatInput.focus();
        alert("To use Voice Dictation on your Mac, simply press the 'Microphone' key (F5) or double-tap the 'Fn' key while typing in the chat box! Your Mac has a powerful, offline dictation engine built right in.");
    }
}
    
function stopDictationUI() {
    isRecording = false;
    micBtn.classList.remove("recording");
    chatInput.placeholder = "Ask anything...";
}

function sendMessage() {
    const text = chatInput.value.trim();
    if (!text || isGenerating || !activeModel) return;
    
    isGenerating = true;
    currentPromptText = text;
    updateInputState();
    
    // Hide welcome screen
    welcomeScreen.classList.add("hidden");
    
    // Append User Bubble
    appendUserBubble(text);
    
    // Setup Agent Bubble Placeholder
    createAgentBubble();
    
    // Show Progress Bar
    agentProgressBar.classList.remove("hidden");
    agentProgressText.textContent = "Agent starting...";
    
    // Send over WS
    const payload = {
        prompt: text,
        model_id: activeModel,
        temperature: parseFloat(tempSlider.value),
        history: conversationHistory
    };
    
    ws.send(JSON.stringify(payload));
    
    // Clear input box
    chatInput.value = "";
    chatInput.style.height = "auto";
}

// 6. Handling WebSocket Messages

let currentAgentBubble = null;
let currentThinkingContainer = null;
let currentThinkingContent = null;
let currentThoughtBlock = null;
let activeToolBlock = null;
let activeToolOutputContent = null;
let finalResponseText = "";
let currentFinalResponseBlock = null;

function handleWebSocketMessage(event) {
    const msg = JSON.parse(event.data);
    
    switch (msg.type) {
        case "turn_start":
            agentProgressText.textContent = `Loop ${msg.loop}: Reasoning...`;
            addThinkingBlock(msg.loop);
            break;
            
        case "thought":
            appendThought(msg.text);
            break;
            
        case "tool_start":
            agentProgressText.textContent = `Running tool: ${msg.name}...`;
            addToolCallBlock(msg.name, msg.args);
            break;
            
        case "tool_end":
            agentProgressText.textContent = `Tool ${msg.name} finished.`;
            completeToolCallBlock(msg.output, false);
            break;
            
        case "tool_error":
            agentProgressText.textContent = `Tool execution failed.`;
            completeToolCallBlock(msg.error, true);
            break;
            
        case "final_response":
            agentProgressText.textContent = "Writing final response...";
            renderFinalResponse(msg.text);
            break;
            
        case "error":
            showErrorBanner(msg.message);
            cleanupGenerationState();
            break;
            
        case "complete":
        default:
            // Final completion
            cleanupGenerationState();
            break;
    }
}

function cleanupGenerationState() {
    isGenerating = false;
    agentProgressBar.classList.add("hidden");
    updateInputState();
    
    // Save history & Trigger TTS
    if (currentFinalResponseBlock && currentFinalResponseBlock.dataset.rawContent) {
        const finalContent = currentFinalResponseBlock.dataset.rawContent;
        // Append to conversationHistory
        conversationHistory.push({ role: "user", content: currentPromptText });
        conversationHistory.push({ role: "assistant", content: finalContent });
        
        // Siri TTS Integration
        if (siriBtn.classList.contains("siri-on") && finalContent.trim().length > 0) {
            fetch("/api/speak", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ text: finalContent })
            }).catch(e => console.error("TTS Error:", e));
        }
        
        // Reveal Copy Button
        if (currentAgentBubble) {
            const copyBtn = currentAgentBubble.querySelector(".copy-msg-btn");
            if (copyBtn) copyBtn.classList.remove("hidden");
        }
        
        saveHistory();
    }
    
    // Reset state pointers
    currentAgentBubble = null;
    currentThinkingContainer = null;
    currentThinkingContent = null;
    currentThoughtBlock = null;
    activeToolBlock = null;
    activeToolOutputContent = null;
    currentFinalResponseBlock = null;
    finalResponseText = "";
}

// History & Session Management
async function loadSessions() {
    try {
        const res = await fetch("/api/sessions");
        const data = await res.json();
        allSessions = data.sessions || [];
        
        // If we have sessions but current is random (new load), load the most recent one
        if (allSessions.length > 0 && !allSessions.find(s => s.id === currentSessionId) && conversationHistory.length === 0) {
            currentSessionId = allSessions[0].id;
            await loadHistory(currentSessionId);
        }
        
        renderSessionsList();
    } catch (e) {
        console.error("Failed to load sessions", e);
    }
}

function renderSessionsList() {
    const listDiv = document.getElementById("recent-chats-list");
    if (!listDiv) return;
    
    listDiv.innerHTML = "";
    
    // Prepend the new unsaved chat if active
    let displaySessions = [...allSessions];
    if (!displaySessions.find(s => s.id === currentSessionId)) {
        const title = conversationHistory.length > 0 ? conversationHistory[0].content : "New Chat";
        displaySessions.unshift({ id: currentSessionId, title: title, history: conversationHistory });
    }
    
    displaySessions.forEach(session => {
        const item = document.createElement("button");
        item.className = `session-item ${session.id === currentSessionId ? "active" : ""}`;
        item.innerHTML = `
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
            </svg>
            <span>${escapeHTML(session.title || "New Chat")}</span>
        `;
        item.onclick = async () => {
            currentSessionId = session.id;
            chatHistory.innerHTML = "";
            chatHistory.appendChild(welcomeScreen);
            await loadHistory(currentSessionId);
            renderSessionsList();
        };
        listDiv.appendChild(item);
    });
}

async function loadHistory(sessionId) {
    if (!sessionId) return;
    try {
        const res = await fetch(`/api/history?session_id=${sessionId}`);
        const data = await res.json();
        conversationHistory = data.history || [];
        if (conversationHistory.length > 0) {
            renderLoadedHistory();
        } else {
            welcomeScreen.style.display = "flex";
        }
    } catch (e) {
        console.error("Failed to load history", e);
    }
}

async function saveHistory() {
    try {
        let title = "New Chat";
        if (conversationHistory.length > 0) {
            title = conversationHistory[0].content;
        }
        
        await fetch("/api/history", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ 
                session_id: currentSessionId,
                title: title,
                history: conversationHistory 
            })
        });
        loadSessions(); // refresh sidebar
    } catch (e) {
        console.error("Failed to save history", e);
    }
}

async function loadProjectOverview() {
    try {
        const res = await fetch("/api/project-overview");
        const data = await res.json();
        const contentDiv = document.getElementById("project-overview-content");
        if (contentDiv) {
            if (data.content.startsWith("No project_overview.md found") || data.content.startsWith("Error")) {
                contentDiv.innerHTML = `<div class="info-note" style="text-align:center; margin-top: 40px;">${data.content}</div>`;
            } else {
                contentDiv.innerHTML = parseMarkdown(data.content);
            }
        }
    } catch (e) {
        console.error("Failed to load project overview", e);
    }
}

function renderLoadedHistory() {
    welcomeScreen.style.display = "none";
    for (let i = 0; i < conversationHistory.length; i++) {
        const msg = conversationHistory[i];
        if (msg.role === "user") {
            appendUserBubble(msg.content);
        } else if (msg.role === "assistant") {
            createAgentBubble();
            // remove thinking and progress UI for loaded history
            if (currentThinkingContainer) {
                currentThinkingContainer.remove();
                currentThinkingContainer = null;
            }
            
            const contentDiv = currentAgentBubble.querySelector('.bubble-content');
            const finalBlock = document.createElement("div");
            finalBlock.className = "markdown-body-text";
            finalBlock.dataset.rawContent = msg.content;
            finalBlock.innerHTML = parseMarkdown(msg.content);
            contentDiv.appendChild(finalBlock);
            
            const copyBtn = currentAgentBubble.querySelector('.copy-msg-btn');
            if (copyBtn) {
                copyBtn.classList.remove("hidden");
            }
            currentAgentBubble = null;
        }
    }
    chatHistory.scrollTop = chatHistory.scrollHeight;
}

// 7. Bubble Creation & Rendering Helpers

function appendUserBubble(text) {
    const bubble = document.createElement("div");
    bubble.className = "chat-bubble user";
    bubble.innerHTML = `
        <div class="bubble-sender">You</div>
        <div class="bubble-content">${escapeHTML(text)}</div>
    `;
    chatHistory.appendChild(bubble);
    scrollChatToBottom();
}

function createAgentBubble() {
    const bubble = document.createElement("div");
    bubble.className = "chat-bubble agent";
    bubble.innerHTML = `
        <div class="bubble-sender">Antigravity MLX</div>
        <div class="bubble-content markdown-body" id="agent-content-placeholder">
            <!-- Thoughts and final markdown responses go here -->
        </div>
        <button class="copy-msg-btn hidden" onclick="copyMessage(this)" title="Copy message">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
            </svg>
        </button>
    `;
    chatHistory.appendChild(bubble);
    currentAgentBubble = bubble;
    scrollChatToBottom();
}

function addThinkingBlock(loopNum) {
    const container = currentAgentBubble.querySelector(".bubble-content");
    
    currentThinkingContainer = document.createElement("div");
    currentThinkingContainer.className = "thinking-container";
    
    currentThinkingContainer.innerHTML = `
        <div class="thinking-header" onclick="toggleThinking(this)">
            <div class="thinking-title">
                <svg class="thinking-icon open" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="9 18 15 12 9 6"/>
                </svg>
                <span>Agent thoughts...</span>
            </div>
            <span class="loop-tag">Loop #${loopNum}</span>
        </div>
        <div class="thinking-content">
            <div class="thought-block"></div>
        </div>
    `;
    
    container.appendChild(currentThinkingContainer);
    currentThinkingContent = currentThinkingContainer.querySelector(".thinking-content");
    currentThoughtBlock = currentThinkingContainer.querySelector(".thought-block");
    scrollChatToBottom();
}

function appendThought(text) {
    if (currentThoughtBlock) {
        currentThoughtBlock.textContent += text;
        scrollChatToBottom();
    }
}

function addToolCallBlock(name, args) {
    if (!currentThinkingContent) return;
    
    activeToolBlock = document.createElement("div");
    activeToolBlock.className = "tool-call-block";
    
    const formattedArgs = JSON.stringify(args, null, 2);
    
    activeToolBlock.innerHTML = `
        <div class="tool-call-header">
            <svg class="tool-icon-indicator" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="16 18 22 12 16 6"/>
                <polyline points="8 6 2 12 8 18"/>
            </svg>
            <span>Running: <span class="tool-name">${name}</span></span>
        </div>
        <pre class="tool-call-args">${escapeHTML(formattedArgs)}</pre>
        <div class="tool-output-details hidden">
            <div class="tool-output-summary" onclick="toggleToolOutput(this)">
                <svg class="thinking-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:12px;height:12px">
                    <polyline points="9 18 15 12 9 6"/>
                </svg>
                <span>Show command output...</span>
            </div>
            <pre class="tool-output-content"></pre>
        </div>
    `;
    
    currentThinkingContent.appendChild(activeToolBlock);
    activeToolOutputContent = activeToolBlock.querySelector(".tool-output-content");
    scrollChatToBottom();
}

function completeToolCallBlock(output, isError) {
    if (!activeToolBlock) return;
    
    const details = activeToolBlock.querySelector(".tool-output-details");
    details.classList.remove("hidden");
    
    if (activeToolOutputContent) {
        activeToolOutputContent.textContent = output;
        if (isError) {
            activeToolOutputContent.classList.add("error");
            activeToolBlock.querySelector(".tool-output-summary span").textContent = "Show execution error...";
        }
    }
    
    // Automatically collapse arguments box to save vertical screen space
    const argsBox = activeToolBlock.querySelector(".tool-call-args");
    argsBox.style.display = "none";
    
    scrollChatToBottom();
}

function renderFinalResponse(text) {
    // If thinking container was active, collapse it to clear the screen
    if (currentThinkingContainer) {
        const header = currentThinkingContainer.querySelector(".thinking-header");
        collapseThinking(header);
    }
    
    const container = currentAgentBubble.querySelector(".bubble-content");
    
    if (!currentFinalResponseBlock) {
        currentFinalResponseBlock = document.createElement("div");
        currentFinalResponseBlock.className = "markdown-body-text";
        container.appendChild(currentFinalResponseBlock);
    }
    
    finalResponseText = text;
    // Cache raw content for conversationHistory building
    currentFinalResponseBlock.dataset.rawContent = finalResponseText;
    currentFinalResponseBlock.innerHTML = parseMarkdown(finalResponseText);
    
    scrollChatToBottom();
    
    // Clean up generator state since this is the final block
    cleanupGenerationState();
}

function addSystemNotification(text) {
    const note = document.createElement("div");
    note.className = "info-note";
    note.style.color = "var(--accent-purple)";
    note.style.textAlign = "center";
    note.style.margin = "10px 0";
    note.textContent = `[System] ${text}`;
    chatHistory.appendChild(note);
    scrollChatToBottom();
}

function showErrorBanner(message) {
    const errorBubble = document.createElement("div");
    errorBubble.className = "chat-bubble agent";
    errorBubble.innerHTML = `
        <div class="bubble-sender">System Error</div>
        <div class="bubble-content" style="border-color:var(--color-error); background-color:rgba(239,68,68,0.05); color:var(--color-error)">
            ${escapeHTML(message)}
        </div>
    `;
    chatHistory.appendChild(errorBubble);
    scrollChatToBottom();
}

// 8. Toggles & Collapse UI handlers

window.toggleThinking = function(headerElement) {
    const icon = headerElement.querySelector(".thinking-icon");
    const content = headerElement.nextElementSibling;
    
    if (icon.classList.contains("open")) {
        icon.classList.remove("open");
        content.style.display = "none";
    } else {
        icon.classList.add("open");
        content.style.display = "flex";
    }
};

function collapseThinking(headerElement) {
    const icon = headerElement.querySelector(".thinking-icon");
    const content = headerElement.nextElementSibling;
    icon.classList.remove("open");
    content.style.display = "none";
}

window.toggleToolOutput = function(summaryElement) {
    const icon = summaryElement.querySelector(".thinking-icon");
    const content = summaryElement.nextElementSibling;
    
    if (icon.classList.contains("open")) {
        icon.classList.remove("open");
        content.style.display = "none";
    } else {
        icon.classList.add("open");
        content.style.display = "block";
    }
};

// 9. Markdown Parser (Line-by-line)

function parseMarkdown(text) {
    if (!text) return "";
    
    let escaped = escapeHTML(text);
    let lines = escaped.split("\n");
    let html = [];
    let inCodeBlock = false;
    let codeBuffer = [];
    let codeLang = "";
    let inList = false;
    
    for (let line of lines) {
        // Code Blocks
        if (line.trim().startsWith("```")) {
            if (inCodeBlock) {
                inCodeBlock = false;
                let codeText = codeBuffer.join("\n");
                html.push(`
                <div class="code-block-wrapper" style="position: relative; margin: 10px 0;">
                    <button class="copy-btn" onclick="copyCode(this)" style="position: absolute; top: 8px; right: 8px; padding: 4px 8px; font-size: 12px; background: rgba(255,255,255,0.2); color: #fff; border: 1px solid rgba(255,255,255,0.4); border-radius: 4px; cursor: pointer; transition: all 0.2s;">Copy</button>
                    <pre style="margin: 0; padding-top: 30px;"><code class="language-${codeLang}">${codeText}</code></pre>
                </div>`);
                codeBuffer = [];
                codeLang = "";
            } else {
                inCodeBlock = true;
                codeLang = line.trim().substring(3) || "plaintext";
            }
            continue;
        }
        
        if (inCodeBlock) {
            codeBuffer.push(line);
            continue;
        }
        
        // Lists (dash bullet)
        let listMatch = line.match(/^(\s*)-\s+(.*)/);
        if (listMatch) {
            if (!inList) {
                inList = true;
                html.push("<ul>");
            }
            html.push(`<li>${parseInlineMarkdown(listMatch[2])}</li>`);
            continue;
        } else if (inList && !line.match(/^(\s*)-\s+(.*)/)) {
            inList = false;
            html.push("</ul>");
        }
        
        // Headings
        if (line.startsWith("### ")) {
            html.push(`<h3>${parseInlineMarkdown(line.substring(4))}</h3>`);
        } else if (line.startsWith("## ")) {
            html.push(`<h2>${parseInlineMarkdown(line.substring(3))}</h2>`);
        } else if (line.startsWith("# ")) {
            html.push(`<h1>${parseInlineMarkdown(line.substring(2))}</h1>`);
        }
        // Blockquotes
        else if (line.startsWith("&gt; ")) {
            html.push(`<blockquote>${parseInlineMarkdown(line.substring(5))}</blockquote>`);
        }
        // Empty space
        else if (line.trim() === "") {
            html.push("<div style='height:8px'></div>");
        }
        // Paragraph
        else {
            html.push(`<p>${parseInlineMarkdown(line)}</p>`);
        }
    }
    
    if (inList) {
        html.push("</ul>");
    }
    
    return html.join("\n");
}

function parseInlineMarkdown(text) {
    let t = text;
    // Bold: **text**
    t = t.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    // Italics: *text*
    t = t.replace(/\*([^*]+)\*/g, "<em>$1</em>");
    // Inline code: `code`
    t = t.replace(/`([^`]+)`/g, "<code>$1</code>");
    return t;
}

// 10. Utilities
window.copyCode = function(btn) {
    const codeBlock = btn.nextElementSibling;
    const code = codeBlock.innerText;
    
    const successCb = () => {
        const originalText = btn.innerText;
        btn.innerText = "Copied!";
        btn.style.background = "rgba(0,255,0,0.3)";
        setTimeout(() => { 
            btn.innerText = originalText; 
            btn.style.background = "rgba(255,255,255,0.2)";
        }, 2000);
    };

    fetch("/api/copy", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: code })
    }).then(res => {
        if (!res.ok) throw new Error("Copy failed");
        successCb();
    }).catch(err => {
        console.error('Copy via backend failed', err);
        btn.innerText = "Error";
    });
};

window.copyMessage = function(btn) {
    const bubble = btn.closest(".chat-bubble");
    const finalBlock = bubble.querySelector(".markdown-body-text");
    if (!finalBlock) return;
    
    const code = finalBlock.dataset.rawContent || finalBlock.innerText;
    
    const successCb = () => {
        btn.innerHTML = `<span style="font-size: 11px; padding: 0 4px;">Copied!</span>`;
        btn.style.color = "var(--accent-green, #10b981)";
        setTimeout(() => { 
            btn.innerHTML = `
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
            </svg>`;
            btn.style.color = "var(--text-muted)";
        }, 2000);
    };

    fetch("/api/copy", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: code })
    }).then(res => {
        if (!res.ok) throw new Error("Copy failed");
        successCb();
    }).catch(err => {
        console.error('Copy via backend failed', err);
    });
};

function escapeHTML(text) {
    return text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
}

function scrollChatToBottom() {
    chatHistory.scrollTop = chatHistory.scrollHeight;
}

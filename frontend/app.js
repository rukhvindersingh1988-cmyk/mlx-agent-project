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

    // Restart Server Button
    const restartServerBtn = document.getElementById("restart-server-btn");
    if (restartServerBtn) {
        restartServerBtn.addEventListener("click", async () => {
            restartServerBtn.textContent = "Restarting... Please wait.";
            restartServerBtn.style.opacity = "0.7";
            restartServerBtn.disabled = true;
            try {
                await fetch("/api/restart", { method: "POST" });
            } catch (err) {
                console.error("Restart API triggered.", err);
            }
            // The python backend will os.execv, causing the window to instantly close and reopen.
        });
    }

    // New Chat Button
    newChatBtn.addEventListener("click", () => {
        currentSessionId = crypto.randomUUID();
        conversationHistory = [];
        chatHistory.innerHTML = "";
        welcomeScreen.classList.remove("hidden");
        welcomeScreen.style.display = "flex";
        chatHistory.appendChild(welcomeScreen);
        activeModelHeader.textContent = activeModel ? `Active Model: ${activeModel}` : "No active model loaded.";
        document.getElementById('chat-input').value = "";
        renderSessionsList();
    });

    // Refresh Overview
    const refreshOverviewBtn = document.getElementById("refresh-overview-btn");
    if (refreshOverviewBtn) {
        refreshOverviewBtn.addEventListener("click", loadProjectOverview);
    }

    // Copy Content (Active Tab)
    const copyOverviewBtn = document.getElementById("copy-overview-btn");
    if (copyOverviewBtn) {
        copyOverviewBtn.addEventListener("click", () => {
            // Find the active tab content
            const activeContent = document.querySelector(".right-sidebar-content.active");
            if (activeContent) {
                navigator.clipboard.writeText(activeContent.innerText).then(() => {
                    addSystemNotification("Content copied to clipboard!");
                }).catch(err => {
                    console.error("Failed to copy text: ", err);
                });
            }
        });
    }

    // Sidebar Tabs Logic
    const sidebarTabs = document.querySelectorAll(".sidebar-tab");
    sidebarTabs.forEach(tab => {
        tab.addEventListener("click", () => {
            sidebarTabs.forEach(t => t.classList.remove("active"));
            document.querySelectorAll(".right-sidebar-content").forEach(c => c.classList.remove("active"));
            
            tab.classList.add("active");
            document.getElementById(tab.dataset.target).classList.add("active");
            
            // Auto-refresh Activity Log when tab is clicked
            if (tab.dataset.target === "project-overview-content") {
                loadProjectOverview();
            }
        });
    });

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
        cleanupGenerationState();
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
            const isCloud = /^(groq|cerebras|together|openrouter|hf)\//.test(model.id);
            const isReady = model.downloaded || isCloud;

            // Populate selector if ready (downloaded or cloud)
            if (isReady) {
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
            
            if (isCloud) {
                statusLabelHTML = '<span class="download-status-label downloaded">☁️ Cloud Ready</span>';
                actionBtnHTML = `<button class="btn-small select-model-btn" onclick="selectModel('${model.id}')">Select</button>`;
            } else if (model.downloaded) {
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
    const disabled = !connected || !modelReady;
    
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
        }
    } else {
        if (isGenerating) {
            chatInput.placeholder = "Agent is working... Type here and press Enter to inject instructions.";
        } else {
            chatInput.placeholder = "Ask anything... (Shift+Enter for new line)";
        }
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

// Pending image path set by the attach button
let pendingImagePath = null;

function sendMessage() {
    const text = chatInput.value.trim();
    if (!text || !activeModel) return;
    
    if (isGenerating) {
        // Send user steering instruction in real-time
        const payload = {
            type: "user_injection",
            prompt: text
        };
        ws.send(JSON.stringify(payload));
        appendUserBubble(text);
        chatInput.value = "";
        chatInput.style.height = "auto";
        return;
    }
    
    isGenerating = true;
    currentPromptText = text;
    updateInputState();
    
    // Hide welcome screen
    welcomeScreen.style.display = "none";
    
    // Append User Bubble (show image name if attached)
    let displayText = text;
    if (pendingImagePath) {
        const fname = pendingImagePath.split("/").pop();
        displayText = `📎 ${fname}\n${text}`;
    }
    appendUserBubble(displayText);
    
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
        history: conversationHistory,
        image_path: pendingImagePath || null
    };
    
    ws.send(JSON.stringify(payload));
    
    // Clear input box and pending image
    chatInput.value = "";
    chatInput.style.height = "auto";
    pendingImagePath = null;
    // Reset attach button appearance
    const attachBtn2 = document.getElementById("attach-btn");
    if (attachBtn2) attachBtn2.title = "Upload Image/File";
}

// 8. Diff Rendering
function renderDiff(file, diffString) {
    const container = document.getElementById("review-changes-content");
    
    // Clear the empty state if it exists
    const emptyState = container.querySelector(".empty-state");
    if (emptyState) {
        container.innerHTML = "";
    }
    
    const diffContainer = document.createElement("div");
    diffContainer.className = "diff-container";
    
    const header = document.createElement("div");
    header.className = "diff-header";
    header.textContent = file;
    diffContainer.appendChild(header);
    
    const lines = diffString.split('\n');
    lines.forEach(line => {
        if (!line) return;
        const lineDiv = document.createElement("div");
        lineDiv.className = "diff-line";
        
        if (line.startsWith('+') && !line.startsWith('+++')) {
            lineDiv.classList.add("diff-add");
        } else if (line.startsWith('-') && !line.startsWith('---')) {
            lineDiv.classList.add("diff-rem");
        } else if (line.startsWith('@@')) {
            lineDiv.classList.add("diff-info");
        }
        
        lineDiv.textContent = line;
        diffContainer.appendChild(lineDiv);
    });
    
    // Prepend so newest diffs are at the top
    container.insertBefore(diffContainer, container.firstChild);
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
let currentLoop = 1;

function handleWebSocketMessage(event) {
    const msg = JSON.parse(event.data);
    
    switch (msg.type) {
        case "turn_start":
            currentLoop = msg.loop;
            agentProgressText.textContent = `Loop ${currentLoop}: Reasoning...`;
            addThinkingBlock(msg.loop);
            break;
            
        case "thought":
            appendThought(msg.text);
            break;
            
        case "tool_start":
            agentProgressText.textContent = `Loop ${currentLoop}: Running tool ${msg.name}...`;
            addToolCallBlock(msg.name, msg.args);
            break;
            
        case "tool_end":
            agentProgressText.textContent = `Loop ${currentLoop}: Tool ${msg.name} finished.`;
            completeToolCallBlock(msg.output, false);
            
            // Show tool output in Overview tab
            const overviewDiv = document.getElementById("project-overview-content");
            if (overviewDiv) {
                // Switch to overview tab
                const overviewTabBtn = document.querySelector('.sidebar-tab[data-target="project-overview-content"]');
                if (overviewTabBtn) overviewTabBtn.click();
                
                // Render output nicely
                overviewDiv.innerHTML = `
                    <div style="padding: 15px;">
                        <h3 style="color: var(--accent-color); margin-top: 0;">Tool Output: ${msg.name}</h3>
                        <pre style="background: var(--bg-tertiary); padding: 12px; border-radius: 6px; white-space: pre-wrap; font-family: monospace; font-size: 0.9em; max-height: 70vh; overflow-y: auto; color: #a3a3a3;">${escapeHTML(msg.output)}</pre>
                    </div>
                `;
            }
            break;
            
        case "tool_error":
            agentProgressText.textContent = `Loop ${currentLoop}: Tool failed.`;
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

        case "file_diff":
            // Automatically switch to Review Changes tab
            document.getElementById("review-changes-tab").click();
            renderDiff(msg.file, msg.diff);
            break;

        case "model_switched":
            // Silently update the active model in UI — no interruption to user
            activeModel = msg.model_id;
            activeModelHeader.textContent = `Active Model: ${activeModel}`;
            // Update the selector dropdown if it exists
            const sel = document.getElementById("model-selector");
            if (sel) sel.value = activeModel;
            // Show a tiny non-blocking toast
            showModelSwitchToast(msg.reason);
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

// Toggle archived section view state
let archiveExpanded = false;

function renderSessionsList() {
    const listDiv = document.getElementById("recent-chats-list");
    const pinnedSection = document.getElementById("pinned-section");
    const pinnedDiv = document.getElementById("pinned-chats-list");
    const archivedDiv = document.getElementById("archived-chats-list");
    const archiveToggleBtn = document.getElementById("archive-toggle-btn");
    
    if (!listDiv || !pinnedDiv || !archivedDiv) return;
    
    listDiv.innerHTML = "";
    pinnedDiv.innerHTML = "";
    archivedDiv.innerHTML = "";
    
    // Add event listener for toggling archived view if not already added
    if (archiveToggleBtn && !archiveToggleBtn.dataset.listener) {
        archiveToggleBtn.dataset.listener = "true";
        archiveToggleBtn.addEventListener("click", () => {
            archiveExpanded = !archiveExpanded;
            if (archiveExpanded) {
                archivedDiv.classList.remove("hidden");
                archiveToggleBtn.classList.add("active");
            } else {
                archivedDiv.classList.add("hidden");
                archiveToggleBtn.classList.remove("active");
            }
        });
    }

    let displaySessions = [...allSessions];
    if (!displaySessions.find(s => s.id === currentSessionId)) {
        const title = conversationHistory.length > 0 ? conversationHistory[0].content : "New Chat";
        displaySessions.unshift({ id: currentSessionId, title: title, history: conversationHistory, pinned: false, archived: false });
    }
    
    let hasPinned = false;

    displaySessions.forEach(session => {
        const isPinned = !!session.pinned;
        const isArchived = !!session.archived;
        
        // Skip display on unsaved chat if active session is archived
        if (session.id === currentSessionId && isArchived) {
            // Keep archived active session shown
        }

        const container = document.createElement("div");
        container.className = `session-item-container ${session.id === currentSessionId ? "active" : ""}`;
        
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
        
        // Pin/Archive/Delete actions
        const actions = document.createElement("div");
        actions.className = "session-actions";
        
        // Pinned Button
        const pinBtn = document.createElement("button");
        pinBtn.className = `action-icon-btn ${isPinned ? "active" : ""}`;
        pinBtn.title = isPinned ? "Unpin conversation" : "Pin conversation";
        pinBtn.innerHTML = `
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="12" y1="17" x2="12" y2="22"></line>
                <path d="M5 17h14v-1.76a2 2 0 0 0-.44-1.24l-2.78-3.5A2 2 0 0 1 15 9.26V5a3 3 0 0 0-6 0v4.26a2 2 0 0 1-.78 1.54l-2.78 3.5a2 2 0 0 0-.44 1.24Z"></path>
            </svg>
        `;
        pinBtn.onclick = (e) => {
            e.stopPropagation();
            togglePinSession(session.id, !isPinned);
        };
        
        // Archive Button
        const archiveBtn = document.createElement("button");
        archiveBtn.className = `action-icon-btn ${isArchived ? "active" : ""}`;
        archiveBtn.title = isArchived ? "Unarchive conversation" : "Archive conversation";
        archiveBtn.innerHTML = `
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="21 8 21 21 3 21 3 8"></polyline>
                <rect x="1" y="3" width="22" height="5"></rect>
                <line x1="10" y1="12" x2="14" y2="12"></line>
            </svg>
        `;
        archiveBtn.onclick = (e) => {
            e.stopPropagation();
            toggleArchiveSession(session.id, !isArchived);
        };
        
        // Delete Button
        const deleteBtn = document.createElement("button");
        deleteBtn.className = "action-icon-btn";
        deleteBtn.title = "Delete conversation";
        deleteBtn.innerHTML = `
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color:var(--color-error)">
                <polyline points="3 6 5 6 21 6"></polyline>
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
            </svg>
        `;
        deleteBtn.onclick = (e) => {
            e.stopPropagation();
            const displayTitle = session.title && session.title.length > 60 
                ? session.title.substring(0, 60) + "..." 
                : (session.title || "New Chat");
            if (confirm(`Delete conversation "${displayTitle}" permanently?`)) {
                deleteSession(session.id);
            }
        };
        
        actions.appendChild(pinBtn);
        actions.appendChild(archiveBtn);
        actions.appendChild(deleteBtn);
        
        container.appendChild(item);
        container.appendChild(actions);
        
        if (isPinned) {
            pinnedDiv.appendChild(container);
            hasPinned = true;
        } else if (isArchived) {
            archivedDiv.appendChild(container);
        } else {
            listDiv.appendChild(container);
        }
    });
    
    // Toggle Pinned sidebar section visibility
    if (hasPinned) {
        pinnedSection.classList.remove("hidden");
    } else {
        pinnedSection.classList.add("hidden");
    }
}

async function togglePinSession(sessionId, state) {
    try {
        // Find in local array & update state
        const session = allSessions.find(s => s.id === sessionId);
        if (session) {
            session.pinned = state;
            // Un-archive if pinned
            if (state) session.archived = false;
            
            await fetch("/api/history", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ 
                    session_id: sessionId,
                    title: session.title,
                    history: session.history 
                })
            });
            // Update additional metadata keys on backend by using save
            await saveHistoryMetadata(sessionId, { pinned: state, archived: session.archived });
        } else if (sessionId === currentSessionId) {
            // Unsaved active chat toggle pin
            addSystemNotification("Pin state will be saved once you start typing.");
        }
        loadSessions();
    } catch (e) {
        console.error(e);
    }
}

async function toggleArchiveSession(sessionId, state) {
    try {
        const session = allSessions.find(s => s.id === sessionId);
        if (session) {
            session.archived = state;
            // Un-pin if archived
            if (state) session.pinned = false;
            
            await saveHistoryMetadata(sessionId, { pinned: session.pinned, archived: state });
        }
        loadSessions();
    } catch (e) {
        console.error(e);
    }
}

async function deleteSession(sessionId) {
    try {
        await fetch(`/api/sessions/${sessionId}`, { method: "DELETE" });
        if (sessionId === currentSessionId) {
            // Reset to new chat if we deleted the current active one
            currentSessionId = crypto.randomUUID();
            conversationHistory = [];
            chatHistory.innerHTML = "";
            chatHistory.appendChild(welcomeScreen);
            welcomeScreen.style.display = "flex";
            activeModelHeader.textContent = activeModel ? `Active Model: ${activeModel}` : "No active model loaded.";
        }
        loadSessions();
    } catch (e) {
        console.error(e);
    }
}

async function saveHistoryMetadata(sessionId, metadata) {
    // Send helper update meta to backend
    try {
        await fetch(`/api/sessions/${sessionId}/metadata`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(metadata)
        });
    } catch (e) {
        console.error("Failed to save session metadata", e);
    }
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
        const res = await fetch(`/api/project-overview?t=${Date.now()}`, { cache: "no-store" });
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

function showModelSwitchToast(reason) {
    if (!reason) return;
    // Remove any existing toast
    const old = document.getElementById("model-switch-toast");
    if (old) old.remove();

    const toast = document.createElement("div");
    toast.id = "model-switch-toast";
    toast.textContent = reason;
    toast.style.cssText = `
        position: fixed; bottom: 90px; left: 50%; transform: translateX(-50%);
        background: rgba(99,102,241,0.92); color: #fff;
        padding: 7px 18px; border-radius: 20px; font-size: 13px;
        font-family: inherit; font-weight: 500; z-index: 9999;
        backdrop-filter: blur(8px); box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        transition: opacity 0.4s ease; pointer-events: none;
    `;
    document.body.appendChild(toast);
    // Fade out after 2.5s
    setTimeout(() => { toast.style.opacity = "0"; }, 2500);
    setTimeout(() => { toast.remove(); }, 3000);
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

// Attach file logic
const attachBtn = document.getElementById("attach-btn");
if (attachBtn) {
    attachBtn.addEventListener("click", async () => {
        if (window.pywebview && window.pywebview.api) {
            const filePath = await window.pywebview.api.open_file_dialog();
            if (filePath) {
                pendingImagePath = filePath;
                const fname = filePath.split("/").pop();
                // Show the filename in the input box as a hint
                chatInput.value = `Analyse this image: ${fname}`;
                attachBtn.title = `📎 ${fname} ready`;
                // Enable send
                sendBtn.disabled = false;
                chatInput.focus();
            }
        } else {
            console.warn("pywebview API not available. File picker disabled.");
        }
    });
}

// --- GEM EASTER EGG ---
document.addEventListener("DOMContentLoaded", () => {
    const brandTitle = document.getElementById("brand-title");
    if (brandTitle) {
        brandTitle.addEventListener("click", () => {
            brandTitle.classList.toggle("gem-glow");
        });
    }
});

// --- SWARM PLAYGROUND CONTROLLER ---
document.addEventListener("DOMContentLoaded", () => {
    const runSwarmBtn = document.getElementById("run-swarm-btn");
    const swarmPromptInput = document.getElementById("swarm-prompt-input");
    const swarmModelSelector = document.getElementById("swarm-model-selector");
    const swarmRunningStatus = document.getElementById("swarm-running-status");
    const swarmResultsSection = document.getElementById("swarm-results-section");

    // Populate swarm selector when main modelSelector has options
    const populateSwarmSelector = () => {
        if (!swarmModelSelector) return;
        swarmModelSelector.innerHTML = "";
        
        // Match options in main modelSelector
        const mainOptions = document.querySelectorAll("#model-selector option");
        mainOptions.forEach(opt => {
            if (opt.value) { // Skip empty option
                const newOpt = document.createElement("option");
                newOpt.value = opt.value;
                newOpt.textContent = opt.textContent;
                newOpt.selected = opt.selected;
                swarmModelSelector.appendChild(newOpt);
            }
        });
        
        // Also add the default cloud open-source option
        const cloudOpt = document.createElement("option");
        cloudOpt.value = "meta-llama/Meta-Llama-3.1-405B-Instruct";
        cloudOpt.textContent = "Llama 3.1 405B (Free HF Cloud API)";
        swarmModelSelector.insertBefore(cloudOpt, swarmModelSelector.firstChild);
        
        // Default to cloud option for easy testing
        swarmModelSelector.value = "meta-llama/Meta-Llama-3.1-405B-Instruct";
    };

    // Watch for model updates
    const observer = new MutationObserver(populateSwarmSelector);
    const target = document.getElementById("model-selector");
    if (target) {
        observer.observe(target, { childList: true });
        // Initial population
        setTimeout(populateSwarmSelector, 1000);
    }

    if (runSwarmBtn) {
        runSwarmBtn.addEventListener("click", async () => {
            const prompt = swarmPromptInput.value.trim();
            const modelId = swarmModelSelector.value;
            
            if (!prompt) {
                alert("Please enter a benchmark prompt.");
                return;
            }
            
            runSwarmBtn.disabled = true;
            swarmRunningStatus.classList.remove("hidden");
            swarmResultsSection.innerHTML = '<div style="opacity: 0.6; padding: 12px; background: var(--bg-hover); border-radius: 6px;">Executing concurrent subagents...</div>';
            
            try {
                const response = await fetch("/api/swarm/run", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ prompt, model_id: modelId })
                });
                const data = await response.json();
                
                if (data.status === "success" && data.report) {
                    swarmResultsSection.innerHTML = `
                        <div style="margin-bottom: 8px; font-weight: bold; color: var(--accent-color);">Benchmark Execution Complete!</div>
                        <div class="markdown-body" style="padding: 12px; border-radius: 8px; background: var(--bg-card); border: 1px solid var(--border-color); overflow-x: auto;">
                            ${parseMarkdown(data.report)}
                        </div>
                    `;
                } else {
                    swarmResultsSection.innerHTML = `<div style="color: var(--color-error); padding: 12px;">Error: ${data.message || "Execution failed."}</div>`;
                }
            } catch (err) {
                swarmResultsSection.innerHTML = `<div style="color: var(--color-error); padding: 12px;">Network/Server Error: ${err.message}</div>`;
            } finally {
                runSwarmBtn.disabled = false;
                swarmRunningStatus.classList.add("hidden");
            }
        });
    }
});

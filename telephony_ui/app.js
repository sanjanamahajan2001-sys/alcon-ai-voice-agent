// API Base configuration:
// - Set USE_LOCAL_API = true to test with your local FastAPI backend running on port 8000.
// - Set USE_LOCAL_API = false to route requests to the public ngrok endpoint (useful for Twilio telephony testing).
const USE_LOCAL_API = true; // Default to true for local testing, set to false to use public ngrok endpoint
const API_BASE = USE_LOCAL_API ? 'http://localhost:8000' : 'https://grinning-linked-rebuilt.ngrok-free.dev';

console.log('Alcon App Version 4.0 Loaded');

let activeCallSid = null;
let pollInterval = null;
let historyInterval = null;
let currentValues = { duration: 0, chars: 0, cost: 0 };

const elements = {};

function initElements() {
    elements.loginOverlay = document.getElementById('login-overlay');
    elements.loginPass = document.getElementById('login-pass');
    elements.loginBtn = document.getElementById('login-btn');
    elements.loginError = document.getElementById('login-error');
    elements.appContainer = document.getElementById('app-container');
    elements.customerList = document.getElementById('customer-list');
    elements.callHistory = document.getElementById('call-history');
    elements.transcript = document.getElementById('live-transcript');
    elements.apiStatus = document.getElementById('api-status');
    elements.statusText = document.getElementById('status-text');
    elements.sidBadge = document.getElementById('active-call-sid');
    elements.stepBadge = document.getElementById('active-step');
    elements.voicePulse = document.getElementById('voice-pulse');
    elements.flowType = document.getElementById('flow-type');
    elements.metrics = {
        duration: document.getElementById('metric-duration'),
        chars: document.getElementById('metric-chars'),
        cost: document.getElementById('metric-cost'),
        status: document.getElementById('metric-status')
    };
    elements.recordingContainer = document.getElementById('recording-container');
    elements.recordingPlayer = document.getElementById('recording-player');
    elements.scanDmsBtn = document.getElementById('scan-dms-btn');
    elements.dmsResults = document.getElementById('dms-scan-results');
    elements.scanCount = document.getElementById('scan-count');
    elements.dueList = document.getElementById('due-customers-list');
    elements.startCampaignBtn = document.getElementById('start-campaign-btn');
    elements.campaignProgress = document.getElementById('campaign-progress');
    elements.campaignStatus = document.getElementById('campaign-status');
    elements.campaignPercent = document.getElementById('campaign-percent');
    elements.progressBar = document.getElementById('progress-bar-fill');
    elements.scanServiceBtn = document.getElementById('scan-service-btn');
    elements.scanSalesBtn = document.getElementById('scan-sales-btn');
    elements.scanInsuranceBtn = document.getElementById('scan-insurance-btn');
    elements.resetLocksBtn = document.getElementById('reset-locks-btn');
    
    // View Switcher Elements
    elements.voiceView = document.getElementById('voice-view');
    elements.navVoice = document.getElementById('nav-voice');
    elements.navChat = document.getElementById('nav-chat');
    // Chat Widget Elements
    elements.chatWidget = document.getElementById('chat-widget');
    elements.chatFab = document.getElementById('chat-fab');
    elements.chatMessages = document.getElementById('chat-messages');
    elements.chatInput = document.getElementById('chat-input');
    elements.chatSendBtn = document.getElementById('chat-send-btn');
    elements.chatQuickOptions = document.getElementById('chat-quick-options');
}

// --- View Management ---
// --- View & Widget Management ---
function switchView(view) {
    if (view === 'voice') {
        elements.voiceView.classList.remove('hidden');
        elements.voiceView.classList.add('active');
        elements.navVoice.classList.add('active');
        elements.navChat.classList.remove('active');
    } else if (view === 'chat') {
        toggleChat();
    }
}

function toggleChat(forceOpen = false) {
    const isOpen = elements.chatWidget.classList.contains('open');
    if (forceOpen || !isOpen) {
        elements.chatWidget.classList.add('open');
        elements.chatFab.classList.add('active');
    } else {
        elements.chatWidget.classList.remove('open');
        elements.chatFab.classList.remove('active');
    }
}

// --- Chat Assistant Logic ---
let chatSessionId = localStorage.getItem('alcon_chat_session_id') || 'chat_' + Math.random().toString(36).substr(2, 9);
localStorage.setItem('alcon_chat_session_id', chatSessionId);

function addChatMessage(text, speaker, isTyping = false) {
    const id = isTyping ? 'typing-' + Date.now() : null;
    let content = text;
    if (isTyping) {
        content = `
            <div class="typing-dots">
                <span></span><span></span><span></span>
            </div>
        `;
    }
    const msgHtml = `
        <div class="msg msg-${speaker === 'ai' ? 'ai' : 'user'}" ${id ? `id="${id}"` : ''}>
            <span class="msg-label">${speaker === 'ai' ? 'Supriya' : 'You'}</span>
            <div class="msg-text">${content}</div>
        </div>
    `;
    elements.chatMessages.insertAdjacentHTML('beforeend', msgHtml);
    elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
    return id;
}

function removeChatMessage(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

function updateChatProgress(state) {
    if (!elements.chatStateLabel || !elements.chatProgressFill) return;
    
    elements.chatStateLabel.innerText = state;
    
    const progressMap = {
        "Initial Greeting": 10,
        "Initial Reception": 10,
        "Service Check": 30,
        "Service Identification": 40,
        "Selecting Date": 50,
        "Vehicle Details": 70,
        "Health Check": 80,
        "Pick & Drop Options": 90,
        "Service Confirmed": 100,
        "Pre-Sales Enquiry": 20,
        "Lead Capture": 40,
        "Model Inquiry": 60,
        "Query Handling": 80,
        "Satisfaction Check": 30,
        "Overall Experience": 90
    };
    
    const percent = progressMap[state] || 0;
    elements.chatProgressFill.style.width = percent + '%';
}

function renderChatOptions(options) {
    if (!elements.chatQuickOptions) return;
    
    if (!options || options.length === 0) {
        elements.chatQuickOptions.innerHTML = '';
        return;
    }
    
    elements.chatQuickOptions.innerHTML = options.map(opt => `
        <button class="chip" onclick="sendChatMessage('${opt.replace(/'/g, "\\'")}')">${opt}</button>
    `).join('');
}

async function sendChatMessage(msg) {
    if (!msg) msg = elements.chatInput.value;
    if (!msg.trim()) return;
    
    addChatMessage(msg, 'user');
    elements.chatInput.value = '';
    renderChatOptions([]); // Clear options while thinking
    
    const typingId = addChatMessage('Thinking...', 'ai', true);
    
    try {
        const res = await fetch(`${API_BASE}/chat`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'ngrok-skip-browser-warning': 'true'
            },
            body: JSON.stringify({ session_id: chatSessionId, message: msg })
        });
        const data = await res.json();
        removeChatMessage(typingId);
        
        addChatMessage(data.text, 'ai');
        renderChatOptions(data.options);
        if (data.ui_state) updateChatProgress(data.ui_state);
        
    } catch (e) {
        removeChatMessage(typingId);
        addChatMessage('I\'m sorry, I\'m having trouble connecting to the service. Please check your internet or try again later.', 'ai');
    }
}

function clearChat() {
    elements.chatMessages.innerHTML = `
        <div class="msg msg-ai">
            <span class="msg-label">Supriya</span>
            <div class="msg-text">Chat history cleared. How else can I help you today?</div>
        </div>
    `;
    chatSessionId = 'chat_' + Math.random().toString(36).substr(2, 9);
    localStorage.setItem('alcon_chat_session_id', chatSessionId);
    if (elements.chatStateLabel) elements.chatStateLabel.innerText = 'Waiting for input';
    if (elements.chatProgressFill) elements.chatProgressFill.style.width = '0%';
    renderChatOptions(['Book a service', 'I want to enquire about a new car', 'Track my service status']);
}

async function checkApiStatus() {
    try {
        const res = await fetch(`${API_BASE}/customers`, {
            headers: { 'ngrok-skip-browser-warning': 'true' }
        });
        if (res.ok) {
            elements.apiStatus.classList.add('online');
            elements.statusText.innerText = 'Connected';
            return true;
        }
    } catch (e) {
        elements.apiStatus.classList.remove('online');
        elements.statusText.innerText = 'Offline';
        return false;
    }
}

async function loadCustomers() {
    try {
        const res = await fetch(`${API_BASE}/customers`, {
            headers: { 'ngrok-skip-browser-warning': 'true' }
        });
        const customers = await res.json();
        
        elements.customerList.innerHTML = customers.map(c => `
            <button class="customer-btn" onclick="startCall('${c.id}', '${c.phone}')">
                <h3>${c.name}</h3>
                <span>${c.car_model} • ${c.phone}</span>
            </button>
        `).join('');
    } catch (e) {
        console.error('Failed to load customers');
    }
}

async function loadHistory() {
    try {
        const res = await fetch(`${API_BASE}/telephony/history`, {
            headers: { 'ngrok-skip-browser-warning': 'true' }
        });
        const history = await res.json();
        
        if (history.length === 0) {
            elements.callHistory.innerHTML = '<div class="empty-state">No past calls found.</div>';
            return;
        }

        elements.callHistory.innerHTML = history.map(call => `
            <div class="history-item" onclick="viewPastCall('${call.call_sid}')">
                <div class="hist-header">
                    <span>${call.customer_name}</span>
                    <span>$${call.estimated_cost.toFixed(4)}</span>
                </div>
                <div class="hist-meta">
                    <span>${call.duration_seconds}s • ${call.total_characters} ch</span>
                    <span>${new Date(call.start_time).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>
                </div>
            </div>
        `).join('');
    } catch (e) {
        console.error('Failed to load history');
    }
}

function animateValue(id, start, end, duration, isCost = false) {
    const obj = elements.metrics[id];
    const range = end - start;
    let startTime = null;

    function step(timestamp) {
        if (!startTime) startTime = timestamp;
        const progress = Math.min((timestamp - startTime) / duration, 1);
        const value = start + (range * progress);
        
        if (isCost) {
            obj.innerText = `$${value.toFixed(4)}`;
        } else {
            obj.innerText = Math.floor(value) + (id === 'duration' ? 's' : '');
        }

        if (progress < 1) {
            window.requestAnimationFrame(step);
        }
    }
    window.requestAnimationFrame(step);
}

function startCall(id, phone, extraParams = {}) {
    if (activeCallSid) return;

    // Reset metrics for new session
    currentValues = { duration: 0, chars: 0, cost: 0 };
    elements.metrics.duration.innerText = '0s';
    elements.metrics.chars.innerText = '0';
    elements.metrics.cost.innerText = '$0.0000';
    elements.metrics.status.innerText = 'IDLE';
    elements.transcript.innerHTML = '';
    elements.sidBadge.classList.add('hidden');
    elements.stepBadge.classList.add('hidden');

    let flowType = elements.flowType.value;
    
    // Auto-switch flow type for campaigns if needed
    if (extraParams.campaign_type) {
        if (extraParams.campaign_type === 'insurance') {
            flowType = 'insurance_start';
            elements.flowType.value = 'insurance_start';
        } else {
            flowType = 'pre_sales';
            elements.flowType.value = 'pre_sales';
        }
    }

    // Set polling timeout to clear stuck queued sessions
    const makeCallTimeout = setTimeout(() => {
        if (activeCallSid && activeCallSid.startsWith('QUEUED_')) {
            console.log("[TIMEOUT] Clearing stuck queued call from UI");
            stopPollingLog();
        }
    }, 15000);

    fetch(`${API_BASE}/make-call/${id}`, {
        method: 'POST',
        headers: { 
            'Content-Type': 'application/json',
            'ngrok-skip-browser-warning': 'true'
        },
        body: JSON.stringify({ 
            to_number: phone, 
            flow_type: flowType,
            ...extraParams
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.call_sid) {
            activeCallSid = data.call_sid;
            elements.sidBadge.innerText = `SID: ${activeCallSid.substring(0, 10)}...`;
            elements.sidBadge.classList.remove('hidden');
            startPollingLog();
        }
    })
    .catch(e => {
        clearTimeout(makeCallTimeout);
        alert("Could not trigger call.");
    });
}

function startPollingLog() {
    pollInterval = setInterval(async () => {
        if (!activeCallSid) return;
        try {
            const res = await fetch(`${API_BASE}/telephony/logs/${activeCallSid}`, {
                headers: { 'ngrok-skip-browser-warning': 'true' }
            });
            if (!res.ok) return;
            const log = await res.json();
            updateUIWithLog(log);
            if (log.status && log.status.toLowerCase() === 'completed') {
                stopPollingLog();
                loadHistory();
            }
        } catch (e) {}
    }, 2000);
}

function stopPollingLog() {
    clearInterval(pollInterval);
    pollInterval = null;
    activeCallSid = null;
    elements.voicePulse.classList.add('hidden');
}

function updateUIWithLog(log) {
    // SID Resolution Check (QUEUED_... -> CA... or SIM_CALL_...)
    if (log.call_sid && log.call_sid !== activeCallSid) {
        console.log(`[SID RESOLVED] Updating activeCallSid from ${activeCallSid} to ${log.call_sid}`);
        activeCallSid = log.call_sid;
        elements.sidBadge.innerText = `SID: ${activeCallSid.substring(0, 10)}...`;
    }

    // Tickers
    if (log.duration_seconds !== currentValues.duration) {
        animateValue('duration', currentValues.duration, log.duration_seconds, 1000);
        currentValues.duration = log.duration_seconds;
    }
    if (log.total_characters !== currentValues.chars) {
        animateValue('chars', currentValues.chars, log.total_characters, 1000);
        currentValues.chars = log.total_characters;
    }
    if (log.estimated_cost !== currentValues.cost) {
        animateValue('cost', currentValues.cost, log.estimated_cost, 1000, true);
        currentValues.cost = log.estimated_cost;
    }

    // Status & Step
    elements.stepBadge.innerText = log.current_step || 'Active';
    elements.stepBadge.classList.remove('hidden');
    
    if (log.status && log.status.toLowerCase() === 'completed') {
        elements.metrics.status.innerText = 'COMPLETED';
        elements.metrics.status.className = 'status-idle';
        elements.voicePulse.classList.add('hidden');
        
        // Handle Recording
        if (log.recording_url) {
            elements.recordingContainer.classList.remove('hidden');
            if (elements.recordingPlayer.src !== log.recording_url) {
                elements.recordingPlayer.src = log.recording_url;
            }
        } else {
            elements.recordingContainer.classList.add('hidden');
        }
    } else if (log.status && (log.status.toLowerCase() === 'queued' || log.status.toLowerCase() === 'initializing' || log.status.toLowerCase() === 'processing')) {
        elements.metrics.status.innerText = log.status.toUpperCase();
        elements.metrics.status.className = 'status-calling';
        elements.recordingContainer.classList.add('hidden');
    } else {
        elements.metrics.status.innerText = 'ACTIVE';
        elements.metrics.status.className = 'status-active';
        elements.recordingContainer.classList.add('hidden');
    }

    if (log.transcript.length > 0) {
        const lastMsg = log.transcript[log.transcript.length - 1];
        if (lastMsg.speaker === 'Supriya' && (!log.status || log.status.toLowerCase() !== 'completed')) {
            elements.voicePulse.classList.remove('hidden');
        } else {
            elements.voicePulse.classList.add('hidden');
        }
    }

    // Transcript with Smart Highlights & Reasoning Trace
    let transcriptHtml = log.transcript.map(msg => {
        const isIssue = /not|ac|noise|problem|bad|issue|issue|fail|leak|broke/i.test(msg.text) && msg.speaker === 'Customer';
        return `
            <div class="msg msg-${msg.speaker === 'Supriya' || msg.speaker === 'System' ? 'ai' : 'user'} ${isIssue ? 'msg-alert' : ''}">
                <span class="msg-label">${msg.speaker}</span>
                <div class="msg-text">${msg.text}</div>
            </div>
        `;
    }).join('');

    // Append Reasoning Trace if available (Production Grade Feature)
    if (log.interest_level && log.reasoning_trace) {
        try {
            const trace = JSON.parse(log.reasoning_trace);
            const traceHtml = `
                <div class="trace-box">
                    <div class="trace-header">
                        <span class="trace-badge ${trace.decision.toLowerCase()}">${trace.decision} LEAD</span>
                        <span class="trace-label">AI Reasoning Trace</span>
                    </div>
                    <div class="trace-body">
                        Matched Keywords: ${trace.matched_hot.length ? trace.matched_hot.join(', ') : 'None'}
                        ${trace.matched_warm.length ? ' | Warm: ' + trace.matched_warm.join(', ') : ''}
                    </div>
                </div>
            `;
            transcriptHtml += traceHtml;
        } catch(e) {}
    }

    if (elements.transcript.innerHTML !== transcriptHtml) {
        elements.transcript.innerHTML = transcriptHtml;
        elements.transcript.scrollTop = elements.transcript.scrollHeight;
    }
}

async function viewPastCall(sid) {
    try {
        const res = await fetch(`${API_BASE}/telephony/logs/${sid}`, {
            headers: { 'ngrok-skip-browser-warning': 'true' }
        });
        const log = await res.json();
        activeCallSid = null;
        elements.sidBadge.innerText = `PAST SID: ${sid.substring(0, 10)}...`;
        elements.sidBadge.classList.remove('hidden');
        updateUIWithLog(log);
    } catch (e) {}
}

async function handleLogin() {
    const password = elements.loginPass.value;
    try {
        const res = await fetch(`${API_BASE}/login`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'ngrok-skip-browser-warning': 'true'
            },
            body: JSON.stringify({ password })
        });

        if (res.ok) {
            elements.loginOverlay.style.opacity = '0';
            setTimeout(() => {
                elements.loginOverlay.classList.add('hidden');
                elements.appContainer.classList.remove('blur');
                document.body.classList.remove('login-active');
            }, 500);
            
            // Start loading data after login
            const online = await checkApiStatus();
            if (online) {
                await loadCustomers();
                await loadHistory();
                historyInterval = setInterval(loadHistory, 10000);
            }
        } else {
            elements.loginError.classList.remove('hidden');
            elements.loginPass.value = '';
        }
    } catch (e) {
        console.error('Login failed', e);
    }
}


// --- DMS Automation Logic ---
let dueCustomers = [];

async function scanDms(type = 'service') {
    try {
        let btn = elements.scanServiceBtn;
        if (type === 'sales') btn = elements.scanSalesBtn;
        if (type === 'insurance') btn = elements.scanInsuranceBtn;
        
        btn.disabled = true;
        btn.innerText = 'Scanning...';
        
        let endpoint = '/dms/scan';
        if (type === 'sales') endpoint = '/dms/scan/sales';
        if (type === 'insurance') endpoint = '/dms/scan/insurance';
        
        const res = await fetch(`${API_BASE}${endpoint}`, {
            headers: { 'ngrok-skip-browser-warning': 'true' }
        });
        dueCustomers = await res.json();
        
        elements.scanCount.innerText = `${dueCustomers.length} Targets Identified`;
        elements.dueList.innerHTML = dueCustomers.map(c => `
            <div class="mini-item">
                <div class="info">
                    <div class="name">${c.name}</div>
                    <div class="model">${c.car_model}</div>
                </div>
                <div class="badge-mini ${c.campaign_type || ''}">${c.campaign_type ? c.campaign_type.toUpperCase() : (type === 'service' ? c.due_months + 'm Due' : 'Upgrade Potential')}</div>
            </div>
        `).join('');
        
        elements.dmsResults.classList.remove('hidden');
        btn.innerText = 'Scan Complete';
    } catch (e) {
        console.error('Scan failed', e);
    }
}

async function startCampaign() {
    if (dueCustomers.length === 0) return;
    
    elements.startCampaignBtn.disabled = true;
    elements.campaignProgress.classList.remove('hidden');
    
    try {
        // Queue Processing (Trigger calls one by one from UI for demo control)
        // We let the UI drive the sequence to maintain real-time visibility in the dashboard
        for (let i = 0; i < dueCustomers.length; i++) {
            const c = dueCustomers[i];
            const percent = Math.round(((i + 1) / dueCustomers.length) * 100);
            
            elements.campaignStatus.innerText = `Calling ${c.name}...`;
            elements.campaignPercent.innerText = `${percent}%`;
            elements.progressBar.style.width = `${percent}%`;
            
            // Pass the campaign context to startCall
            const campaignParams = {
                campaign_type: c.campaign_type || (elements.scanInsuranceBtn.disabled ? 'insurance' : 'sales'),
                vehicle_age: c.vehicle_age,
                stage: c.stage || 1
            };
            
            await startCall(c.id, c.phone, campaignParams);
            
            // Wait for call to finish before next one
            while (activeCallSid) {
                await new Promise(r => setTimeout(r, 2000));
            }
            
            await new Promise(r => setTimeout(r, 1000)); 
        }
        
        elements.campaignStatus.innerText = 'Campaign Complete!';
        elements.startCampaignBtn.innerText = 'Finished';
        
        // Reset buttons
        elements.scanServiceBtn.disabled = false;
        elements.scanServiceBtn.innerText = 'Scan Service Due';
        elements.scanSalesBtn.disabled = false;
        elements.scanSalesBtn.innerText = 'Scan Upgrade Potential';
        elements.scanInsuranceBtn.disabled = false;
        elements.scanInsuranceBtn.innerText = 'Scan Insurance Renewals';
    } catch (e) {
        console.error('Campaign failed', e);
        elements.campaignStatus.innerText = 'Campaign Error';
        elements.startCampaignBtn.disabled = false;
    }
}

async function resetLocks() {
    const btn = elements.resetLocksBtn;
    if (!btn) return;
    
    const originalText = btn.innerText;
    btn.disabled = true;
    btn.innerText = 'Clearing...';
    btn.style.opacity = '0.7';

    try {
        const res = await fetch(`${API_BASE}/telephony/reset-locks`, {
            method: 'POST',
            headers: {
                'ngrok-skip-browser-warning': 'true'
            }
        });
        
        const data = await res.json();
        if (res.ok && data.status === 'success') {
            btn.innerText = 'Cleared!';
            btn.style.borderColor = 'rgba(74, 222, 128, 0.4)';
            btn.style.color = '#4ade80';
            btn.style.background = 'rgba(74, 222, 128, 0.05)';
            
            // Reload customer list automatically so user sees fresh state
            if (typeof loadCustomers === 'function') {
                loadCustomers();
            }
            
            setTimeout(() => {
                btn.disabled = false;
                btn.innerText = originalText;
                btn.style.borderColor = 'rgba(255, 68, 68, 0.4)';
                btn.style.color = '#ff5555';
                btn.style.background = 'rgba(255, 68, 68, 0.05)';
                btn.style.opacity = '1';
            }, 3000);
        } else {
            throw new Error(data.detail || 'Reset failed');
        }
    } catch (e) {
        console.error('Reset failed', e);
        btn.innerText = 'Error!';
        setTimeout(() => {
            btn.disabled = false;
            btn.innerText = originalText;
            btn.style.opacity = '1';
        }, 3000);
        alert(`Failed to reset locks: ${e.message}`);
    }
}

// Init
document.addEventListener('DOMContentLoaded', async () => {
    initElements();
    if (elements.resetLocksBtn) elements.resetLocksBtn.onclick = resetLocks;
    if (elements.scanServiceBtn) elements.scanServiceBtn.onclick = () => scanDms('service');
    if (elements.scanSalesBtn) elements.scanSalesBtn.onclick = () => scanDms('sales');
    if (elements.scanInsuranceBtn) elements.scanInsuranceBtn.onclick = () => scanDms('insurance');
    if (elements.startCampaignBtn) elements.startCampaignBtn.onclick = startCampaign;
    if (elements.loginBtn) elements.loginBtn.onclick = handleLogin;
    if (elements.loginPass) elements.loginPass.onkeypress = (e) => { if (e.key === 'Enter') handleLogin(); };
    
    // Chat Event Listeners
    if (elements.chatSendBtn) elements.chatSendBtn.onclick = () => sendChatMessage();
    if (elements.chatInput) {
        elements.chatInput.onkeypress = (e) => {
            if (e.key === 'Enter') sendChatMessage();
        };
    }

    console.log('Alcon Dashboard Initialized');
});

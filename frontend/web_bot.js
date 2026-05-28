const API_BASE = "http://localhost:8000";

// Generate or retrieve Session ID
let sessionId = localStorage.getItem("alcon_session_id");
if (!sessionId) {
    sessionId = "web_" + Math.random().toString(36).substr(2, 9);
    localStorage.setItem("alcon_session_id", sessionId);
}

const chatContainer = document.getElementById("chat-container");
const userInput = document.getElementById("user-input");
const sendBtn = document.getElementById("send-btn");
const stateLabel = document.getElementById("state-label");
const currentUiState = document.getElementById("current-ui-state");
const progressFill = document.getElementById("progress-fill");

function addMessage(text, isUser = false) {
    const msgDiv = document.createElement("div");
    msgDiv.className = `message ${isUser ? 'user-message' : 'bot-message'}`;
    msgDiv.innerText = text;
    chatContainer.appendChild(msgDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
    return msgDiv;
}

function addOptions(options) {
    if (!options || options.length === 0) return;
    
    const optionsContainer = document.createElement("div");
    optionsContainer.className = "options-container";
    
    options.forEach(opt => {
        const btn = document.createElement("button");
        btn.className = "option-btn";
        btn.innerText = opt;
        btn.onclick = () => sendQuickMessage(opt);
        optionsContainer.appendChild(btn);
    });
    
    chatContainer.appendChild(optionsContainer);
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

async function sendMessage(text) {
    if (!text.trim()) return;
    
    addMessage(text, true);
    userInput.value = "";
    
    // Add typing indicator
    const typing = addMessage("...", false);
    
    try {
        const response = await fetch(`${API_BASE}/chat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                session_id: sessionId,
                message: text
            })
        });
        
        const data = await response.json();
        
        // Remove typing indicator
        chatContainer.removeChild(typing);
        
        addMessage(data.text);
        addOptions(data.options);
        
        // Update Flow Explainer
        stateLabel.innerText = data.ui_state;
        currentUiState.innerText = "Processing...";
        setTimeout(() => currentUiState.innerText = "Online", 1000);
        
        // Update Progress Bar (Simple mapping)
        const progressMap = {
            "Initial Greeting": 10,
            "Service Check": 30,
            "Selecting Date": 50,
            "Vehicle Details": 70,
            "Health Check": 80,
            "Pick & Drop Options": 90,
            "Service Confirmed": 100
        };
        progressFill.style.width = (progressMap[data.ui_state] || 0) + "%";
        
    } catch (error) {
        console.error("Chat Error:", error);
        chatContainer.removeChild(typing);
        addMessage("Sorry, I'm having trouble connecting. Please try again later.");
    }
}

function sendQuickMessage(text) {
    sendMessage(text);
}

sendBtn.onclick = () => sendMessage(userInput.value);
userInput.onkeypress = (e) => {
    if (e.key === "Enter") sendMessage(userInput.value);
};

const API_BASE = 'http://localhost:8000';

let currentCustomer = null;
let callStartTime = null;
let callTimerInterval = null;

// Views
const views = {
    setup: document.getElementById('setup-view'),
    call: document.getElementById('call-view'),
    success: document.getElementById('success-view')
};

const elements = {
    customerList: document.getElementById('customer-list'),
    transcript: document.getElementById('transcript'),
    actions: document.getElementById('user-actions'),
    timer: document.getElementById('call-timer'),
    status: document.getElementById('status-pill'),
    successMsg: document.getElementById('success-msg'),
    waveform: document.getElementById('waveform')
};

let currentActions = [];
let recognition = null;
let currentConversation = [];

// Date parsing logic
function parseDatePhrase(input) {
    const today = new Date();
    const dayNames = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday'];
    const monthNames = ['january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december'];
    
    input = input.toLowerCase();
    
    // Relative dates
    if (input.includes('tomorrow')) {
        const d = new Date(today);
        d.setDate(today.getDate() + 1);
        return d;
    }
    
    // Days of week
    for (let i = 0; i < 7; i++) {
        if (input.includes(dayNames[i])) {
            const d = new Date(today);
            let daysUntil = (i - today.getDay() + 7) % 7;
            if (daysUntil === 0) daysUntil = 7; // Assume next week if saying today's day
            d.setDate(today.getDate() + daysUntil);
            return d;
        }
    }
    
    // Specific dates like "18th", "19th April"
    const dayMatch = input.match(/(\d+)(st|nd|rd|th)?/);
    if (dayMatch) {
        const day = parseInt(dayMatch[1]);
        const d = new Date(today);
        
        // Check for month
        let month = today.getMonth();
        for (let i = 0; i < 12; i++) {
            if (input.includes(monthNames[i])) { month = i; break; }
        }
        
        d.setMonth(month);
        d.setDate(day);
        
        // If date is in the past, assume next year (or next month if just day mentioned)
        if (d < today && !input.includes(monthNames[month])) {
            d.setMonth(month + 1);
        }
        
        return d;
    }
    
    return null;
}

function formatDateFull(date) {
    const options = { weekday: 'long', month: 'long', day: 'numeric' };
    return date.toLocaleDateString('en-US', options);
}

// Initialize Speech Recognition
if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'en-US';

    recognition.onstart = () => {
        elements.status.innerText = 'Listening...';
        elements.status.style.background = '#fbbf24';
        elements.waveform.classList.remove('hidden');
    };

    recognition.onresult = (event) => {
        const text = event.results[0][0].transcript;
        console.log('User said:', text);
        handleVoiceInput(text);
    };

    recognition.onend = () => {
        elements.waveform.classList.add('hidden');
        if (elements.status.innerText === 'Listening...') {
            elements.status.innerText = 'Ready';
            elements.status.style.background = '#4ade80';
        }
    };

    recognition.onerror = (event) => {
        console.error('Speech Recognition Error:', event.error);
        elements.waveform.classList.add('hidden');
    };
}

// State handling
function switchView(viewName) {
    Object.keys(views).forEach(key => {
        views[key].classList.add('hidden');
    });
    views[viewName].classList.remove('hidden');
}

async function loadCustomers() {
    try {
        const response = await fetch(`${API_BASE}/customers`);
        const customers = await response.json();
        
        elements.customerList.innerHTML = customers.map(c => `
            <div class="customer-card" onclick="startCall('${c.id}')">
                <h3>${c.name}</h3>
                <p>${c.car_model} • ${c.phone}</p>
            </div>
        `).join('');
    } catch (err) {
        console.error('Failed to load customers:', err);
        elements.customerList.innerHTML = '<p>Offline: Ensure backend is running.</p>';
        elements.status.style.background = '#ef4444';
        elements.status.innerText = 'Offline';
    }
}

async function startCall(customerId) {
    try {
        const statusResponse = await fetch(`${API_BASE}/customer/${customerId}/status`);
        currentCustomer = await statusResponse.json();
        
        switchView('call');
        elements.transcript.innerHTML = '';
        startTimer();
        
        // Step 1: Greeting
        await speakAndShow(`Hello, am I speaking with ${currentCustomer.customer.name}?`);
        showActions([
            { text: `Yes, this is ${currentCustomer.customer.name}`, action: () => proceedToNext('intro') },
            { text: 'No, wrong number', action: () => {
                speakAndShow("My apologies, I must have the wrong number. Have a wonderful day!").then(() => setTimeout(endCall, 2000));
            }}
        ]);
    } catch (err) {
        console.error('Call initialization failed:', err);
    }
}

async function proceedToNext(step) {
    clearActions();
    
    if (step === 'intro') {
        await speakAndShow(`This is Supriya from Alcon Hyundai regarding your car, the ${currentCustomer.customer.car_model}.`);
        
        if (currentCustomer.is_due) {
            await speakAndShow(`Your last service was about ${currentCustomer.months_since_last} months ago, and your next service is due now. Would you like to book an appointment?`);
            showActions([
                { text: 'Yes, help me book', action: () => proceedToNext('booking') },
                { text: 'Not right now', action: () => speakAndShow("Understood. Have a great day!").then(() => setTimeout(endCall, 2000)) }
            ]);
        } else {
            await speakAndShow(`I checked our records and your car is performing well! Your next service isn't due yet. We'll call you when it is. Have a great day!`);
            setTimeout(endCall, 3000);
        }
    } 
    
    else if (step === 'booking') {
        await speakAndShow(`Great. May I know your preferred date for the service?`);
        showActions([
            { text: 'Tomorrow morning', action: () => confirmBooking('Tomorrow morning') },
            { text: 'This weekend', action: () => confirmBooking('This weekend') }
        ]);
    }
}

async function confirmBooking(time) {
    clearActions();
    await speakAndShow(`Perfect. Your appointment for ${time} is confirmed. A driver will pick up the car from your address.`);
    await fetch(`${API_BASE}/book`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ customer_id: currentCustomer.customer.id, time })
    });
    
    setTimeout(() => {
        stopTimer();
        switchView('success');
        elements.successMsg.innerText = `Appointment at ${time} for ${currentCustomer.customer.name} confirmed.`;
    }, 3000);
}

// Helpers
async function speakAndShow(text) {
    if (recognition) { 
        try { recognition.stop(); } catch(e) {} 
    }
    elements.waveform.classList.add('hidden');

    const msgDiv = document.createElement('div');
    msgDiv.className = 'bot-msg';
    msgDiv.innerHTML = `<span class="msg-label">Supriya</span>${text}`;
    elements.transcript.appendChild(msgDiv);
    elements.transcript.scrollTop = elements.transcript.scrollHeight;

    elements.status.innerText = 'Speaking...';
    elements.status.style.background = '#00aad2';
    
    console.log('Requesting TTS for:', text);
    
    try {
        const response = await fetch(`${API_BASE}/tts`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text })
        });
        
        if (response.ok) {
            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            const audio = new Audio(url);
            
            return new Promise(resolve => {
                audio.onended = () => {
                    elements.status.innerText = 'Ready';
                    elements.status.style.background = '#4ade80';
                    if (recognition) recognition.start();
                    resolve();
                };
                audio.onerror = () => {
                    elements.status.innerText = 'Ready';
                    elements.status.style.background = '#4ade80';
                    resolve();
                };
                audio.play().catch(() => resolve());
            });
        }
    } catch (err) {
        console.warn('TTS failed:', err);
        elements.status.innerText = 'Ready';
        elements.status.style.background = '#4ade80';
    }
}

function showActions(actions) {
    currentActions = actions;
    elements.actions.innerHTML = '';
    actions.forEach(a => {
        const btn = document.createElement('button');
        btn.className = 'action-btn';
        btn.innerText = a.text;
        btn.onclick = a.action;
        elements.actions.appendChild(btn);
    });
}

function handleVoiceInput(text) {
    const input = text.toLowerCase();
    
    const msgDiv = document.createElement('div');
    msgDiv.className = 'user-msg';
    msgDiv.innerHTML = `<span class="msg-label">You</span>${text}`;
    elements.transcript.appendChild(msgDiv);
    elements.transcript.scrollTop = elements.transcript.scrollHeight;
    
    let matched = false;
    
    // Improved Matching Logic
    if (input.includes('no') || input.includes('not') || input.includes('wrong') || input.includes('cancel')) {
        const noAction = currentActions.find(a => a.text.toLowerCase().includes('no') || a.text.toLowerCase().includes('not'));
        if (noAction) { noAction.action(); matched = true; }
    }
    
    if (!matched && (input.includes('yes') || input.includes('yeah') || input.includes('sure') || input.includes('speaking') || input.includes('correct') || input.includes('book'))) {
        const yesAction = currentActions.find(a => a.text.toLowerCase().includes('yes') || a.text.toLowerCase().includes('correct') || a.text.toLowerCase().includes('book'));
        if (yesAction) { yesAction.action(); matched = true; }
    }
    
    // Date Logic for Booking
    if (!matched) {
        const isBookingStep = currentActions.some(a => a.text.toLowerCase().includes('morning') || a.text.toLowerCase().includes('weekend'));
        if (isBookingStep) {
            const parsedDate = parseDatePhrase(input);
            if (parsedDate) {
                const dayStr = formatDateFull(parsedDate);
                const timeStr = parsedDate.getDay() === 0 || parsedDate.getDay() === 6 ? "11:00 AM" : "10:00 AM";
                confirmBooking(`${dayStr} at ${timeStr}`);
                matched = true;
            } else {
                // FALLBACK for demo: use original buttons if no date found
                if (input.includes('morning')) confirmBooking('Tomorrow morning at 9:30 AM');
                else if (input.includes('weekend')) confirmBooking('This Saturday at 11:00 AM');
                else confirmBooking(`${text} at 10:00 AM`);
                matched = true;
            }
        }
    }
}

function clearActions() {
    elements.actions.innerHTML = '';
}

function startTimer() {
    callStartTime = Date.now();
    callTimerInterval = setInterval(() => {
        const seconds = Math.floor((Date.now() - callStartTime) / 1000);
        const m = Math.floor(seconds / 60).toString().padStart(2, '0');
        const s = (seconds % 60).toString().padStart(2, '0');
        elements.timer.innerText = `${m}:${s}`;
    }, 1000);
}

function stopTimer() {
    clearInterval(callTimerInterval);
}

async function endCall() {
    stopTimer();
    
    // Save transcript to backend
    const logData = {
        customer: currentCustomer?.customer.name,
        transcript: elements.transcript.innerText,
        duration: elements.timer.innerText
    };
    
    await fetch(`${API_BASE}/logs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(logData)
    });

    switchView('setup');
    currentCustomer = null;
}

document.getElementById('end-call').onclick = endCall;
document.getElementById('restart').onclick = () => switchView('setup');

// Init
loadCustomers();
setInterval(loadCustomers, 5000); // Heartbeat

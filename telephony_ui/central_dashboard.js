const API_BASE = 'http://localhost:8000';
let isPolling = false;
let pollInterval = null;
let currentEligibleData = null;

document.addEventListener("DOMContentLoaded", () => {
    // Initial fetch of queue status
    fetchQueueStatus();
    startQueuePolling();
});

// 1. DMS Scan Implementation with visual step animation
async function scanDMS() {
    const scanBtn = document.getElementById("scan-dms-btn");
    const progressBanner = document.getElementById("scan-progress-banner");
    const progressFill = document.getElementById("scan-progress-fill");
    const percentText = document.getElementById("scan-percent");
    const resultsText = document.getElementById("scan-results-text");
    
    // Disable controls during scan
    scanBtn.disabled = true;
    progressBanner.style.display = "flex";
    progressFill.style.width = "0%";
    percentText.innerText = "0%";
    resultsText.innerText = "Running business algorithms...";
    
    appendTerminalLog("System initiated deep DMS database table scans...", "system");

    // Start fetching eligibility in parallel
    let responseData = null;
    const fetchPromise = fetch(`${API_BASE}/campaign/scan`)
        .then(res => res.json())
        .catch(err => {
            console.error("Scan API Error:", err);
            return null;
        });

    // Animate scanning bar smoothly over 2 seconds
    for (let p = 0; p <= 100; p += 5) {
        progressFill.style.width = `${p}%`;
        percentText.innerText = `${p}%`;
        
        if (p === 30) resultsText.innerText = "Verifying DND & NCPR statuses...";
        if (p === 60) resultsText.innerText = "Analyzing timeline metrics...";
        if (p === 85) resultsText.innerText = "Mapping template conditions...";
        
        await new Promise(resolve => setTimeout(resolve, 80));
    }

    responseData = await fetchPromise;

    if (!responseData) {
        resultsText.innerText = "❌ Scan failed. Server offline.";
        scanBtn.disabled = false;
        appendTerminalLog("DMS scan aborted due to backend connection failure.", "system");
        return;
    }

    currentEligibleData = responseData;
    
    // Render staged customers in individual collapsible dropdowns
    renderStagedCustomers(responseData);
    
    // Update eligibility UI badges
    updateBadge("badge-booking", responseData.booking ? responseData.booking.length : 0);
    updateBadge("badge-pickup", responseData.pd_pickup_coordination ? responseData.pd_pickup_coordination.length : 0);
    updateBadge("badge-workshop", responseData.pd_workshop_update ? responseData.pd_workshop_update.length : 0);
    updateBadge("badge-ready", responseData.pd_ready ? responseData.pd_ready.length : 0);
    updateBadge("badge-insurance", responseData.insurance_start ? responseData.insurance_start.length : 0);
    updateBadge("badge-feedback3", responseData.feedback_3rd_day ? responseData.feedback_3rd_day.length : 0);
    updateBadge("badge-feedback15", responseData.feedback_15day_v2 ? responseData.feedback_15day_v2.length : 0);
    updateBadge("badge-presales", responseData.pre_sales ? responseData.pre_sales.length : 0);
    updateBadge("badge-inbound", responseData.reception ? responseData.reception.length : 0);

    // Update triggers eligibility status
    let totalEligible = 0;
    Object.keys(responseData).forEach(flow => {
        const count = responseData[flow] ? responseData[flow].length : 0;
        totalEligible += count;
        
        // Enable individual buttons
        const triggerBtn = getTriggerBtnByFlow(flow);
        if (triggerBtn) {
            if (count > 0) {
                triggerBtn.disabled = false;
                triggerBtn.style.opacity = "1";
            } else {
                triggerBtn.disabled = true;
                triggerBtn.style.opacity = "0.6";
            }
        }
    });

    resultsText.innerText = `✅ Scan completed: ${totalEligible} targets ready!`;
    scanBtn.disabled = false;
    
    if (totalEligible > 0) {
        document.getElementById("trigger-all-btn").disabled = false;
        appendTerminalLog(`DMS scan finished successfully. Mapped ${totalEligible} eligible campaign profiles across all 9 segments.`, "system");
    } else {
        document.getElementById("trigger-all-btn").disabled = true;
        appendTerminalLog("DMS scan finished. No eligible profiles identified today.", "system");
    }
}

function updateBadge(badgeId, count) {
    const badge = document.getElementById(badgeId);
    if (!badge) return;
    badge.innerText = `${count} Staged`;
    if (count > 0) {
        badge.classList.add("active-targets");
    } else {
        badge.classList.remove("active-targets");
    }
}

function getTriggerBtnByFlow(flow) {
    if (flow === 'booking') return document.getElementById("btn-trigger-booking");
    if (flow === 'pd_pickup_coordination') return document.getElementById("btn-trigger-pickup");
    if (flow === 'pd_workshop_update') return document.getElementById("btn-trigger-workshop");
    if (flow === 'pd_ready') return document.getElementById("btn-trigger-ready");
    if (flow === 'insurance_start') return document.getElementById("btn-trigger-insurance");
    if (flow === 'feedback_3rd_day') return document.getElementById("btn-trigger-feedback3");
    if (flow === 'feedback_15day_v2') return document.getElementById("btn-trigger-feedback15");
    if (flow === 'pre_sales') return document.getElementById("btn-trigger-presales");
    if (flow === 'reception') return document.getElementById("btn-trigger-inbound");
    return null;
}

// 2. Trigger All Staged Campaigns
async function triggerAllCampaigns() {
    if (!currentEligibleData) return;
    
    const triggerBtn = document.getElementById("trigger-all-btn");
    triggerBtn.disabled = true;
    
    appendTerminalLog("[ORCHESTRATOR] Initiating parallel-batch queueing strategy for all segments...", "system");

    // Gather all eligible segments
    const payload = {};
    Object.keys(currentEligibleData).forEach(flow => {
        if (currentEligibleData[flow] && currentEligibleData[flow].length > 0) {
            payload[flow] = currentEligibleData[flow];
        }
    });

    try {
        const response = await fetch(`${API_BASE}/campaign/trigger`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const data = await response.json();
        
        if (data.status === 'success') {
            appendTerminalLog(`Successfully queued ${data.queued_count} campaign triggers into background SQLite queue manager.`, "system");
            fetchQueueStatus();
        } else {
            appendTerminalLog(`Orchestrator Error: ${data.message}`, "system");
            triggerBtn.disabled = false;
        }
    } catch (err) {
        console.error("Trigger API Error:", err);
        appendTerminalLog("Failed to initiate triggering pipeline due to network error.", "system");
        triggerBtn.disabled = false;
    }
}

// 3. Trigger Individual Flow Campaign
async function triggerSingleCampaign(flowType) {
    if (!currentEligibleData || !currentEligibleData[flowType]) return;
    
    const triggerBtn = getTriggerBtnByFlow(flowType);
    if (triggerBtn) triggerBtn.disabled = true;
    
    appendTerminalLog(`[ORCHESTRATOR] Queueing isolated campaigns for flow: ${flowType}...`, "system");

    const payload = {};
    payload[flowType] = currentEligibleData[flowType];

    try {
        const response = await fetch(`${API_BASE}/campaign/trigger`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const data = await response.json();
        
        if (data.status === 'success') {
            appendTerminalLog(`Queued ${data.queued_count} jobs for flow '${flowType}' into central queue.`, "system");
            fetchQueueStatus();
        } else {
            appendTerminalLog(`Orchestrator Error: ${data.message}`, "system");
            if (triggerBtn) triggerBtn.disabled = false;
        }
    } catch (err) {
        console.error("Trigger Flow API Error:", err);
        appendTerminalLog("Failed to queue isolated flow due to network error.", "system");
        if (triggerBtn) triggerBtn.disabled = false;
    }
}

// 4. Polling Queue Manager & Dialog Terminal
function startQueuePolling() {
    if (isPolling) return;
    isPolling = true;
    pollInterval = setInterval(fetchQueueStatus, 1500);
}

async function fetchQueueStatus() {
    try {
        const response = await fetch(`${API_BASE}/campaign/queue`);
        const data = await response.json();
        
        // Update Queue count badge
        const queueBadge = document.getElementById("queue-count-badge");
        const clearBtn = document.getElementById("clear-queue-btn");
        
        const activeJobs = data.queue.filter(j => j.status === 'queued' || j.status === 'processing').length;
        queueBadge.innerText = `${activeJobs} Jobs Active`;
        
        if (data.queue.length > 0) {
            clearBtn.disabled = false;
        } else {
            clearBtn.disabled = true;
        }
        
        // Render queue items
        renderQueueList(data.queue);
        
        // Sync active queue status badges inside the collapsible lists
        syncStagedTargetsStatuses(data.queue);
        
        // Sync terminal logs
        syncTerminalLogs(data.logs);
        
    } catch (err) {
        console.error("Polling Queue status error:", err);
    }
}

function renderQueueList(queueItems) {
    const container = document.getElementById("queue-list-container");
    if (!queueItems || queueItems.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div>⏳</div>
                <div>Queue is currently empty. Run a DMS Scan and Trigger Campaigns to see active queue items.</div>
            </div>`;
        return;
    }

    let html = "";
    queueItems.forEach(item => {
        // Calculate progress percentage based on node count / steps
        let progress = 0;
        if (item.status === 'completed') progress = 100;
        else if (item.status === 'failed') progress = 40;
        else if (item.status === 'processing') {
            // Pick a progress depending on current node name length or randomly step it
            progress = item.progress_percent || 35;
        }

        const retriggerHtml = (item.status === 'completed' || item.status === 'failed') 
            ? `<button class="retrigger-btn" onclick="retriggerJob(${item.id})">Re-Trigger</button>` 
            : '';

        html += `
            <div class="queue-item">
                <div class="queue-item-header">
                    <div class="queue-item-title">${item.customer_name}</div>
                    <span class="queue-status-badge status-${item.status}">${item.status}</span>
                </div>
                <div class="queue-item-meta" style="display: flex; justify-content: space-between;">
                    <span>Flow: <code>${item.flow_type}</code></span>
                    <span>Car: ${item.car_model}</span>
                </div>
                <div class="progress-container">
                    <div class="progress-bar-bg">
                        <div class="progress-bar-fill" style="width: ${progress}%;"></div>
                    </div>
                </div>
                <div class="queue-item-actions">
                    <span>${item.active_node ? `Current Step: <b>${item.active_node}</b>` : 'Staged & Waiting...'}</span>
                    ${retriggerHtml}
                </div>
            </div>`;
    });
    
    container.innerHTML = html;
}

// Retrigger Completed/Failed Job
async function retriggerJob(jobId) {
    appendTerminalLog(`[ORCHESTRATOR] Re-triggering campaign job ID: ${jobId}...`, "system");
    try {
        const response = await fetch(`${API_BASE}/campaign/queue/retrigger`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ job_id: jobId })
        });
        const data = await response.json();
        if (data.status === 'success') {
            appendTerminalLog(`Job ID ${jobId} successfully re-enqueued.`, "system");
            fetchQueueStatus();
        } else {
            appendTerminalLog(`Failed to re-trigger: ${data.message}`, "system");
        }
    } catch (err) {
        console.error("Retrigger API Error:", err);
        appendTerminalLog("Retrigger failed due to network error.", "system");
    }
}

// Clear Campaign Queue
async function clearQueue() {
    if (!confirm("Are you sure you want to flush all queued and processed campaign tasks?")) return;
    
    appendTerminalLog("[ORCHESTRATOR] Flushing active SQLite campaign queue table...", "system");
    try {
        const response = await fetch(`${API_BASE}/campaign/queue/clear`, {
            method: "POST"
        });
        const data = await response.json();
        if (data.status === 'success') {
            appendTerminalLog("Campaign queue cleared completely. All logs reset.", "system");
            fetchQueueStatus();
        }
    } catch (err) {
        console.error("Clear API Error:", err);
    }
}

// Sync Scrolling Terminal Dialogue Logs
let lastTerminalLogCount = 0;
function syncTerminalLogs(logs) {
    const container = document.getElementById("terminal-logs-container");
    if (!logs || logs.length === 0) return;
    
    // Only append new lines
    if (logs.length > lastTerminalLogCount) {
        const newLogs = logs.slice(lastTerminalLogCount);
        newLogs.forEach(log => {
            const line = document.createElement("div");
            
            // Rich color parsing based on token identifiers
            if (log.includes("[SYSTEM]")) {
                line.className = "terminal-system";
            } else if (log.includes("[AI Agent]")) {
                line.className = "terminal-ai";
            } else if (log.includes("[Customer]")) {
                line.className = "terminal-customer";
            } else if (log.includes("Outcome:") || log.includes("OUTCOME_")) {
                line.className = "terminal-outcome";
            } else {
                line.className = "terminal-log";
            }
            
            line.innerText = log;
            container.appendChild(line);
        });
        
        lastTerminalLogCount = logs.length;
        // Autoscroll terminal to the bottom
        container.scrollTop = container.scrollHeight;
    }
}

function appendTerminalLog(message, type = "log") {
    const container = document.getElementById("terminal-logs-container");
    const line = document.createElement("div");
    const timestamp = new Date().toLocaleTimeString();
    
    if (type === "system") {
        line.className = "terminal-system";
        line.innerText = `[${timestamp}] [SYSTEM] ${message}`;
    } else {
        line.className = "terminal-log";
        line.innerText = `[${timestamp}] ${message}`;
    }
    
    container.appendChild(line);
    container.scrollTop = container.scrollHeight;
}

function clearTerminal() {
    const container = document.getElementById("terminal-logs-container");
    container.innerHTML = '<div class="terminal-system">[SYSTEM] Console reset. Waiting for scans...</div>';
    lastTerminalLogCount = 0;
}

// --- Dynamic Staged Customers Live Monitoring Helpers ---

// Render customer lists in the 9 collapsible campaign cards
function renderStagedCustomers(responseData) {
    Object.keys(responseData).forEach(flow => {
        const container = document.getElementById(`list-${flow}`);
        if (!container) return;
        
        const customers = responseData[flow] || [];
        if (customers.length === 0) {
            container.innerHTML = `<div style="font-size: 0.7rem; color: var(--text-secondary); text-align: center; padding: 0.5rem 0;">No active targets.</div>`;
            return;
        }
        
        let html = "";
        customers.forEach(cust => {
            const carText = cust.car_model ? `<span class="target-car">(${cust.car_model})</span>` : "";
            html += `
                <div class="target-item" data-cust-id="${cust.id}">
                    <div>
                        <span class="target-name">${cust.name}</span>
                        ${carText}
                    </div>
                    <span class="target-status staged" id="target-status-${flow}-${cust.id}">Staged</span>
                </div>`;
        });
        container.innerHTML = html;
    });
}

// Toggle collapsible dropdown list visibility
function toggleStagedTargets(flowType) {
    const dropdown = document.getElementById(`dropdown-${flowType}`);
    if (!dropdown) return;
    
    const isHidden = dropdown.style.display === "none" || dropdown.style.display === "";
    dropdown.style.display = isHidden ? "block" : "none";
    
    // Determine the corresponding toggle button element
    let btnId = "btn-toggle-booking";
    if (flowType === 'pd_pickup_coordination') btnId = "btn-toggle-pickup";
    else if (flowType === 'pd_workshop_update') btnId = "btn-toggle-workshop";
    else if (flowType === 'pd_ready') btnId = "btn-toggle-ready";
    else if (flowType === 'insurance_start') btnId = "btn-toggle-insurance";
    else if (flowType === 'feedback_3rd_day') btnId = "btn-toggle-feedback3";
    else if (flowType === 'feedback_15day_v2') btnId = "btn-toggle-feedback15";
    else if (flowType === 'pre_sales') btnId = "btn-toggle-presales";
    else if (flowType === 'reception') btnId = "btn-toggle-inbound";
    
    const btn = document.getElementById(btnId);
    if (btn) {
        btn.innerText = isHidden ? "👁️ Hide Staged" : "👁️ Show Staged";
    }
}

// Sync individual target status badges in real-time with the central queue state
function syncStagedTargetsStatuses(queueItems) {
    // 1. Reset all targets to staged by default
    const badges = document.querySelectorAll(".target-status");
    badges.forEach(badge => {
        badge.className = "target-status staged";
        badge.innerText = "Staged";
    });
    
    // 2. Map and update statuses from active or finished queue items
    if (!queueItems || queueItems.length === 0) return;
    
    queueItems.forEach(item => {
        const badge = document.getElementById(`target-status-${item.flow_type}-${item.customer_id}`);
        if (badge) {
            badge.className = `target-status ${item.status}`;
            badge.innerText = item.status.charAt(0).toUpperCase() + item.status.slice(1);
        }
    });
}

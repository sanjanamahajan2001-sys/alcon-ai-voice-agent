const API_BASE = 'http://localhost:8000'; // Local development target

async function fetchKPIs() {
    try {
        const res = await fetch(`${API_BASE}/telephony/dashboard/kpis`, {
            headers: { 'ngrok-skip-browser-warning': 'true' }
        });
        const data = await res.json();
        
        document.getElementById('kpi-total').innerText = data.total_calls || 0;
        document.getElementById('kpi-connected').innerText = data.connected_calls || 0;
        document.getElementById('kpi-conversions').innerText = data.conversions || 0;
        document.getElementById('kpi-conv-rate').innerText = (data.conversion_rate || 0) + '%';
        document.getElementById('kpi-hot').innerText = data.hot_leads || 0;
    } catch (e) {
        console.error('Failed to fetch KPIs', e);
    }
}

async function fetchLeads() {
    try {
        const res = await fetch(`${API_BASE}/telephony/dashboard/leads`, {
            headers: { 'ngrok-skip-browser-warning': 'true' }
        });
        const leads = await res.json();
        
        const tbody = document.getElementById('lead-table-body');
        if (leads.length === 0) {
            tbody.innerHTML = '<tr><td colspan="9" style="text-align: center; padding: 40px; color: var(--text-muted);">No campaign data yet. Start a call!</td></tr>';
            return;
        }

        tbody.innerHTML = leads.map(lead => `
            <tr>
                <td>
                    <div style="font-weight: 600;">${lead.customer_name || 'Unknown'}</div>
                    <div style="font-size: 0.75rem; color: var(--text-muted);">${lead.call_sid ? lead.call_sid.substring(0, 10) : 'SIM'}...</div>
                </td>
                <td>${lead.vehicle || '-'}</td>
                <td><span class="badge badge-stage-${lead.stage}">T-${lead.stage === 1 ? '30' : lead.stage === 2 ? '15' : lead.stage === 3 ? '7' : lead.stage === 4 ? '1' : 'EXP'}</span></td>
                <td><span class="badge" style="background: rgba(255,255,255,0.05);">${lead.lead_status || 'PENDING'}</span></td>
                <td style="font-size: 0.85rem; color: #4ade80;">
                    ${lead.last_action || 'Calling...'}
                    ${lead.fallback_triggered ? '<br><span style="font-size: 0.65rem; color: #f97316;">(Fallback: WhatsApp Sent)</span>' : ''}
                    ${lead.pending_updates ? `<br><span class="badge-mini" style="background: #3b82f6; font-size: 0.6rem; padding: 2px 4px; margin-top: 4px; display: inline-block;">MODIFIED</span>` : ''}
                </td>
                <td style="font-size: 0.85rem; color: #FFD700;">
                    ${lead.next_step || 'Wait'}
                    ${lead.disposition && lead.disposition.includes('STATUS:REVIEW_REQUIRED') ? `<br><span class="badge-mini" style="background: #ef4444; font-size: 0.6rem;">⚠️ REVIEW</span>` : ''}
                    ${lead.disposition && lead.disposition.includes('STATUS:CONFLICT') ? `<br><span class="badge-mini" style="background: #f59e0b; font-size: 0.6rem;">⚡ CONFLICT</span>` : ''}
                </td>
                <td style="font-size: 0.85rem; font-family: monospace; color: var(--text-muted);">${(lead.confidence_score || 1.0).toFixed(2)}</td>
                <td><span class="${lead.lead_score >= 85 ? 'score-high' : lead.lead_score >= 50 ? 'score-mid' : 'score-low'}">${lead.lead_score || 0}</span></td>
                <td>
                    <div style="display: flex; gap: 5px;">
                        <button class="action-btn-mini" onclick="viewConversation('${lead.call_sid}', '${lead.customer_name || 'Customer'}', '${lead.customer_id}')">View</button>
                        ${lead.escalation_status === 'REQUIRED' ? `
                            <button class="action-btn-mini" style="background: #ef4444; color: white;" onclick="escalateCall('${lead.call_sid}')">🚨 Take Over</button>
                        ` : lead.escalation_status === 'IN_PROGRESS' ? `
                            <button class="action-btn-mini" style="background: var(--primary-gold); color: black;" onclick="resumeAICall('${lead.call_sid}')">🔄 Resume AI</button>
                        ` : ''}
                        ${lead.disposition && lead.disposition.includes('STATUS:REVIEW_REQUIRED') ? `
                            <button class="action-btn-mini" style="background: #27ae60; color: white;" onclick="openApproveModal('${lead.call_sid}')">Approve & Sync</button>
                        ` : ''}
                    </div>
                </td>
            </tr>
        `).join('');
    } catch (e) {
        console.error('Failed to fetch leads', e);
    }
}

async function viewConversation(sid, name, customerId) {
    try {
        const res = await fetch(`${API_BASE}/telephony/leads/${sid}/conversation`, {
            headers: { 'ngrok-skip-browser-warning': 'true' }
        });
        const data = await res.json();
        const transcript = data.transcript || [];
        
        document.getElementById('modal-customer-name').innerText = `Conversation with ${name}`;
        const body = document.getElementById('modal-body');
        
        if (!transcript || transcript.length === 0) {
            body.innerHTML = '<div style="text-align: center; padding: 20px; color: var(--text-muted);">No transcript available for this call.</div>';
        } else {
            body.innerHTML = transcript.map(msg => `
                <div class="msg msg-${msg.speaker === 'Supriya' ? 'ai' : 'user'}" style="margin-bottom: 15px;">
                    <span class="msg-label" style="font-size: 0.7rem; color: var(--text-muted); display: block; margin-bottom: 4px;">${msg.speaker}</span>
                    <div class="msg-text" style="padding: 10px; border-radius: 12px; background: ${msg.speaker === 'Supriya' ? 'rgba(255,215,0,0.05)' : 'rgba(255,255,255,0.03)'}; border: 1px solid ${msg.speaker === 'Supriya' ? 'rgba(255,215,0,0.1)' : 'rgba(255,255,255,0.05)'};">
                        ${msg.tags && msg.tags.length ? msg.tags.map(t => `<span class="tag-badge">[${t}]</span>`).join('') : ''}
                        ${msg.text}
                    </div>
                </div>
            `).join('');
        }
        
        // Update modal buttons
        const footer = document.getElementById('modal-footer');
        footer.innerHTML = `
            <button class="action-btn-mini" style="flex: 1;" onclick="viewAudit('${sid}')">Audit Report</button>
            <button class="action-btn-mini" style="flex: 1; background: var(--primary-gold);" onclick="callLead('${customerId}')">Call Now</button>
            <button class="action-btn-mini" style="flex: 1; background: #4ade80;" onclick="sendQuote('${sid}')">Send Quote</button>
        `;
        
        document.getElementById('conv-modal').classList.remove('hidden');
    } catch (e) {
        console.error('Failed to fetch conversation', e);
    }
}

async function callLead(customerId) {
    if (!confirm("Start outbound call to this customer?")) return;
    try {
        await fetch(`${API_BASE}/make-call/${customerId}`, { 
            method: "POST",
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ override: true, flow_type: 'insurance_start' })
        });
        alert("Call initiated successfully.");
        closeModal();
    } catch (e) {
        alert("Failed to initiate call.");
    }
}

async function viewAudit(sid) {
    try {
        const res = await fetch(`${API_BASE}/telephony/leads/${sid}/audit`, {
            headers: { 'ngrok-skip-browser-warning': 'true' }
        });
        const audit = await res.json();
        
        const body = document.getElementById('modal-body');
        const summary = audit.audit_summary || {};
        
        body.innerHTML = `
            <div style="background: rgba(255,255,255,0.03); padding: 20px; border-radius: 16px; border: 1px solid var(--border-color);">
                <h3 style="color: var(--primary-gold); margin-bottom: 15px; font-size: 1.1rem;">IRDAI Compliance Report</h3>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                    <div class="audit-item">
                        <div style="font-size: 0.75rem; color: var(--text-muted);">Compliance Status</div>
                        <div style="font-weight: 700; color: ${audit.compliance === 'PASSED' ? '#4ade80' : '#f87171'};">${audit.compliance}</div>
                    </div>
                    <div class="audit-item">
                        <div style="font-size: 0.75rem; color: var(--text-muted);">Outcome</div>
                        <div style="font-weight: 600;">${audit.outcome || 'N/A'}</div>
                    </div>
                    <div class="audit-item">
                        <div style="font-size: 0.75rem; color: var(--text-muted);">Consent Captured</div>
                        <div style="color: ${summary.consent_taken ? '#4ade80' : '#f87171'};">${summary.consent_taken ? '✅ Yes' : '❌ No'}</div>
                    </div>
                    <div class="audit-item">
                        <div style="font-size: 0.75rem; color: var(--text-muted);">DND Compliance</div>
                        <div style="color: ${summary.dnd_respected ? '#4ade80' : '#f87171'};">${summary.dnd_respected ? '✅ Passed' : '❌ Failed'}</div>
                    </div>
                    <div class="audit-item">
                        <div style="font-size: 0.75rem; color: var(--text-muted);">No Misrepresentation</div>
                        <div style="color: ${summary.no_misrepresentation ? '#4ade80' : '#f87171'};">${summary.no_misrepresentation ? '✅ Verified' : '❌ Failed'}</div>
                    </div>
                    <div class="audit-item">
                        <div style="font-size: 0.75rem; color: var(--text-muted);">Feedback Score</div>
                        <div style="font-weight: 700; color: var(--primary-gold);">${summary.feedback_score ? summary.feedback_score + '/5' : 'PENDING'}</div>
                    </div>
                </div>
                ${summary.feedback_text ? `
                <div style="margin-top: 15px; padding: 10px; background: rgba(255,215,0,0.05); border-radius: 8px; border: 1px solid rgba(255,215,0,0.1);">
                    <div style="font-size: 0.75rem; color: var(--text-muted); margin-bottom: 4px;">Feedback Given</div>
                    <div style="font-size: 0.9rem; font-style: italic;">"${summary.feedback_text}"</div>
                </div>
                ` : ''}
                <div style="margin-top: 20px; padding-top: 15px; border-top: 1px solid var(--border-color);">
                    <div style="font-size: 0.75rem; color: var(--text-muted); margin-bottom: 5px;">Audit Timestamp</div>
                    <div style="font-size: 0.85rem; font-family: monospace;">${summary.audit_timestamp || '-'}</div>
                </div>
            </div>
        `;
    } catch (e) {
        console.error('Failed to fetch audit', e);
        alert("Audit log not available for this record yet.");
    }
}

async function sendQuote(sid) {
    try {
        await fetch(`${API_BASE}/telephony/leads/${sid}/send-quote`, { method: "POST" });
        alert("Quote sent successfully via WhatsApp.");
        closeModal();
        fetchLeads();
    } catch (e) {
        alert("Failed to send quote.");
    }
}

function closeModal() {
    document.getElementById('conv-modal').classList.add('hidden');
}

function closeApproveModal() {
    document.getElementById('approve-modal').classList.add('hidden');
}

async function openApproveModal(sid) {
    try {
        const res = await fetch(`${API_BASE}/telephony/leads/${sid}`, {
            headers: { 'ngrok-skip-browser-warning': 'true' }
        });
        const lead = await res.json();
        const updates = typeof lead.pending_updates === 'string' ? JSON.parse(lead.pending_updates || '{}') : (lead.pending_updates || {});
        
        const body = document.getElementById('approve-modal-body');
        let html = `
            <div style="margin-bottom: 20px;">
                <p style="color: var(--text-muted); font-size: 0.9rem;">The following updates were staged by the manager. Review carefully before syncing to the production DMS.</p>
                <div style="background: rgba(255,255,255,0.03); border: 1px solid var(--border-color); border-radius: 8px; padding: 15px;">
                    <table style="width: 100%; font-size: 0.9rem;">
        `;
        
        for (const [key, value] of Object.entries(updates)) {
            html += `
                <tr>
                    <td style="color: var(--primary-gold); padding: 5px 0; width: 40%; font-weight: 500;">${key.toUpperCase()}</td>
                    <td style="color: #4ade80; padding: 5px 0; font-family: monospace;">${value}</td>
                </tr>
            `;
        }
        
        html += `
                    </table>
                </div>
            </div>
        `;
        
        body.innerHTML = html;
        document.getElementById('approve-modal').classList.remove('hidden');
        document.getElementById('btn-final-sync').onclick = () => submitSync(sid);
    } catch (e) {
        console.error('Failed to open approval modal', e);
    }
}

async function submitSync(sid) {
    const btn = document.getElementById('btn-final-sync');
    btn.disabled = true;
    btn.innerText = 'Syncing...';
    
    try {
        const res = await fetch(`${API_BASE}/telephony/approve-updates/${sid}`, {
            method: 'POST'
        });
        
        if (res.ok) {
            closeApproveModal();
            fetchLeads();
            alert('Success: Data pushed to production DMS.');
        } else {
            alert('Error: DMS Sync failed. Check backend logs.');
        }
    } catch (e) {
        console.error('Sync failed', e);
    } finally {
        btn.disabled = false;
        btn.innerText = 'Confirm & Sync to DMS';
    }
}

// Polling
setInterval(() => {
    fetchKPIs();
    fetchLeads();
}, 5000);

document.addEventListener('DOMContentLoaded', () => {
    fetchKPIs();
    fetchLeads();
    
    document.getElementById('refresh-btn').onclick = () => {
        fetchKPIs();
        fetchLeads();
    };
});

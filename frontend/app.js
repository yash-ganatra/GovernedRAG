/**
 * GovernedRAG — Dashboard & Chatbot Application Logic
 * ====================================================
 * Handles: tab navigation, KPI rendering, Chart.js charts,
 *          logs table, policy search chatbot, and full audit mode.
 */

const API_BASE = '';
let currentChatMode = 'search';
let radarChart = null;
let barChart = null;

// ═══════════════════════════════════════════════════════════════════
//  TAB NAVIGATION
// ═══════════════════════════════════════════════════════════════════

document.querySelectorAll('.nav-tab').forEach(tab => {
    tab.addEventListener('click', () => {
        document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
        tab.classList.add('active');
        const viewId = 'view-' + tab.dataset.tab;
        document.getElementById(viewId).classList.add('active');

        if (tab.dataset.tab === 'logs') loadLogs();
    });
});

// ═══════════════════════════════════════════════════════════════════
//  METRICS DASHBOARD
// ═══════════════════════════════════════════════════════════════════

async function loadMetrics(fast = false) {
    const btn = fast ? document.getElementById('btn-fast-metrics') : document.getElementById('btn-refresh-metrics');
    const originalText = btn.innerHTML;
    btn.innerHTML = '⏳ Loading...';
    btn.disabled = true;

    // Reset KPI values
    ['reci', 'uqrr', 'bdi', 'ocr', 'vid', 'mdr', 'ovi', 'etbr'].forEach(m => {
        document.getElementById('val-' + m).textContent = '...';
        document.getElementById('bar-' + m).style.width = '0%';
    });

    try {
        const endpoint = fast ? '/api/metrics/fast' : '/api/metrics';
        const res = await fetch(API_BASE + endpoint);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        renderMetrics(data);
    } catch (err) {
        console.error('Metrics error:', err);
        document.getElementById('val-alcr').textContent = 'Error';
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

function renderMetrics(data) {
    const s = data.dashboard_summary || {};
    const m = data.metrics || {};

    // KPI Cards — all 8 metrics
    setKPI('reci', s.RECI, '%', 100);
    setKPI('uqrr', s.UQRR, '%', 100);
    setKPI('bdi', s.BDI, '', 1);
    setKPI('ocr', s.OCR, '%', 100);
    setKPI('vid', s.VID, '', 1);
    setKPI('mdr', s.MDR, '%', 100);
    setKPI('ovi', s.OVI, '', 1);
    setKPI('etbr', s.ETBR, '%', 100);

    // Charts
    renderRadarChart(s);
    renderBarChart(s);

    // Interpretations
    renderInterpretations(m);
}

function setKPI(id, value, suffix, max) {
    const el = document.getElementById('val-' + id);
    const bar = document.getElementById('bar-' + id);

    if (value === null || value === undefined) {
        el.textContent = 'N/A';
        bar.style.width = '0%';
        return;
    }

    const displayVal = typeof value === 'number' ?
        (suffix === '%' ? value.toFixed(1) + '%' :
            suffix === 'h' ? value.toFixed(1) + 'h' :
                value.toFixed(3)) : value;

    el.textContent = displayVal;

    const pct = Math.min((parseFloat(value) / max) * 100, 100);
    setTimeout(() => { bar.style.width = pct + '%'; }, 100);
}

function renderRadarChart(summary) {
    const ctx = document.getElementById('chart-radar').getContext('2d');
    const labels = ['RECI', 'UQRR', 'BDI', 'OCR', 'VID', 'MDR', 'OVI', 'ETBR'];
    // Invert risk metrics (lower=better), keep MDR as-is (higher=better)
    const values = [
        1 - Math.min((summary.RECI || 0) / 100, 1),
        1 - Math.min((summary.UQRR || 0) / 100, 1),
        1 - Math.min(summary.BDI || 0, 1),
        1 - Math.min((summary.OCR || 0) / 100, 1),
        1 - Math.min(summary.VID || 0, 1),
        Math.min((summary.MDR || 0) / 100, 1),  // Higher MDR = better
        1 - Math.min(summary.OVI || 0, 1),
        1 - Math.min((summary.ETBR || 0) / 100, 1),
    ];

    if (radarChart) radarChart.destroy();

    radarChart = new Chart(ctx, {
        type: 'radar',
        data: {
            labels,
            datasets: [{
                label: 'Compliance Score',
                data: values,
                backgroundColor: 'rgba(59, 130, 246, 0.15)',
                borderColor: 'rgba(59, 130, 246, 0.8)',
                pointBackgroundColor: 'rgba(59, 130, 246, 1)',
                pointBorderColor: '#fff',
                pointHoverRadius: 6,
                borderWidth: 2,
            }]
        },
        options: {
            responsive: true,
            scales: {
                r: {
                    beginAtZero: true,
                    max: 1,
                    ticks: { stepSize: 0.2, color: '#6b7394', backdropColor: 'transparent' },
                    grid: { color: 'rgba(42, 48, 80, 0.5)' },
                    pointLabels: { color: '#9ca3b8', font: { size: 12, weight: 600 } },
                }
            },
            plugins: {
                legend: { display: false },
            }
        }
    });
}

function renderBarChart(summary) {
    const ctx = document.getElementById('chart-bar').getContext('2d');
    const labels = ['RECI', 'UQRR', 'BDI', 'OCR', 'VID', 'MDR', 'OVI', 'ETBR'];
    const values = [
        (summary.RECI || 0) / 100,
        (summary.UQRR || 0) / 100,
        summary.BDI || 0,
        (summary.OCR || 0) / 100,
        summary.VID || 0,
        (summary.MDR || 0) / 100,
        summary.OVI || 0,
        (summary.ETBR || 0) / 100,
    ];
    const colors = ['#ef4444', '#f59e0b', '#8b5cf6', '#f97316', '#06b6d4', '#10b981', '#3b82f6', '#e11d48'];

    if (barChart) barChart.destroy();

    barChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels,
            datasets: [{
                label: 'Risk Level (0–1)',
                data: values,
                backgroundColor: colors.map(c => c + '40'),
                borderColor: colors,
                borderWidth: 2,
                borderRadius: 6,
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true, max: 1,
                    ticks: { color: '#6b7394' },
                    grid: { color: 'rgba(42, 48, 80, 0.3)' },
                },
                x: {
                    ticks: { color: '#9ca3b8', font: { weight: 600 } },
                    grid: { display: false },
                },
            },
            plugins: {
                legend: { display: false },
            }
        }
    });
}

function renderInterpretations(metrics) {
    const container = document.getElementById('interpretations-list');
    container.innerHTML = '';

    const order = ['RECI', 'UQRR', 'BDI', 'OCR', 'VID', 'MDR', 'OVI', 'ETBR'];
    order.forEach(key => {
        const m = metrics[key];
        if (!m) return;
        const interp = m.interpretation || m.reason || '';
        if (!interp) return;

        const div = document.createElement('div');
        div.className = 'interp-item';
        div.innerHTML = `<span class="metric-tag">${key}</span><span>${interp}</span>`;
        container.appendChild(div);
    });
}

// ═══════════════════════════════════════════════════════════════════
//  INFERENCE LOGS
// ═══════════════════════════════════════════════════════════════════

async function loadLogs() {
    const btn = document.getElementById('btn-refresh-logs');
    btn.innerHTML = '⏳ Loading...';
    btn.disabled = true;

    try {
        const res = await fetch(API_BASE + '/api/logs');
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        renderLogs(data);
    } catch (err) {
        console.error('Logs error:', err);
    } finally {
        btn.innerHTML = '<span>↻</span> Refresh';
        btn.disabled = false;
    }
}

function renderLogs(data) {
    const tbody = document.getElementById('logs-tbody');
    tbody.innerHTML = '';

    const summary = document.getElementById('logs-summary');
    summary.innerHTML = `<span style="color:var(--text-muted)">Total: <b style="color:var(--text-primary)">${data.total}</b> entries</span>`;

    (data.logs || []).forEach(log => {
        const tr = document.createElement('tr');
        const statusClass = `status-${String(log.http_status || '200')[0]}00`;
        const hasGT = log.ground_truth && log.ground_truth.trim();
        const evalScore = log.evaluation_score != null ? log.evaluation_score.toFixed(2) : '—';

        tr.innerHTML = `
            <td title="${log.query_id}">${(log.query_id || '').substring(0, 8)}...</td>
            <td title="${escapeHtml(log.user_input || '')}">${escapeHtml((log.user_input || '').substring(0, 60))}</td>
            <td>${log.policy_category || '—'}</td>
            <td>${log.latency_ms || '—'} ms</td>
            <td><span class="status-badge ${statusClass}">${log.http_status}</span></td>
            <td>${evalScore}</td>
            <td>${log.review_required ? '⚠️ Yes' : '✅ Auto'}</td>
            <td><span class="gt-badge ${hasGT ? 'gt-yes' : 'gt-no'}">${hasGT ? '✓ Yes' : '✗ No'}</span></td>
        `;
        tbody.appendChild(tr);
    });
}

// ═══════════════════════════════════════════════════════════════════
//  CHATBOT
// ═══════════════════════════════════════════════════════════════════

function setChatMode(mode) {
    currentChatMode = mode;
    document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
    document.querySelector(`.mode-btn[data-mode="${mode}"]`).classList.add('active');
}

async function sendMessage() {
    const input = document.getElementById('chat-input');
    const query = input.value.trim();
    if (!query) return;

    input.value = '';
    addMessage(query, 'user');
    addTypingIndicator();

    const sendBtn = document.getElementById('btn-send');
    sendBtn.disabled = true;

    try {
        if (currentChatMode === 'search') {
            const res = await fetch(API_BASE + '/api/query', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query }),
            });
            const data = await res.json();
            removeTypingIndicator();
            renderSearchResult(data);
        } else {
            const res = await fetch(API_BASE + '/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query }),
            });
            const data = await res.json();
            removeTypingIndicator();
            renderAuditResult(data);
        }
    } catch (err) {
        removeTypingIndicator();
        addMessage(`❌ Error: ${err.message}`, 'bot');
    } finally {
        sendBtn.disabled = false;
    }
}

function addMessage(text, type) {
    const container = document.getElementById('chat-messages');
    const div = document.createElement('div');
    div.className = `message ${type}-message`;
    div.innerHTML = `<div class="message-content"><p>${escapeHtml(text)}</p></div>`;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

function addTypingIndicator() {
    const container = document.getElementById('chat-messages');
    const div = document.createElement('div');
    div.className = 'message bot-message';
    div.id = 'typing-indicator';
    div.innerHTML = `<div class="message-content typing-indicator">
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
    </div>`;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

function removeTypingIndicator() {
    const el = document.getElementById('typing-indicator');
    if (el) el.remove();
}

function renderSearchResult(data) {
    const container = document.getElementById('chat-messages');
    const div = document.createElement('div');
    div.className = 'message bot-message';

    let html = '<div class="message-content">';

    if (data.warning) {
        html += `<p>⚠️ ${escapeHtml(data.warning)}</p>`;
    } else {
        html += `<p>Found <b>${data.total_results}</b> relevant policy clauses (threshold: ${data.distance_threshold}):</p>`;

        (data.clauses || []).forEach((clause, i) => {
            html += `
                <div class="clause-card">
                    <div class="clause-header">
                        <span class="clause-source">${escapeHtml(clause.source_file)} / ${escapeHtml(clause.section)}</span>
                        <span class="clause-distance">distance: ${clause.distance}</span>
                    </div>
                    <div class="clause-text">${escapeHtml(clause.text.substring(0, 300))}${clause.text.length > 300 ? '...' : ''}</div>
                </div>
            `;
        });
    }

    html += '</div>';
    div.innerHTML = html;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

function renderAuditResult(data) {
    const container = document.getElementById('chat-messages');
    const div = document.createElement('div');
    div.className = 'message bot-message';

    const report = data.compliance_report || {};
    const adjudication = report.step_5_adjudication || {};
    const gaps = (report.step_4_gap_analysis || {}).gaps || [];

    const statusColors = {
        'COMPLIANT': 'var(--accent-green)',
        'PARTIALLY_COMPLIANT': 'var(--accent-orange)',
        'NON_COMPLIANT': 'var(--accent-red)',
        'INSUFFICIENT_DATA': 'var(--text-muted)',
    };

    let html = '<div class="message-content">';

    // Check if the agent returned a raw_output (JSON parsing failed)
    if (report.raw_output && !report.step_5_adjudication) {
        html += `<p><b style="color: var(--accent-orange); font-size: 16px;">
                    AUDIT COMPLETE</b></p>`;
        html += `<p style="white-space: pre-wrap; color: var(--text-secondary);">${escapeHtml(report.raw_output)}</p>`;
    } else {
        const statusColor = statusColors[adjudication.overall_status] || 'var(--text-muted)';

        html += `<p><b style="color:${statusColor}; font-size: 16px;">
                    ${adjudication.overall_status || 'UNKNOWN'}</b>
                    <span style="color: var(--text-muted); margin-left: 8px;">
                    Confidence: ${adjudication.confidence_score || 'N/A'}</span></p>`;
        html += `<p>${escapeHtml(adjudication.summary || '')}</p>`;

        if (gaps.length > 0) {
            html += '<p><b>Gap Analysis:</b></p>';
            gaps.forEach(gap => {
                html += `<div class="clause-card">
                    <div class="clause-header">
                        <span class="clause-source">${escapeHtml(gap.obligation || '')}</span>
                        <span class="clause-distance">${gap.status}</span>
                    </div>
                    <div class="clause-text">${escapeHtml(gap.gap_description || '')}</div>
                </div>`;
            });
        }

        if (adjudication.recommendations && adjudication.recommendations.length > 0) {
            html += '<p><b>Recommendations:</b></p><ul>';
            adjudication.recommendations.forEach(r => {
                html += `<li style="margin-bottom:4px; color:var(--text-secondary)">${escapeHtml(r)}</li>`;
            });
            html += '</ul>';
        }
    }

    html += `<p style="color:var(--text-muted); font-size:11px; margin-top:8px;">
        Audit ID: ${escapeHtml(adjudication.audit_id || data.audit_metadata?.audit_id || '')}
        | Tools called: ${data.audit_metadata?.tools_called || 'N/A'}
    </p>`;
    html += '</div>';

    div.innerHTML = html;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

// ═══════════════════════════════════════════════════════════════════
//  REPORT GENERATION
// ═══════════════════════════════════════════════════════════════════

async function generateReport(fast = false) {
    const container = document.getElementById('report-container');
    const btnFast = document.getElementById('btn-report-fast');
    const btnFull = document.getElementById('btn-report-full');
    btnFast.disabled = true;
    btnFull.disabled = true;

    container.innerHTML = `
        <div class="report-loading">
            <div class="spinner"></div>
            <p>${fast ? '⚡ Generating quick report...' : '📄 Generating full report (computing embedding metrics)...'}</p>
        </div>`;

    try {
        const res = await fetch(API_BASE + `/api/report?fast=${fast}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        renderReport(data);
    } catch (err) {
        container.innerHTML = `<div class="report-loading"><p>❌ Error: ${escapeHtml(err.message)}</p></div>`;
    } finally {
        btnFast.disabled = false;
        btnFull.disabled = false;
    }
}

function renderReport(data) {
    const container = document.getElementById('report-container');
    const meta = data.report_metadata || {};
    const overall = data.overall_assessment || {};
    const assessments = data.metric_assessments || {};
    const logSummary = data.log_summary || {};
    const recs = data.recommendations || [];
    const interpretations = data.interpretations || {};

    // Status class mapping
    const statusClassMap = {
        'COMPLIANT': 'status-compliant',
        'PARTIALLY_COMPLIANT': 'status-partial',
        'NON_COMPLIANT': 'status-noncompliant',
    };
    const statusClass = statusClassMap[overall.status] || 'status-partial';
    const statusLabel = (overall.status || 'UNKNOWN').replace(/_/g, ' ');

    // Metric name mapping
    const metricNames = {
        RECI: 'Risk Exposure Concentration',
        UQRR: 'Unresolved Query Recurrence',
        BDI: 'Behavioural Drift Index',
        OCR: 'Overcommitment Ratio',
        VID: 'Version Impact Deviation',
        MDR: 'Monitoring Depth Ratio',
        OVI: 'Operational Volatility Index',
        ETBR: 'Escalation Breach Rate',
    };

    let html = '';

    // ─── Report Header ───
    html += `
        <div class="report-header">
            <h2>🛡️ ${escapeHtml(meta.title || 'Compliance Report')}</h2>
            <div class="report-meta">
                <span>📅 ${new Date(meta.generated_at).toLocaleString()}</span>
                <span>📋 ${meta.report_type === 'quick' ? 'Quick Report' : 'Full Report'}</span>
                <span>📜 ${(meta.frameworks || []).join(' · ')}</span>
            </div>
        </div>`;

    // ─── Overall Assessment Banner ───
    html += `
        <div class="report-overall ${statusClass}">
            <div>
                <div class="status-label">${statusLabel}</div>
                <div class="status-badges">
                    <span class="metric-count count-green">🟢 ${overall.green_metrics || 0} Green</span>
                    <span class="metric-count count-amber">🟡 ${overall.amber_metrics || 0} Amber</span>
                    <span class="metric-count count-red">🔴 ${overall.red_metrics || 0} Red</span>
                </div>
            </div>
            <div class="status-score">
                <div class="score-value">${((overall.score || 0) * 100).toFixed(0)}%</div>
                <div class="score-label">Overall Score</div>
            </div>
        </div>`;

    // ─── Metric Assessments Grid ───
    html += `<div class="report-section"><h3>📊 Metric Assessments</h3><div class="assessment-grid">`;

    const metricOrder = ['RECI', 'UQRR', 'BDI', 'OCR', 'VID', 'MDR', 'OVI', 'ETBR'];
    metricOrder.forEach(key => {
        const a = assessments[key];
        if (!a) return;
        const cardClass = a.status === 'GREEN' ? 'a-green' :
            a.status === 'AMBER' ? 'a-amber' :
                a.status === 'RED' ? 'a-red' : 'a-na';

        let displayVal = 'N/A';
        if (a.value !== null && a.value !== undefined) {
            if (a.unit === '%') displayVal = a.value.toFixed(1) + '%';
            else if (a.unit === 'hours') displayVal = a.value.toFixed(1) + 'h';
            else if (a.unit === 'score') displayVal = a.value.toFixed(3);
            else displayVal = String(a.value);
        }

        html += `
            <div class="assessment-card ${cardClass}">
                <div class="a-label">${key}</div>
                <div class="a-value">${displayVal}</div>
                <div style="font-size:11px;color:var(--text-muted);margin-bottom:6px">${metricNames[key] || key}</div>
                <span class="a-status">${a.status}</span>
            </div>`;
    });

    html += `</div></div>`;

    // ─── Interpretations ───
    html += `<div class="report-section"><h3>📝 Metric Interpretations</h3><div class="recommendations-list">`;
    metricOrder.forEach(key => {
        const interp = interpretations[key];
        if (!interp) return;
        const a = assessments[key] || {};
        const cls = a.status === 'RED' ? 'rec-critical' : a.status === 'AMBER' ? 'rec-warning' : 'rec-ok';
        html += `<div class="rec-item ${cls}"><span class="rec-icon">${key}</span><span>${escapeHtml(interp)}</span></div>`;
    });
    html += `</div></div>`;

    // ─── Log Summary ───
    html += `
        <div class="report-section">
            <h3>📋 Inference Log Summary</h3>
            <div class="log-summary-grid">
                <div class="log-stat">
                    <div class="stat-value">${logSummary.total_interactions || 0}</div>
                    <div class="stat-label">Total Interactions</div>
                </div>
                <div class="log-stat">
                    <div class="stat-value">${logSummary.error_count || 0}</div>
                    <div class="stat-label">Errors</div>
                </div>
                <div class="log-stat">
                    <div class="stat-value">${logSummary.error_rate_pct || 0}%</div>
                    <div class="stat-label">Error Rate</div>
                </div>
                <div class="log-stat">
                    <div class="stat-value">${logSummary.review_flagged || 0}</div>
                    <div class="stat-label">Flagged for Review</div>
                </div>
                <div class="log-stat">
                    <div class="stat-value">${logSummary.avg_latency_ms || 0}ms</div>
                    <div class="stat-label">Avg Latency</div>
                </div>
            </div>`;

    // Category breakdown
    const cats = logSummary.by_category || {};
    if (Object.keys(cats).length > 0) {
        html += `<div class="category-list">`;
        Object.entries(cats).forEach(([cat, count]) => {
            html += `<span class="category-chip">${escapeHtml(cat)} <span class="chip-count">${count}</span></span>`;
        });
        html += `</div>`;
    }
    html += `</div>`;

    // ─── Recommendations ───
    html += `<div class="report-section"><h3>💡 Recommendations</h3><div class="recommendations-list">`;
    recs.forEach(r => {
        const isCritical = r.startsWith('CRITICAL');
        const isOk = r.includes('acceptable thresholds');
        const cls = isCritical ? 'rec-critical' : isOk ? 'rec-ok' : 'rec-warning';
        const icon = isCritical ? '🚨' : isOk ? '✅' : '⚠️';
        html += `<div class="rec-item ${cls}"><span class="rec-icon">${icon}</span><span>${escapeHtml(r)}</span></div>`;
    });
    html += `</div></div>`;

    // ─── Actions ───
    html += `
        <div class="report-actions">
            <button class="btn btn-secondary" onclick="window.print()">🖨️ Print Report</button>
            <button class="btn btn-primary" onclick="downloadReportJSON()">📥 Download JSON</button>
        </div>`;

    container.innerHTML = html;

    // Store latest report for download
    container._reportData = data;
}

function downloadReportJSON() {
    const container = document.getElementById('report-container');
    const data = container._reportData;
    if (!data) return;

    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `compliance_report_${new Date().toISOString().split('T')[0]}.json`;
    a.click();
    URL.revokeObjectURL(url);
}

// ═══════════════════════════════════════════════════════════════════
//  UTILITIES
// ═══════════════════════════════════════════════════════════════════

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text || '';
    return div.innerHTML;
}

// ═══════════════════════════════════════════════════════════════════
//  INIT
// ═══════════════════════════════════════════════════════════════════

window.addEventListener('DOMContentLoaded', () => {
    loadMetrics(true);  // Start with fast metrics on load
});

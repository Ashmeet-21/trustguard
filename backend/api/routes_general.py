"""
TrustGuard - General Routes
Landing page with interactive testing, health check.
"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["General"])

# These get set by main.py during startup
deepfake_detector_loaded = False
liveness_detector_loaded = False
voice_detector_loaded = False


LANDING_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TrustGuard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0a0a0a;
            color: #e0e0e0;
            min-height: 100vh;
        }

        /* ── Nav ─────────────────────────────── */
        .nav {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 16px 32px;
            border-bottom: 1px solid #1a1a1a;
            position: sticky;
            top: 0;
            background: #0a0a0aee;
            backdrop-filter: blur(12px);
            z-index: 100;
        }
        .nav-logo {
            font-size: 20px;
            font-weight: 700;
            background: linear-gradient(135deg, #00d4ff, #7b2ff7);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .nav-links { display: flex; gap: 8px; }
        .nav-links a {
            padding: 6px 14px;
            border-radius: 6px;
            font-size: 13px;
            color: #999;
            text-decoration: none;
            transition: all 0.2s;
        }
        .nav-links a:hover { color: #fff; background: #1a1a1a; }
        .nav-links a.active { color: #fff; background: #1a1a1a; }
        .status-dot {
            width: 8px; height: 8px; border-radius: 50%;
            background: #4ade80; display: inline-block; margin-right: 6px;
        }

        /* ── Layout ──────────────────────────── */
        .container { max-width: 1100px; margin: 0 auto; padding: 32px 24px; }

        /* ── Header ──────────────────────────── */
        .header {
            text-align: center;
            padding: 48px 0 40px;
        }
        .header h1 {
            font-size: 40px;
            font-weight: 700;
            background: linear-gradient(135deg, #00d4ff, #7b2ff7);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 8px;
        }
        .header p { color: #666; font-size: 16px; }

        /* ── Test Panel ──────────────────────── */
        .test-section {
            display: grid;
            grid-template-columns: 380px 1fr;
            gap: 24px;
            margin-bottom: 48px;
        }

        .upload-panel {
            background: #111;
            border: 1px solid #222;
            border-radius: 12px;
            padding: 24px;
        }
        .upload-panel h2 {
            font-size: 16px;
            margin-bottom: 20px;
            color: #fff;
        }

        /* Drop zone */
        .drop-zone {
            border: 2px dashed #333;
            border-radius: 10px;
            padding: 40px 20px;
            text-align: center;
            cursor: pointer;
            transition: all 0.2s;
            margin-bottom: 20px;
            position: relative;
            overflow: hidden;
        }
        .drop-zone:hover, .drop-zone.drag-over {
            border-color: #7b2ff7;
            background: #0d0520;
        }
        .drop-zone-icon { font-size: 36px; margin-bottom: 8px; }
        .drop-zone-text { color: #666; font-size: 14px; }
        .drop-zone-text span { color: #7b2ff7; text-decoration: underline; cursor: pointer; }
        .drop-zone input { display: none; }
        .drop-zone .preview {
            max-width: 100%;
            max-height: 180px;
            border-radius: 8px;
            display: none;
        }
        .file-name {
            font-size: 12px;
            color: #888;
            margin-bottom: 16px;
            display: none;
        }

        /* Endpoint selector */
        .endpoint-selector { margin-bottom: 20px; }
        .endpoint-selector label {
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 8px;
            display: block;
        }
        .endpoint-btns {
            display: flex;
            flex-direction: column;
            gap: 6px;
        }
        .endpoint-btn {
            padding: 10px 14px;
            border-radius: 8px;
            border: 1px solid #222;
            background: #0a0a0a;
            color: #ccc;
            font-size: 13px;
            cursor: pointer;
            text-align: left;
            transition: all 0.15s;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .endpoint-btn:hover { border-color: #444; background: #111; }
        .endpoint-btn.selected {
            border-color: #7b2ff7;
            background: #0d0520;
            color: #fff;
        }
        .endpoint-btn .tag {
            font-size: 10px;
            padding: 2px 8px;
            border-radius: 4px;
            font-weight: 600;
        }
        .tag-kyc { background: #1a0d2e; color: #a78bfa; }
        .tag-deepfake { background: #0d2e1a; color: #4ade80; }
        .tag-liveness { background: #0c1d3a; color: #60a5fa; }

        /* Run button */
        .run-btn {
            width: 100%;
            padding: 12px;
            border: none;
            border-radius: 8px;
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            background: linear-gradient(135deg, #00d4ff, #7b2ff7);
            color: #fff;
        }
        .run-btn:hover { opacity: 0.9; transform: translateY(-1px); }
        .run-btn:disabled {
            opacity: 0.3;
            cursor: not-allowed;
            transform: none;
        }
        .run-btn.loading {
            background: #333;
            pointer-events: none;
        }

        /* ── Results Panel ───────────────────── */
        .results-panel {
            background: #111;
            border: 1px solid #222;
            border-radius: 12px;
            padding: 24px;
            min-height: 400px;
        }
        .results-panel h2 {
            font-size: 16px;
            margin-bottom: 20px;
            color: #fff;
        }
        .results-empty {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 300px;
            color: #444;
            font-size: 14px;
        }
        .results-empty-icon { font-size: 48px; margin-bottom: 12px; }

        /* Verdict banner */
        .verdict-banner {
            padding: 16px 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .verdict-banner.pass { background: #0d2e1a; border: 1px solid #166534; }
        .verdict-banner.fail { background: #2e0d0d; border: 1px solid #7f1d1d; }
        .verdict-banner.review { background: #2e2a0d; border: 1px solid #854d0e; }
        .verdict-icon { font-size: 28px; }
        .verdict-text h3 { font-size: 18px; margin-bottom: 2px; }
        .verdict-text h3.pass-text { color: #4ade80; }
        .verdict-text h3.fail-text { color: #f87171; }
        .verdict-text h3.review-text { color: #fbbf24; }
        .verdict-text p { font-size: 13px; color: #888; }

        /* Score bars */
        .scores { margin-bottom: 20px; }
        .score-row {
            display: flex;
            align-items: center;
            margin-bottom: 10px;
            gap: 12px;
        }
        .score-label {
            width: 130px;
            font-size: 13px;
            color: #999;
            flex-shrink: 0;
        }
        .score-bar-bg {
            flex: 1;
            height: 8px;
            background: #1a1a1a;
            border-radius: 4px;
            overflow: hidden;
        }
        .score-bar {
            height: 100%;
            border-radius: 4px;
            transition: width 0.6s ease;
        }
        .score-bar.green { background: linear-gradient(90deg, #22c55e, #4ade80); }
        .score-bar.yellow { background: linear-gradient(90deg, #eab308, #fbbf24); }
        .score-bar.red { background: linear-gradient(90deg, #dc2626, #f87171); }
        .score-value {
            width: 48px;
            text-align: right;
            font-size: 13px;
            font-weight: 600;
            font-family: monospace;
            color: #ccc;
        }

        /* Detail cards */
        .detail-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
            margin-bottom: 16px;
        }
        .detail-card {
            background: #0a0a0a;
            border: 1px solid #1a1a1a;
            border-radius: 8px;
            padding: 14px;
        }
        .detail-card-title {
            font-size: 11px;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 6px;
        }
        .detail-card-value {
            font-size: 20px;
            font-weight: 700;
        }
        .detail-card-sub { font-size: 12px; color: #666; margin-top: 2px; }
        .text-green { color: #4ade80; }
        .text-red { color: #f87171; }
        .text-yellow { color: #fbbf24; }
        .text-blue { color: #60a5fa; }

        /* Raw JSON toggle */
        .raw-toggle {
            font-size: 12px;
            color: #555;
            cursor: pointer;
            margin-top: 16px;
            user-select: none;
        }
        .raw-toggle:hover { color: #888; }
        .raw-json {
            background: #0a0a0a;
            border: 1px solid #1a1a1a;
            border-radius: 8px;
            padding: 16px;
            margin-top: 8px;
            font-family: 'SF Mono', Monaco, monospace;
            font-size: 12px;
            color: #888;
            white-space: pre-wrap;
            word-break: break-all;
            max-height: 300px;
            overflow-y: auto;
            display: none;
        }

        /* Processing time */
        .proc-time {
            font-size: 12px;
            color: #555;
            text-align: right;
            margin-top: 12px;
        }

        /* ── Stats bar ───────────────────────── */
        .stats-bar {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 12px;
            margin-bottom: 32px;
        }
        .stat-card {
            background: #111;
            border: 1px solid #222;
            border-radius: 10px;
            padding: 16px;
            text-align: center;
        }
        .stat-num {
            font-size: 28px;
            font-weight: 700;
            background: linear-gradient(135deg, #00d4ff, #7b2ff7);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .stat-label { font-size: 11px; color: #555; margin-top: 2px; }

        /* ── Footer ──────────────────────────── */
        .footer {
            text-align: center;
            padding: 24px 0;
            color: #333;
            font-size: 12px;
            border-top: 1px solid #1a1a1a;
        }
        .footer a { color: #555; text-decoration: none; }
        .footer a:hover { color: #999; }

        /* ── Responsive ──────────────────────── */
        @media (max-width: 768px) {
            .test-section { grid-template-columns: 1fr; }
            .stats-bar { grid-template-columns: repeat(2, 1fr); }
            .detail-grid { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>

    <!-- Nav -->
    <nav class="nav">
        <div class="nav-logo">TrustGuard</div>
        <div class="nav-links">
            <a href="/" class="active"><span class="status-dot"></span>Dashboard</a>
            <a href="/docs">API Docs</a>
            <a href="/redoc">ReDoc</a>
            <a href="/health">Health</a>
        </div>
    </nav>

    <div class="container">

        <!-- Header -->
        <div class="header">
            <h1>Identity Verification</h1>
            <p>Upload an image to test deepfake detection, liveness checks, or full KYC verification</p>
        </div>

        <!-- Stats -->
        <div class="stats-bar">
            <div class="stat-card">
                <div class="stat-num">13</div>
                <div class="stat-label">API Endpoints</div>
            </div>
            <div class="stat-card">
                <div class="stat-num">6</div>
                <div class="stat-label">Liveness Checks</div>
            </div>
            <div class="stat-card">
                <div class="stat-num">44</div>
                <div class="stat-label">Tests Passing</div>
            </div>
            <div class="stat-card">
                <div class="stat-num" id="scan-count">0</div>
                <div class="stat-label">Scans Today</div>
            </div>
        </div>

        <!-- Test Section -->
        <div class="test-section">

            <!-- Left: Upload + Controls -->
            <div class="upload-panel">
                <h2>Upload &amp; Test</h2>

                <div class="drop-zone" id="dropZone">
                    <div class="drop-zone-icon" id="dropIcon">&#x1F4F7;</div>
                    <div class="drop-zone-text" id="dropText">
                        Drag &amp; drop an image here<br>or <span>browse files</span>
                    </div>
                    <img class="preview" id="preview">
                    <input type="file" id="fileInput" accept="image/jpeg,image/png,image/jpg">
                </div>
                <div class="file-name" id="fileName"></div>

                <div class="endpoint-selector">
                    <label>Choose Test</label>
                    <div class="endpoint-btns">
                        <button class="endpoint-btn selected" data-url="/api/v1/verify/kyc" onclick="selectEndpoint(this)">
                            KYC Verification (Full Pipeline)
                            <span class="tag tag-kyc">RECOMMENDED</span>
                        </button>
                        <button class="endpoint-btn" data-url="/api/v1/detect/deepfake/image" onclick="selectEndpoint(this)">
                            Deepfake Detection
                            <span class="tag tag-deepfake">IMAGE</span>
                        </button>
                        <button class="endpoint-btn" data-url="/api/v1/detect/liveness" onclick="selectEndpoint(this)">
                            Liveness Detection
                            <span class="tag tag-liveness">IMAGE</span>
                        </button>
                    </div>
                </div>

                <button class="run-btn" id="runBtn" onclick="runTest()" disabled>
                    Upload an image first
                </button>
            </div>

            <!-- Right: Results -->
            <div class="results-panel">
                <h2>Results</h2>
                <div class="results-empty" id="resultsEmpty">
                    <div class="results-empty-icon">&#x1F50E;</div>
                    <div>Upload an image and click Run to see results</div>
                </div>
                <div id="resultsContent" style="display:none;"></div>
            </div>

        </div>

        <div class="footer">
            TrustGuard v1.0.0 &nbsp;&middot;&nbsp;
            Built by <a href="https://github.com/Ashmeet-21">Ashmeet Singh</a> &nbsp;&middot;&nbsp;
            <a href="/docs">API Docs</a>
        </div>
    </div>

<script>
    let selectedFile = null;
    let selectedUrl = '/api/v1/verify/kyc';

    // ── Drop Zone ────────────────────────────
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    const preview = document.getElementById('preview');
    const dropIcon = document.getElementById('dropIcon');
    const dropText = document.getElementById('dropText');
    const fileName = document.getElementById('fileName');
    const runBtn = document.getElementById('runBtn');

    dropZone.addEventListener('click', () => fileInput.click());
    dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.classList.add('drag-over'); });
    dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('drag-over');
        if (e.dataTransfer.files.length) handleFile(e.dataTransfer.files[0]);
    });
    fileInput.addEventListener('change', () => { if (fileInput.files.length) handleFile(fileInput.files[0]); });

    function handleFile(file) {
        if (!file.type.match(/image\/(jpeg|jpg|png)/)) {
            alert('Please upload a JPEG or PNG image');
            return;
        }
        selectedFile = file;
        const reader = new FileReader();
        reader.onload = (e) => {
            preview.src = e.target.result;
            preview.style.display = 'block';
            dropIcon.style.display = 'none';
            dropText.style.display = 'none';
        };
        reader.readAsDataURL(file);
        fileName.textContent = file.name + ' (' + (file.size / 1024).toFixed(1) + ' KB)';
        fileName.style.display = 'block';
        runBtn.disabled = false;
        runBtn.textContent = 'Run Analysis';
    }

    // ── Endpoint Selection ───────────────────
    function selectEndpoint(btn) {
        document.querySelectorAll('.endpoint-btn').forEach(b => b.classList.remove('selected'));
        btn.classList.add('selected');
        selectedUrl = btn.dataset.url;
    }

    // ── Run Test ─────────────────────────────
    async function runTest() {
        if (!selectedFile) return;

        runBtn.textContent = 'Analyzing...';
        runBtn.classList.add('loading');
        runBtn.disabled = true;

        const formData = new FormData();
        formData.append('file', selectedFile);

        try {
            const resp = await fetch(selectedUrl, { method: 'POST', body: formData });
            const data = await resp.json();

            if (!resp.ok) {
                showError(data.detail || 'Request failed');
                return;
            }

            displayResults(data);
            updateScanCount();
        } catch (err) {
            showError('Network error: ' + err.message);
        } finally {
            runBtn.textContent = 'Run Analysis';
            runBtn.classList.remove('loading');
            runBtn.disabled = false;
        }
    }

    // ── Display Results ──────────────────────
    function displayResults(data) {
        document.getElementById('resultsEmpty').style.display = 'none';
        const content = document.getElementById('resultsContent');
        content.style.display = 'block';

        // KYC response
        if (data.verdict) {
            content.innerHTML = renderKycResult(data);
        }
        // Deepfake response
        else if ('is_deepfake' in data) {
            content.innerHTML = renderDeepfakeResult(data);
        }
        // Liveness response
        else if ('is_live' in data) {
            content.innerHTML = renderLivenessResult(data);
        }

        // Add raw JSON toggle
        content.innerHTML += `
            <div class="raw-toggle" onclick="toggleRaw()">&#9660; Show Raw JSON</div>
            <div class="raw-json" id="rawJson">${JSON.stringify(data, null, 2)}</div>
        `;

        if (data.processing_time_ms) {
            content.innerHTML += `<div class="proc-time">Processed in ${data.processing_time_ms}ms</div>`;
        }
    }

    function renderKycResult(d) {
        const vc = d.verdict === 'PASS' ? 'pass' : d.verdict === 'FAIL' ? 'fail' : 'review';
        const vi = d.verdict === 'PASS' ? '&#x2705;' : d.verdict === 'FAIL' ? '&#x274C;' : '&#x26A0;';
        const df = d.deepfake_check;
        const lv = d.liveness_check;
        const checks = lv.checks || {};

        return `
            <div class="verdict-banner ${vc}">
                <div class="verdict-icon">${vi}</div>
                <div class="verdict-text">
                    <h3 class="${vc}-text">${d.verdict}</h3>
                    <p>${d.reason}</p>
                </div>
            </div>

            <div class="detail-grid">
                <div class="detail-card">
                    <div class="detail-card-title">Deepfake Check</div>
                    <div class="detail-card-value ${df.is_deepfake ? 'text-red' : 'text-green'}">
                        ${df.classification}
                    </div>
                    <div class="detail-card-sub">Confidence: ${(df.confidence * 100).toFixed(1)}%</div>
                </div>
                <div class="detail-card">
                    <div class="detail-card-title">Liveness Check</div>
                    <div class="detail-card-value ${lv.is_live ? 'text-green' : 'text-red'}">
                        ${lv.classification}
                    </div>
                    <div class="detail-card-sub">Score: ${(lv.liveness_score * 100).toFixed(1)}%</div>
                </div>
                <div class="detail-card">
                    <div class="detail-card-title">Overall Risk</div>
                    <div class="detail-card-value ${riskColor(d.overall_risk)}">${d.overall_risk}</div>
                </div>
                <div class="detail-card">
                    <div class="detail-card-title">Face Detected</div>
                    <div class="detail-card-value ${checks.face_detected ? 'text-green' : 'text-red'}">
                        ${checks.face_detected ? 'YES' : 'NO'}
                    </div>
                </div>
            </div>

            <div class="scores">
                ${scoreBar('Texture', checks.texture_score)}
                ${scoreBar('Frequency', checks.frequency_score)}
                ${scoreBar('Color', checks.color_score)}
                ${scoreBar('Edge Density', checks.edge_score)}
                ${scoreBar('Sharpness', checks.sharpness_score)}
            </div>
        `;
    }

    function renderDeepfakeResult(d) {
        return `
            <div class="verdict-banner ${d.is_deepfake ? 'fail' : 'pass'}">
                <div class="verdict-icon">${d.is_deepfake ? '&#x274C;' : '&#x2705;'}</div>
                <div class="verdict-text">
                    <h3 class="${d.is_deepfake ? 'fail' : 'pass'}-text">${d.classification}</h3>
                    <p>${d.is_deepfake ? 'This image appears to be AI-generated' : 'This image appears authentic'}</p>
                </div>
            </div>
            <div class="detail-grid">
                <div class="detail-card">
                    <div class="detail-card-title">Confidence</div>
                    <div class="detail-card-value text-blue">${(d.confidence * 100).toFixed(1)}%</div>
                </div>
                <div class="detail-card">
                    <div class="detail-card-title">Risk Level</div>
                    <div class="detail-card-value ${riskColor(d.risk_level)}">${d.risk_level}</div>
                </div>
            </div>
            <div class="scores">
                ${scoreBar('Real', d.probabilities?.real)}
                ${scoreBar('Fake', d.probabilities?.fake)}
            </div>
        `;
    }

    function renderLivenessResult(d) {
        const checks = d.checks || {};
        return `
            <div class="verdict-banner ${d.is_live ? 'pass' : 'fail'}">
                <div class="verdict-icon">${d.is_live ? '&#x2705;' : '&#x274C;'}</div>
                <div class="verdict-text">
                    <h3 class="${d.is_live ? 'pass' : 'fail'}-text">${d.classification}</h3>
                    <p>${d.is_live ? 'Image appears to be a live person' : 'Possible spoof detected (photo/screen/mask)'}</p>
                </div>
            </div>
            <div class="detail-grid">
                <div class="detail-card">
                    <div class="detail-card-title">Liveness Score</div>
                    <div class="detail-card-value text-blue">${(d.liveness_score * 100).toFixed(1)}%</div>
                </div>
                <div class="detail-card">
                    <div class="detail-card-title">Face Detected</div>
                    <div class="detail-card-value ${checks.face_detected ? 'text-green' : 'text-red'}">
                        ${checks.face_detected ? 'YES' : 'NO'}
                    </div>
                </div>
            </div>
            <div class="scores">
                ${scoreBar('Texture', checks.texture_score)}
                ${scoreBar('Frequency', checks.frequency_score)}
                ${scoreBar('Color', checks.color_score)}
                ${scoreBar('Edge Density', checks.edge_score)}
                ${scoreBar('Sharpness', checks.sharpness_score)}
            </div>
        `;
    }

    // ── Helpers ──────────────────────────────
    function scoreBar(label, value) {
        if (value === undefined || value === null) return '';
        const pct = (value * 100).toFixed(1);
        const cls = value >= 0.7 ? 'green' : value >= 0.4 ? 'yellow' : 'red';
        return `
            <div class="score-row">
                <div class="score-label">${label}</div>
                <div class="score-bar-bg"><div class="score-bar ${cls}" style="width:${pct}%"></div></div>
                <div class="score-value">${pct}%</div>
            </div>
        `;
    }

    function riskColor(risk) {
        if (risk === 'LOW') return 'text-green';
        if (risk === 'MEDIUM') return 'text-yellow';
        return 'text-red';
    }

    function showError(msg) {
        document.getElementById('resultsEmpty').style.display = 'none';
        const content = document.getElementById('resultsContent');
        content.style.display = 'block';
        content.innerHTML = `
            <div class="verdict-banner fail">
                <div class="verdict-icon">&#x26A0;</div>
                <div class="verdict-text">
                    <h3 class="fail-text">Error</h3>
                    <p>${msg}</p>
                </div>
            </div>
        `;
    }

    function toggleRaw() {
        const el = document.getElementById('rawJson');
        el.style.display = el.style.display === 'none' ? 'block' : 'none';
    }

    function updateScanCount() {
        const el = document.getElementById('scan-count');
        el.textContent = parseInt(el.textContent) + 1;
    }

    // Load scan count from analytics on page load
    fetch('/api/v1/analytics/summary')
        .then(r => r.json())
        .then(d => { document.getElementById('scan-count').textContent = d.total_verifications || 0; })
        .catch(() => {});
</script>

</body>
</html>
"""


@router.get("/", response_class=HTMLResponse)
async def root():
    """Landing page — interactive testing dashboard."""
    return LANDING_PAGE


@router.get("/health")
async def health_check():
    """Health check — shows which models are loaded."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "models_loaded": {
            "deepfake_detector": deepfake_detector_loaded,
            "liveness_detector": liveness_detector_loaded,
            "voice_detector": voice_detector_loaded,
        }
    }

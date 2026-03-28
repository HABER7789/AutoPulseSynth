"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || function (mod) {
    if (mod && mod.__esModule) return mod;
    var result = {};
    if (mod != null) for (var k in mod) if (k !== "default" && Object.prototype.hasOwnProperty.call(mod, k)) __createBinding(result, mod, k);
    __setModuleDefault(result, mod);
    return result;
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.PulseInspectorProvider = void 0;
const vscode = __importStar(require("vscode"));
const path = __importStar(require("path"));
/**
 * Custom editor provider that renders .pulse.json files as interactive
 * waveform + fidelity visualizations inside VS Code.
 *
 * Architecture (simple):
 *   VS Code <-- CustomTextEditorProvider --> Webview (HTML + Canvas)
 *         |                                       |
 *         |  postMessage({ type: 'update', ... }) |  (extension -> webview)
 *         |  postMessage({ type: 'reoptimize' })  |  (webview -> extension)
 *         |                                       |
 *         +-------- FastAPI backend (http) --------+
 */
class PulseInspectorProvider {
    static register(context) {
        return vscode.window.registerCustomEditorProvider('autopulsesynth.pulseInspector', new PulseInspectorProvider(context), { supportsMultipleEditorsPerDocument: false });
    }
    constructor(context) {
        this.context = context;
    }
    async resolveCustomTextEditor(document, webviewPanel, _token) {
        webviewPanel.webview.options = { enableScripts: true };
        webviewPanel.webview.html = this.getHtml(webviewPanel.webview);
        // Send document content to the webview whenever it changes
        const sendUpdate = () => {
            webviewPanel.webview.postMessage({ type: 'update', text: document.getText() });
        };
        const sub = vscode.workspace.onDidChangeTextDocument(e => {
            if (e.document.uri.toString() === document.uri.toString()) {
                sendUpdate();
            }
        });
        webviewPanel.onDidDispose(() => sub.dispose());
        // Handle messages FROM the webview
        webviewPanel.webview.onDidReceiveMessage(async (msg) => {
            if (msg.type === 'reoptimize') {
                await this.reoptimize(document, webviewPanel, msg.gate);
            }
            else if (msg.type === 'ready') {
                sendUpdate();
            }
        });
        sendUpdate();
    }
    /** Call the FastAPI backend to re-optimize and update the file */
    async reoptimize(document, panel, gate) {
        const apiUrl = vscode.workspace.getConfiguration('autopulsesynth').get('apiUrl', 'http://localhost:8000');
        panel.webview.postMessage({ type: 'status', text: 'Calling API...' });
        try {
            const http = await Promise.resolve().then(() => __importStar(require('http')));
            const body = JSON.stringify({ gate: gate || 'X', quick: true, seed: Date.now() % 10000 });
            const result = await new Promise((resolve, reject) => {
                const parsed = new URL(apiUrl + '/api/synthesize');
                const req = http.request({ hostname: parsed.hostname, port: parsed.port, path: parsed.pathname, method: 'POST', headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(body) } }, (res) => { let d = ''; res.on('data', (c) => d += c); res.on('end', () => res.statusCode === 200 ? resolve(d) : reject(new Error(`HTTP ${res.statusCode}`))); });
                req.on('error', reject);
                req.write(body);
                req.end();
            });
            // Write result back to the file (triggers update -> webview re-renders)
            const edit = new vscode.WorkspaceEdit();
            edit.replace(document.uri, new vscode.Range(0, 0, document.lineCount, 0), JSON.stringify(JSON.parse(result), null, 2));
            await vscode.workspace.applyEdit(edit);
            panel.webview.postMessage({ type: 'status', text: 'Optimization complete!' });
        }
        catch (err) {
            panel.webview.postMessage({ type: 'status', text: `Error: ${err.message}. Is the API running?` });
        }
    }
    getHtml(webview) {
        const scriptUri = webview.asWebviewUri(vscode.Uri.file(path.join(this.context.extensionPath, 'media', 'inspector.js')));
        const styleUri = webview.asWebviewUri(vscode.Uri.file(path.join(this.context.extensionPath, 'media', 'styles.css')));
        const nonce = getNonce();
        return `<!DOCTYPE html>
<html lang="en">
<head>
	<meta charset="UTF-8">
	<meta http-equiv="Content-Security-Policy"
		content="default-src 'none'; style-src ${webview.cspSource}; script-src 'nonce-${nonce}';">
	<meta name="viewport" content="width=device-width, initial-scale=1.0">
	<link href="${styleUri}" rel="stylesheet" />
	<title>Pulse Inspector</title>
</head>
<body>
	<div id="header">
		<h2>AutoPulseSynth Inspector</h2>
		<div id="status-bar"></div>
	</div>

	<div id="metrics-panel">
		<div class="metric-card" id="card-gate"><span class="label">Gate</span><span class="value" id="val-gate">—</span></div>
		<div class="metric-card" id="card-fmean"><span class="label">Fidelity (mean)</span><span class="value" id="val-fmean">—</span></div>
		<div class="metric-card" id="card-fworst"><span class="label">Fidelity (worst)</span><span class="value" id="val-fworst">—</span></div>
		<div class="metric-card" id="card-r2"><span class="label">Surrogate R²</span><span class="value" id="val-r2">—</span></div>
		<div class="metric-card" id="card-fallback"><span class="label">Baseline Fallback</span><span class="value" id="val-fallback">—</span></div>
	</div>

	<div id="charts-row">
		<div class="chart-box">
			<h3>Pulse Waveform (I/Q)</h3>
			<canvas id="canvas-waveform" width="560" height="280"></canvas>
		</div>
		<div class="chart-box">
			<h3>Robustness vs Detuning</h3>
			<canvas id="canvas-fidelity" width="560" height="280"></canvas>
		</div>
	</div>

	<div id="circuit-panel">
		<h3 id="circuit-toggle" class="toggle-header">▸ Quil-T Hardware Program (click to expand)</h3>
		<pre id="quilt-code" class="collapsed">No Quil-T program loaded.</pre>
		<div id="circuit-summary"></div>
	</div>

	<div id="bottom-row">
		<div id="params-panel">
			<h3>Optimized Parameters</h3>
			<pre id="params-text">No data loaded.</pre>
		</div>
		<div id="actions-panel">
			<h3>Actions</h3>
			<button id="btn-reoptimize">Re-Optimize (Quick)</button>
			<div id="debug-output"></div>
		</div>
	</div>

	<script nonce="${nonce}" src="${scriptUri}"></script>
</body>
</html>`;
    }
}
exports.PulseInspectorProvider = PulseInspectorProvider;
function getNonce() {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    let result = '';
    for (let i = 0; i < 32; i++) {
        result += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    return result;
}
//# sourceMappingURL=pulseInspector.js.map
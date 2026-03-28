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
exports.deactivate = exports.activate = void 0;
const vscode = __importStar(require("vscode"));
const pulseInspector_1 = require("./pulseInspector");
function activate(context) {
    console.log('AutoPulseSynth Inspector activated');
    // Register custom editor for .pulse.json files
    context.subscriptions.push(pulseInspector_1.PulseInspectorProvider.register(context));
    // Command: open any JSON file in the inspector
    context.subscriptions.push(vscode.commands.registerCommand('autopulsesynth.openInspector', async () => {
        const uris = await vscode.window.showOpenDialog({
            filters: { 'Pulse JSON': ['json'] },
            canSelectMany: false,
        });
        if (uris && uris[0]) {
            vscode.commands.executeCommand('vscode.openWith', uris[0], 'autopulsesynth.pulseInspector');
        }
    }));
    // Command: run a quick optimization and open result
    context.subscriptions.push(vscode.commands.registerCommand('autopulsesynth.quickOptimize', async () => {
        const gate = await vscode.window.showQuickPick(['X', 'SX'], { placeHolder: 'Select target gate' });
        if (!gate) {
            return;
        }
        const apiUrl = vscode.workspace.getConfiguration('autopulsesynth').get('apiUrl', 'http://localhost:8000');
        await vscode.window.withProgress({ location: vscode.ProgressLocation.Notification, title: `Optimizing ${gate} gate...`, cancellable: false }, async () => {
            try {
                const http = await Promise.resolve().then(() => __importStar(require('http')));
                const body = JSON.stringify({ gate, quick: true, seed: 42 });
                const result = await httpPost(http, apiUrl + '/api/synthesize', body);
                const parsed = JSON.parse(result);
                // Save result as .pulse.json
                const wsFolder = vscode.workspace.workspaceFolders?.[0];
                if (!wsFolder) {
                    vscode.window.showErrorMessage('Open a workspace first.');
                    return;
                }
                const filePath = vscode.Uri.joinPath(wsFolder.uri, `optimized_${gate.toLowerCase()}.pulse.json`);
                const content = Buffer.from(JSON.stringify(parsed, null, 2));
                await vscode.workspace.fs.writeFile(filePath, content);
                vscode.commands.executeCommand('vscode.openWith', filePath, 'autopulsesynth.pulseInspector');
            }
            catch (err) {
                vscode.window.showErrorMessage(`Optimization failed: ${err.message}. Is the API running at ${apiUrl}?`);
            }
        });
    }));
}
exports.activate = activate;
/** Simple HTTP POST helper (no external deps) */
function httpPost(http, url, body) {
    return new Promise((resolve, reject) => {
        const parsed = new URL(url);
        const req = http.request({ hostname: parsed.hostname, port: parsed.port, path: parsed.pathname, method: 'POST', headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(body) } }, (res) => {
            let data = '';
            res.on('data', (chunk) => data += chunk);
            res.on('end', () => res.statusCode === 200 ? resolve(data) : reject(new Error(`HTTP ${res.statusCode}: ${data}`)));
        });
        req.on('error', reject);
        req.write(body);
        req.end();
    });
}
function deactivate() { }
exports.deactivate = deactivate;
//# sourceMappingURL=extension.js.map
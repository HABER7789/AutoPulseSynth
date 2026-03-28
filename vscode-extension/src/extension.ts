import * as vscode from 'vscode';
import { PulseInspectorProvider } from './pulseInspector';

export function activate(context: vscode.ExtensionContext) {
	console.log('AutoPulseSynth Inspector activated');

	// Register custom editor for .pulse.json files
	context.subscriptions.push(PulseInspectorProvider.register(context));

	// Command: open any JSON file in the inspector
	context.subscriptions.push(
		vscode.commands.registerCommand('autopulsesynth.openInspector', async () => {
			const uris = await vscode.window.showOpenDialog({
				filters: { 'Pulse JSON': ['json'] },
				canSelectMany: false,
			});
			if (uris && uris[0]) {
				vscode.commands.executeCommand('vscode.openWith', uris[0], 'autopulsesynth.pulseInspector');
			}
		})
	);

	// Command: run a quick optimization and open result
	context.subscriptions.push(
		vscode.commands.registerCommand('autopulsesynth.quickOptimize', async () => {
			const gate = await vscode.window.showQuickPick(['X', 'SX'], { placeHolder: 'Select target gate' });
			if (!gate) { return; }

			const apiUrl = vscode.workspace.getConfiguration('autopulsesynth').get<string>('apiUrl', 'http://localhost:8000');

			await vscode.window.withProgress(
				{ location: vscode.ProgressLocation.Notification, title: `Optimizing ${gate} gate...`, cancellable: false },
				async () => {
					try {
						const http = await import('http');
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
					} catch (err: any) {
						vscode.window.showErrorMessage(`Optimization failed: ${err.message}. Is the API running at ${apiUrl}?`);
					}
				}
			);
		})
	);
}

/** Simple HTTP POST helper (no external deps) */
function httpPost(http: any, url: string, body: string): Promise<string> {
	return new Promise((resolve, reject) => {
		const parsed = new URL(url);
		const req = http.request(
			{ hostname: parsed.hostname, port: parsed.port, path: parsed.pathname, method: 'POST', headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(body) } },
			(res: any) => {
				let data = '';
				res.on('data', (chunk: string) => data += chunk);
				res.on('end', () => res.statusCode === 200 ? resolve(data) : reject(new Error(`HTTP ${res.statusCode}: ${data}`)));
			}
		);
		req.on('error', reject);
		req.write(body);
		req.end();
	});
}

export function deactivate() {}

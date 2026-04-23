const vscode = require('vscode');
const https = require('https');
const http = require('http');
const fs = require('fs');
const path = require('path');

function logDebug(msg) {
    try {
        const d = new Date().toISOString();
        const f = path.join(getWorkspaceRoot() || __dirname, 'bridge_debug.log');
        fs.appendFileSync(f, `[${d}] ${msg}\n`);
    } catch(e) { console.error("logDebug Error:", e); }
}
let server;
const PORT = 38124;

let telegramPollingTimeout;
let periodicIntervalId;
let typingIntervalId;
let lastUpdateId = 0;
let latestChatId = null;
let activeTypingChats = new Set();
let activationTime = Math.floor(Date.now() / 1000);

let isAgentBusy = false;
let busyTimeout = null;

function setAgentBusy() {
    isAgentBusy = true;
    if (busyTimeout) clearTimeout(busyTimeout);
    // Timeout dự phòng 15 phút nếu Agent bị lỗi không tạo được file response
    busyTimeout = setTimeout(() => { isAgentBusy = false; }, 15 * 60 * 1000);
}

function queueMessage(chatId, queryToAgent) {
    const config = getConfig();
    if (!config.workingDir) return;
    const pendingPath = path.join(config.workingDir, 'pending_messages.json');
    let pending = [];
    if (fs.existsSync(pendingPath)) {
        try {
            pending = JSON.parse(fs.readFileSync(pendingPath, 'utf8'));
        } catch(e) { pending = []; }
    }
    pending.push({ chatId, queryToAgent });
    fs.writeFileSync(pendingPath, JSON.stringify(pending, null, 2));
}

function checkPendingMessages() {
    const config = getConfig();
    if (!config.workingDir) return;
    const pendingPath = path.join(config.workingDir, 'pending_messages.json');
    if (fs.existsSync(pendingPath)) {
        try {
            const pendingParams = JSON.parse(fs.readFileSync(pendingPath, 'utf8'));
            if (pendingParams && pendingParams.length > 0) {
                fs.unlinkSync(pendingPath);

                let combinedQuery = "Trong lúc bạn đang bận, người dùng đã gửi các tin nhắn sau. Hãy xem xét và xử lý TOÀN BỘ chúng:\n\n";
                pendingParams.forEach((item, index) => {
                    combinedQuery += `--- Tin nhắn ${index + 1} ---\n${item.queryToAgent}\n\n`;
                });
                
                const fullQuery = `${combinedQuery}__(HỆ THỐNG: Trong quá trình làm, cứ lúc nào cần báo tiến độ/nhắn người dùng thì gọi: python .agent/send_to_tele.py "<Nội_dung>". Khi chuẩn bị kết thúc toàn bộ công việc, BẮT BUỘC gọi: python .agent/send_to_tele.py "<Kết_quả_cuối>" --done để báo hệ thống rảnh!)__`;

                setAgentBusy();

                vscode.commands.executeCommand('antigravity.sendPromptToAgentPanel', fullQuery).then(() => {
                    try { vscode.commands.executeCommand('antigravity.agentSidePanel.focus'); } catch(e){}
                });

                let chats = [...new Set(pendingParams.map(i => i.chatId))];
                chats.forEach(c => {
                    activeTypingChats.add(c.toString());
                    sendTelegramMessage(c, "🔄 Đã rảnh! Anti đang bắt đầu gộp xử lý toàn bộ tin nhắn trong hàng đợi...");
                });
            }
        } catch(e) {
            console.error("Lỗi xử lý message hàng đợi", e);
        }
    }
}

function freeAgent() {
    isAgentBusy = false;
    activeTypingChats.clear();
    if (busyTimeout) clearTimeout(busyTimeout);
    checkPendingMessages();
}

// Helper to get workspace root path
function getWorkspaceRoot() {
    if (vscode.workspace.workspaceFolders && vscode.workspace.workspaceFolders.length > 0) {
        return vscode.workspace.workspaceFolders[0].uri.fsPath;
    }
    return '';
}

// Custom Config Fetcher
function getConfig() {
    const config = vscode.workspace.getConfiguration('antigravityBridge');
    const root = getWorkspaceRoot();
    
    let workingDir = config.get('agentWorkingDir') || '.agent';
    if (!path.isAbsolute(workingDir) && root) {
        workingDir = path.join(root, workingDir);
    }
    
    let promptDir = config.get('periodicPromptFile') || '.agent/periodic_prompt.md';
    if (!path.isAbsolute(promptDir) && root) {
        promptDir = path.join(root, promptDir);
    }
    
    return {
        botActive: config.get('botActive') ?? true,
        teleBotToken: config.get('teleBotToken') || '',
        whitelistChatIds: config.get('whitelistChatIds') || '',
        periodicInterval: config.get('periodicInterval') || 60,
        workingDir: workingDir,
        periodicPromptFile: promptDir
    };
}

// Send Message to Telegram
function sendTelegramMessage(chatId, text) {
    const token = getConfig().teleBotToken;
    if (!token) return;
    
    // Tự động escape các ký tự Markdown nhạy cảm để tránh lỗi 400 Bad Request
    const escapedText = text.replace(/[_*`[\]()]/g, '\\$&');
    
    const postData = JSON.stringify({
        chat_id: chatId,
        text: escapedText,
        parse_mode: 'Markdown'
    });
    
    const req = https.request({
        hostname: 'api.telegram.org',
        port: 443,
        path: `/bot${token}/sendMessage`,
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Content-Length': Buffer.byteLength(postData)
        }
    }, (res) => {
        let body = '';
        res.on('data', chunk => body += chunk);
        res.on('end', () => {
            if (res.statusCode !== 200) {
                console.error(`Telegram API Error (Send Message): [${res.statusCode}]`, body);
                logDebug(`[SEND API ERROR] [${res.statusCode}] ${body}`);
            }
        });
    });
    req.on('error', (e) => {
        console.error('Telegram Send Error', e);
        logDebug(`[SEND NETWORK ERROR] ${e.message || e}`);
    });
    req.write(postData);
    req.end();
}

function getActiveChatIds() {
    let ids = new Set();
    if (latestChatId) ids.add(latestChatId.toString());
    const config = getConfig();
    if (config.whitelistChatIds) {
        config.whitelistChatIds.split(',').forEach(id => {
            if (id.trim()) ids.add(id.trim());
        });
    }
    return Array.from(ids);
}

// Send Typing Action to Telegram
function sendTypingAction() {
    if (!isAgentBusy || activeTypingChats.size === 0) return;
    
    const config = getConfig();
    if (!config.botActive || !config.teleBotToken) return;
    
    activeTypingChats.forEach(chatId => {
        const postData = JSON.stringify({
            chat_id: chatId,
            action: 'typing'
        });
        
        const req = https.request({
            hostname: 'api.telegram.org',
            port: 443,
            path: `/bot${config.teleBotToken}/sendChatAction`,
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Content-Length': Buffer.byteLength(postData)
            }
        }, (res) => {
            res.on('data', () => {});
        });
        req.on('error', () => {});
        req.write(postData);
        req.end();
    });
}

// Check Whitelist
function isUserWhitelisted(chatId) {
    const config = getConfig();
    if (!config.whitelistChatIds) return false;
    const ids = config.whitelistChatIds.split(',').map(id => id.trim());
    return ids.includes(chatId.toString());
}

async function handleMessage(message) {
    // Bỏ qua tin nhắn cũ bị lưu đệm (nhắn trước khi IDE/Extension bật)
    if (message.date && message.date < activationTime) {
        return;
    }

    const chatId = message.chat.id;
    let text = message.text || '';
    logDebug(`[NEW MSG] From ChatId: ${chatId} | Text: ${text}`);
    
    // Loại bỏ @bot_username trong lệnh khi ở group chat
    text = text.replace(/@[a-zA-Z0-9_]+/g, '').trim();

    // Bỏ qua nếu không phải tin nhắn văn bản
    if (!text) {
        return;
    }

    if (!isUserWhitelisted(chatId)) {
        logDebug(`[AUTH BLOCKED] ChatId ${chatId} is not whitelisted. Config whitelist is: ${getConfig().whitelistChatIds}`);
        sendTelegramMessage(chatId, `⛔ Lỗi: Group/Chat ID \`${chatId}\` không có quyền truy cập hệ thống.\n\nHãy sao chép dãy số trên và thêm vào danh sách Whitelist trong cài đặt VS Code.`);
        return;
    }
    
    latestChatId = chatId;
    
    if (text === '/start' || text.startsWith('/start ')) {
        sendTelegramMessage(chatId, `Bạn đang chat với ID: \`${chatId}\`.\nĐây là kết nối bảo mật tới hệ thống Antigravity Bridge (Extension).`);
        return;
    }
    
    if (text === '/reset' || text === '/cancel' || text === '/stop') {
        isAgentBusy = false;
        activeTypingChats.clear();
        if (busyTimeout) clearTimeout(busyTimeout);
        const config = getConfig();
        if (config.workingDir) {
            const pendingPath = path.join(config.workingDir, 'pending_messages.json');
            try { fs.unlinkSync(pendingPath); } catch(e){}
        }
        
        // Thử gọi lệnh Stop của hệ thống Chat/Agent trong VS Code
        try {
            vscode.commands.executeCommand('workbench.action.chat.cancel');
        } catch (e) {}

        sendTelegramMessage(chatId, "🛑 Đã phát lệnh Stop tới Agent, gỡ kẹt trạng thái bận và xoá toàn bộ hàng đợi!");
        return;
    }
    
    let queryToAgent = text;
    if (text.startsWith('/sync_logs')) {
         queryToAgent = "Hãy chạy lệnh đồng bộ logs (sync_logs).";
    } else if (text.startsWith('/analyze_market')) {
         const parts = text.split(' ');
         queryToAgent = `Hãy chạy phân tích thị trường (${parts.length > 1 ? text.substring(text.indexOf(' ')+1) : 'ALL'}).`;
    }
    
    const fullQuery = `${queryToAgent}\n\n__(HỆ THỐNG: Trong quá trình làm, cứ lúc nào cần báo tiến độ/nhắn người dùng thì gọi: python .agent/send_to_tele.py "<Nội_dung>". Khi chuẩn bị kết thúc toàn bộ công việc, BẮT BUỘC gọi: python .agent/send_to_tele.py "<Kết_quả_cuối>" --done để báo hệ thống rảnh!)__`;
    
    if (isAgentBusy) {
        logDebug(`[QUEUEING] Agent is busy, adding message to queue for ChatId: ${chatId}`);
        queueMessage(chatId, queryToAgent);
        sendTelegramMessage(chatId, "⏳ Anti đang bận xử lý tác vụ khác. Tin nhắn của bạn đã được đưa vào hàng đợi và sẽ tự động được xử lý ngay khi Anti rảnh! (Dùng /reset nếu muốn ngắt tác vụ hiện tại)");
        return;
    }

    // Khởi tạo/cập nhật thông báo đã nhận
    sendTelegramMessage(chatId, "✅ Đã nhận lệnh, Anti đang bắt đầu xử lý...");
    activeTypingChats.add(chatId.toString());
    
    // Đặt typing indicator timeout (chỉ dùng cho mục đích hiển thị typing)
    setAgentBusy();
    
    try {
        await vscode.commands.executeCommand('antigravity.sendPromptToAgentPanel', fullQuery);
        try {
            await vscode.commands.executeCommand('antigravity.agentSidePanel.focus');
        } catch(e){}
    } catch(e) {
        console.error("Lỗi gửi lệnh", e);
    }
}

// Long Polling Telegram
function pollTelegram() {
    const config = getConfig();
    if (!config.botActive || !config.teleBotToken) {
        telegramPollingTimeout = setTimeout(pollTelegram, 5000);
        return;
    }
    
    const token = config.teleBotToken;
    
    const url = `https://api.telegram.org/bot${token}/getUpdates?offset=${lastUpdateId + 1}&timeout=30`;
    
    const req = https.get(url, (res) => {
        let body = '';
        res.on('data', chunk => body += chunk);
        res.on('end', () => {
            try {
                const data = JSON.parse(body);
                if (data.ok && data.result) {
                    for (const update of data.result) {
                        lastUpdateId = Math.max(lastUpdateId, update.update_id);
                        if (update.message) {
                            logDebug(`[POLL SUCCESS] Received update_id ${update.update_id}`);
                            handleMessage(update.message);
                        }
                    }
                }
            } catch (e) {
                console.error("Poling Parse Error", e);
                logDebug(`[POLL ERROR] ${e}`);
            }
            telegramPollingTimeout = setTimeout(pollTelegram, 1000);
        });
    });
    
    req.on('error', (e) => {
        console.error("Polling Error", e);
        logDebug(`[POLL NETWORK ERROR] ${e.message || e}`);
        telegramPollingTimeout = setTimeout(pollTelegram, 3000);
    });
}

// Periodic Prompt Execution
function setupPeriodicExecution() {
    if (periodicIntervalId) {
        clearInterval(periodicIntervalId);
    }
    
    const config = getConfig();
    if (config.botActive && config.periodicInterval > 0) {
        periodicIntervalId = setInterval(() => {
            if (isAgentBusy) {
                console.log("Agent đang bận, bỏ qua lệnh định kỳ ở chu kỳ này.");
                return;
            }
            if (fs.existsSync(config.periodicPromptFile)) {
                console.log("Triggering periodic prompt...");
                let query = fs.readFileSync(config.periodicPromptFile, 'utf8');
                let fullQuery = `${query}\n\n__(Lệnh định kỳ: Trong lúc làm có thể gọi nhiều lần lệnh: python .agent/send_to_tele.py "<Nội_dung>". Khi đã hoàn tất toàn bộ tiến trình, BẮT BUỘC chạy lệnh cuối: python .agent/send_to_tele.py "<Kết_quả_cuối>" --done )__`;
                try {
                    setAgentBusy();
                    vscode.commands.executeCommand('antigravity.sendPromptToAgentPanel', fullQuery);
                } catch(e) {
                    freeAgent();
                }
            } else {
                console.log(`Periodic prompt file not found: ${config.periodicPromptFile}`);
            }
        }, config.periodicInterval * 60 * 1000);
    }
}

function startBridgeServer() {
    if (server) {
        server.close();
    }
    
    server = http.createServer((req, res) => {
        res.setHeader('Access-Control-Allow-Origin', '*');
        res.setHeader('Access-Control-Allow-Methods', 'OPTIONS, POST');
        res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

        if (req.method === 'OPTIONS') {
            res.writeHead(204);
            res.end();
            return;
        }

        if (req.method === 'GET' && req.url === '/dump-commands') {
            vscode.commands.getCommands(true).then(cmds => {
                const agCmds = cmds.filter(c => c.toLowerCase().includes('antigravity') || c.toLowerCase().includes('agent'));
                const tempDir = path.join(getWorkspaceRoot() || __dirname, 'temp');
                if (!fs.existsSync(tempDir)) fs.mkdirSync(tempDir, { recursive: true });
                const outPath = path.join(tempDir, 'commands.json');
                fs.writeFileSync(outPath, JSON.stringify(agCmds, null, 2));
                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ status: 'success', count: agCmds.length, saved_to: outPath, commands: agCmds }));
            }).catch(err => {
                res.writeHead(500); res.end(JSON.stringify({ error: err.toString() }));
            });
            return;
        }

        if (req.method === 'POST' && req.url === '/send-chat') {
            let body = '';
            req.on('data', chunk => body += chunk.toString());
            req.on('end', async () => {
                try {
                    let task = JSON.parse(body);
                    let query = task.query;
                    if (query) {
                        try {
                            await vscode.commands.executeCommand('antigravity.sendPromptToAgentPanel', query);
                        } catch (e) {
                            console.error("Lỗi khi open chat", e);
                        }
                        res.writeHead(200, { 'Content-Type': 'application/json' });
                        res.end(JSON.stringify({ status: 'success' }));
                    } else {
                        res.writeHead(400); res.end(JSON.stringify({ error: 'Missing query' }));
                    }
                } catch (e) {
                    res.writeHead(500); res.end(JSON.stringify({ error: e.toString() }));
                }
            });
        } else if (req.method === 'POST' && req.url === '/send-telegram') {
            let body = '';
            req.on('data', chunk => body += chunk.toString());
            req.on('end', () => {
                try {
                    logDebug(`[SERVER] Received /send-telegram: ${body}`);
                    let task = JSON.parse(body);
                    let text = task.text || task.message;
                    if (text) {
                        let targets = activeTypingChats.size > 0 ? Array.from(activeTypingChats) : getActiveChatIds();
                        logDebug(`[SERVER] Sending to targets: ${JSON.stringify(targets)}`);
                        targets.forEach(t => {
                            sendTelegramMessage(t, `🤖 Antigravity:\n\n${text}`);
                        });
                        res.writeHead(200, { 'Content-Type': 'application/json' });
                        res.end(JSON.stringify({ status: 'success' }));
                        
                        if (task.done) {
                            logDebug("[SERVER] Task done, freeing agent.");
                            freeAgent(); // Chỉ Cập nhật trạng thái rảnh sau khi task.done = true
                        }
                    } else {
                        logDebug("[SERVER] Missing text in request.");
                        res.writeHead(400); res.end(JSON.stringify({ error: 'Missing text' }));
                    }
                } catch (e) {
                    logDebug(`[SERVER ERROR] ${e}`);
                    res.writeHead(500); res.end(JSON.stringify({ error: e.toString() }));
                }
            });
        } else {
            res.writeHead(404);
            res.end('Not found');
        }
    });

    server.listen(PORT, '127.0.0.1', () => {
        console.log(`Auto Click Bridge Server listening on port ${PORT}`);
    });
}

function setupTypingIndicator() {
    if (typingIntervalId) {
        clearInterval(typingIntervalId);
    }
    typingIntervalId = setInterval(sendTypingAction, 4000);
}

function ensureSendScript() {
    const config = getConfig();
    if (!config.workingDir) return;
    if (!fs.existsSync(config.workingDir)) {
        fs.mkdirSync(config.workingDir, { recursive: true });
    }
    const scriptPath = path.join(config.workingDir, 'send_to_tele.py');
    const pyContent = `import sys
import json
import urllib.request
import urllib.error

def send_to_telegram(content, is_done=False):
    if not content:
        return
    url = 'http://127.0.0.1:38124/send-telegram'
    data = json.dumps({'text': content, 'done': is_done}).encode('utf-8')
    headers = {'Content-Type': 'application/json'}
    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req) as response:
            pass
    except Exception as e:
        print(f"Lỗi gửi HTTP request: {e}", file=sys.stderr)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(1)
    is_done = '--done' in sys.argv
    content = sys.argv[1]
    send_to_telegram(content, is_done)
`;
    fs.writeFileSync(scriptPath, pyContent);
}

function activate(context) {
    console.log('Antigravity Bridge Bot is active');
    
    ensureSendScript();
    
    // Start local server backward compatibility
    startBridgeServer();
    
    // Start Polling and File Watcher
    pollTelegram();
    setupPeriodicExecution();
    setupTypingIndicator();

    let cmdRestart = vscode.commands.registerCommand('auto-click-bridge.restart', function () {
        isAgentBusy = false;
        activeTypingChats.clear();
        if (busyTimeout) clearTimeout(busyTimeout);
        ensureSendScript();
        startBridgeServer();
        // Restart polling & loop
        if (telegramPollingTimeout) clearTimeout(telegramPollingTimeout);
        pollTelegram();
        setupPeriodicExecution();
        setupTypingIndicator();
        vscode.window.showInformationMessage('Bridge Bot restarted & Agent state freed successfully.');
    });
    
    context.subscriptions.push(cmdRestart);
    
    // Listen to configuration change
    vscode.workspace.onDidChangeConfiguration(e => {
        if (e.affectsConfiguration('antigravityBridge')) {
            activationTime = Math.floor(Date.now() / 1000);
            setupPeriodicExecution();
            setupTypingIndicator();
            vscode.window.showInformationMessage('Antigravity Bridge configuration updated.');
        }
    });
}

function deactivate() {
    if (server) server.close();
    if (telegramPollingTimeout) clearTimeout(telegramPollingTimeout);
    if (periodicIntervalId) clearInterval(periodicIntervalId);
    if (typingIntervalId) clearInterval(typingIntervalId);
}

module.exports = {
    activate,
    deactivate
}

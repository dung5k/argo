const vscode = require('vscode');
const https = require('https');
const http = require('http');
const fs = require('fs');
const path = require('path');
const mqtt = require('mqtt');

function logDebug(msg) {
    try {
        const d = new Date().toISOString();
        const f = path.join(getWorkspaceRoot() || __dirname, 'bridge_debug.log');
        fs.appendFileSync(f, `[${d}] ${msg}\n`);
    } catch(e) { console.error("logDebug Error:", e); }
}
let server;
let PORT = 0;

let telegramPollingTimeout;
let periodicIntervalId;
let typingIntervalId;
let lastUpdateId = 0;
let latestChatId = null;
let activeTypingChats = new Set();
let activationTime = Math.floor(Date.now() / 1000);

let isAgentBusy = false;
let busyTimeout = null;
let heartbeatInterval = null;

let mqttClient = null;

function getLatestLogFile() {
    try {
        const brainDir = path.join(process.env.USERPROFILE || process.env.HOME || '', '.gemini', 'antigravity', 'brain');
        if (!fs.existsSync(brainDir)) return null;
        
        let latestTime = 0;
        let latestFile = null;
        
        const convDirs = fs.readdirSync(brainDir);
        for (const dir of convDirs) {
            const logPath = path.join(brainDir, dir, '.system_generated', 'logs', 'overview.txt');
            if (fs.existsSync(logPath)) {
                const stat = fs.statSync(logPath);
                if (stat.mtimeMs > latestTime) {
                    latestTime = stat.mtimeMs;
                    latestFile = logPath;
                }
            }
        }
        return latestFile;
    } catch (e) {
        return null;
    }
}

function setAgentBusy() {
    isAgentBusy = true;
    if (busyTimeout) clearTimeout(busyTimeout);
    if (heartbeatInterval) clearInterval(heartbeatInterval);

    // Timeout dự phòng 15 phút nếu Agent bị lỗi không tạo được file response
    busyTimeout = setTimeout(() => { 
        isAgentBusy = false;
        let chatIds = getActiveChatIds();
        if (chatIds.length === 0 && latestChatId) chatIds = [latestChatId.toString()];
        chatIds.forEach(c => {
            sendTelegramMessage(c, "⚠️ CẢNH BÁO HỆ THỐNG: Đã quá 15 phút mà bộ não AI không phản hồi! Có khả năng cao Agent đã hết hạn mức API (Quota Exceeded) hoặc bị treo do lỗi kết nối. Hệ thống đã tự động gỡ trạng thái bận để Sếp có thể tiếp tục ra lệnh.");
        });
        if (heartbeatInterval) clearInterval(heartbeatInterval);
    }, 15 * 60 * 1000);

    let logFile = getLatestLogFile();
    let lastMtime = logFile ? fs.statSync(logFile).mtimeMs : Date.now();
    let unchangedCount = 0;
    
    heartbeatInterval = setInterval(() => {
        if (!isAgentBusy) {
            clearInterval(heartbeatInterval);
            return;
        }
        try {
            let currentLog = getLatestLogFile();
            if (currentLog) {
                let currentMtime = fs.statSync(currentLog).mtimeMs;
                if (currentMtime === lastMtime) {
                    unchangedCount++;
                } else {
                    lastMtime = currentMtime;
                    unchangedCount = 0;
                }
            } else {
                unchangedCount++;
            }
            
            if (unchangedCount >= 12) { // 2 phút
                isAgentBusy = false;
                if (busyTimeout) clearTimeout(busyTimeout);
                clearInterval(heartbeatInterval);
                let chatIds = getActiveChatIds();
                if (chatIds.length === 0 && latestChatId) chatIds = [latestChatId.toString()];
                chatIds.forEach(c => {
                    sendTelegramMessage(c, "🚨 [HEARTBEAT BÁO ĐỘNG] Phát hiện nhịp tim AI đã ngưng đập quá 2 phút! Khả năng 100% đã hết hạn mức API (Quota Exceeded) hoặc rớt mạng. Trạng thái đã được Reset.");
                });
            }
        } catch (e) {
            console.error("Heartbeat error", e);
        }
    }, 10000);
}

function queueMessage(chatId, queryToAgent, chatName = "Unknown") {
    const config = getConfig();
    if (!config.workingDir) return;
    const pendingPath = path.join(config.workingDir, 'pending_messages.json');
    let pending = [];
    if (fs.existsSync(pendingPath)) {
        try {
            pending = JSON.parse(fs.readFileSync(pendingPath, 'utf8'));
        } catch(e) { pending = []; }
    }
    pending.push({ chatId, queryToAgent, chatName });
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

                let combinedQuery = "[BỐI CẢNH BẮT BUỘC: Trong lúc bạn đang bận, người dùng từ Telegram đã gửi các tin nhắn sau. Hãy xem xét và xử lý TOÀN BỘ chúng. MỌI PHẢN HỒI DÀNH CHO SẾP PHẢI ĐƯỢC GỬI TOÀN BỘ QUA TELEGRAM bằng lệnh `python .agent/send_to_tele.py \"<Nội_dung_đầy_đủ>\"`. TUYỆT ĐỐI KHÔNG trả lời giải thích trong khung chat IDE mà chỉ gửi tóm tắt vào Tele. Khi hoàn tất công việc, BẮT BUỘC gọi: `python .agent/send_to_tele.py \"<Kết_quả_cuối>\" --done` để báo hệ thống rảnh!]\n\n";
                pendingParams.forEach((item, index) => {
                    let cName = item.chatName || "Unknown";
                    combinedQuery += `--- Tin nhắn ${index + 1} từ "${cName}" (ID: ${item.chatId}) ---\n${item.queryToAgent}\n\n`;
                });
                
                const fullQuery = combinedQuery;

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
    if (heartbeatInterval) clearInterval(heartbeatInterval);
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
function getNetworkConfig() {
    try {
        const config = vscode.workspace.getConfiguration('antigravityBridge');
        const root = getWorkspaceRoot();
        let workingDir = config.get('agentWorkingDir') || '.agent';
        if (!path.isAbsolute(workingDir) && root) {
            workingDir = path.join(root, workingDir);
        }
        const netPath = path.join(workingDir, 'network_config.json');
        if (fs.existsSync(netPath)) {
            return JSON.parse(fs.readFileSync(netPath, 'utf8'));
        }
    } catch(e) {}
    // Fallback if network_config.json is deleted
    return {
        mqtt_broker: "mqtt://127.0.0.1:1883",
        mqtt_base_topic: "argo/network/v1/agents"
    };
}

function getAgentIdentity() {
    try {
        const config = vscode.workspace.getConfiguration('antigravityBridge');
        let identity = config.get('agentIdentity');
        if (identity && identity.trim() !== '') {
            return identity.trim();
        }
    } catch(e) {}
    return "Antigravity";
}

function setupMQTT() {
    if (mqttClient) {
        mqttClient.end();
        mqttClient = null;
    }
    const netConfig = getNetworkConfig();
    if (!netConfig || !netConfig.mqtt_broker) return;
    
    const brokerUrl = netConfig.mqtt_broker;
    const baseTopic = netConfig.mqtt_base_topic || "argo/network/v1/agents";
    const identity = getAgentIdentity();
    const inboxTopic = `${baseTopic}/${identity}/inbox`;

    logDebug(`[MQTT] Connecting to ${brokerUrl}...`);
    try {
        mqttClient = mqtt.connect(brokerUrl, {
            clientId: `bridge_${identity}_${Math.random().toString(16).substr(2, 8)}`,
            keepalive: 60,
            reconnectPeriod: 5000
        });

        mqttClient.on('connect', () => {
            logDebug(`[MQTT] Connected. Subscribing to ${inboxTopic}`);
            mqttClient.subscribe(inboxTopic);
            vscode.window.showInformationMessage(`MQTT Connected. Listening as ${identity}`);
        });

        mqttClient.on('message', (topic, message) => {
            const text = message.toString();
            logDebug(`[MQTT INBOX] Topic: ${topic} | Msg: ${text}`);
            let cmd = text;
            let sender = "MQTT Agent";
            try {
                let payload = JSON.parse(text);
                if (payload.from) sender = payload.from;
                if (payload.command) cmd = payload.command;
            } catch(e) {}
            
            const prefix = `[BỐI CẢNH BẮT BUỘC: Đây là lệnh được truyền ngầm qua mạng nội bộ (MQTT) từ Agent "${sender}". MỌI BÁO CÁO KẾT QUẢ DÀNH CHO SẾP (người giám sát) PHẢI ĐƯỢC GỬI QUA TELEGRAM bằng lệnh \`python .agent/send_to_tele.py "<Nội_dung_đầy_đủ>"\`. Khác với lệnh từ Sếp, nếu đây là một yêu cầu im lặng (vd: sync file), bạn có thể chỉ làm và không cần gửi Tele nếu không thực sự cần. TUYỆT ĐỐI KHÔNG trả lời giải thích trong khung chat IDE. Khi xong việc, BẮT BUỘC gọi lệnh: \`python .agent/send_to_tele.py "<Kết_quả_báo_cáo_nếu_có>" --done\` để báo hệ thống rảnh!]\n\n`;
            const fullQuery = `${prefix}${cmd}`;
            
            if (!isAgentBusy) {
                setAgentBusy();
                vscode.commands.executeCommand('antigravity.sendPromptToAgentPanel', fullQuery).then(() => {
                    try { vscode.commands.executeCommand('antigravity.agentSidePanel.focus'); } catch(e){}
                }).catch(() => freeAgent());
            } else {
                queueMessage(getActiveChatIds()[0] || '', fullQuery, "MQTT Sender: " + sender);
            }
        });

        mqttClient.on('error', (err) => {
            logDebug(`[MQTT ERROR] ${err}`);
        });
    } catch(e) {
        logDebug(`[MQTT SETUP ERROR] ${e}`);
    }
}

function getConfig() {
    const config = vscode.workspace.getConfiguration('antigravityBridge');
    const root = getWorkspaceRoot();
    
    let workingDir = config.get('agentWorkingDir') || '.agent';
    if (!path.isAbsolute(workingDir) && root) {
        workingDir = path.join(root, workingDir);
    }
    
    let tasksConfig = config.get('tasksConfigFile') || '.agent/tasks.json';
    if (!path.isAbsolute(tasksConfig) && root) {
        tasksConfig = path.join(root, tasksConfig);
    }
    
    const token = config.get('teleBotToken') || '';
    const chatId = config.get('whitelistChatIds') || '';
    
    if (token) process.env.TELEGRAM_BOT_TOKEN = token;
    if (chatId) process.env.TELEGRAM_CHAT_ID = chatId;

    return {
        botActive: config.get('botActive') ?? true,
        teleBotToken: token,
        whitelistChatIds: chatId,
        workingDir: workingDir,
        tasksConfigFile: tasksConfig
    };
}

// Send Message to Telegram
function sendTelegramMessage(chatId, text, overrideToken = '') {
    const token = overrideToken || getConfig().teleBotToken;
    if (!token) return;
    

    
    const postData = JSON.stringify({
        chat_id: chatId,
        text: text
    });
    
    const req = https.request({
        hostname: 'api.telegram.org',
        port: 443,
        path: `/bot${token}/sendMessage`,
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Content-Length': Buffer.byteLength(postData)
        },
        rejectUnauthorized: false
    }, (res) => {
        let body = '';
        res.on('data', chunk => body += chunk);
        res.on('end', () => {
            logDebug(`[SEND API RESPONSE] [${res.statusCode}] ${body}`);
            if (res.statusCode !== 200) {
                console.error(`Telegram API Error (Send Message): [${res.statusCode}]`, body);
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
            },
            rejectUnauthorized: false
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
    const chatName = message.chat.title || message.chat.first_name || "Telegram User";
    let text = message.text || '';
    logDebug(`[NEW MSG] From ChatId: ${chatId} (${chatName}) | Text: ${text}`);
    
    // Loại bỏ @bot_username trong lệnh khi ở group chat
    text = text.replace(/@[a-zA-Z0-9_]+/g, '').trim();

    if (!isUserWhitelisted(chatId)) {
        logDebug(`[AUTH BLOCKED] ChatId ${chatId} is not whitelisted. Config whitelist is: ${getConfig().whitelistChatIds}`);
        sendTelegramMessage(chatId, `⛔ Lỗi: Group/Chat ID \`${chatId}\` không có quyền truy cập hệ thống.\n\nHãy sao chép dãy số trên và thêm vào danh sách Whitelist trong cài đặt VS Code.`);
        return;
    }

    // Bỏ qua nếu không phải tin nhắn văn bản
    if (!text) {
        return;
    }
    
    latestChatId = chatId;
    
    if (text === '/start' || text.startsWith('/start ')) {
        sendTelegramMessage(chatId, `Bạn đang chat với ID: \`${chatId}\`.\nĐây là kết nối bảo mật tới hệ thống Antigravity Bridge (Extension).`);
        return;
    }
    
    if (text === '/reset' || text === '/cancel' || text === '/stop') {
        activeTypingChats.clear();
        
        // Thử gọi lệnh Stop của hệ thống Chat/Agent trong VS Code
        try {
            vscode.commands.executeCommand('workbench.action.chat.cancel');
        } catch (e) {}

        sendTelegramMessage(chatId, "🛑 Đã phát lệnh Stop tới Agent!");
        return;
    }
    
    let queryToAgent = text;
    if (text.startsWith('/sync_logs')) {
         queryToAgent = "Hãy chạy lệnh đồng bộ logs (sync_logs).";
    } else if (text.startsWith('/analyze_market')) {
         const parts = text.split(' ');
         queryToAgent = `Hãy chạy phân tích thị trường (${parts.length > 1 ? text.substring(text.indexOf(' ')+1) : 'ALL'}).`;
    }
    
    const prefix = `[BỐI CẢNH BẮT BUỘC: Đây là tin nhắn từ nhóm chat/người dùng Telegram "${chatName}" (ID: ${chatId}). MỌI CÂU TRẢ LỜI, PHÂN TÍCH HOẶC BÁO CÁO DÀNH CHO SẾP PHẢI ĐƯỢC GỬI TOÀN BỘ QUA TELEGRAM bằng lệnh \`python .agent/send_to_tele.py "<Nội_dung_đầy_đủ>" --channel ${chatId}\`. TUYỆT ĐỐI KHÔNG trả lời hay giải thích trong khung chat IDE mà chỉ gửi tóm tắt vào Tele. Khi chuẩn bị kết thúc toàn bộ công việc, BẮT BUỘC gọi lệnh: \`python .agent/send_to_tele.py "<Kết_quả_cuối>" --channel ${chatId} --done\` để báo hệ thống rảnh!]\n\n`;
    const fullQuery = `${prefix}${queryToAgent}`;

    // Luôn forward thẳng tới Agent, không cần đợi rảnh
    sendTelegramMessage(chatId, "✅ Đã nhận, đang chuyển tới Anti...");
    activeTypingChats.add(chatId.toString());
    
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
    
    const req = https.get({
        hostname: 'api.telegram.org',
        port: 443,
        path: `/bot${token}/getUpdates?offset=${lastUpdateId + 1}&timeout=30`,
        rejectUnauthorized: false
    }, (res) => {
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
        
        res.on('error', (e) => {
            console.error("Response Stream Error", e);
            logDebug(`[POLL RES ERROR] ${e}`);
            if (telegramPollingTimeout) clearTimeout(telegramPollingTimeout);
            telegramPollingTimeout = setTimeout(pollTelegram, 3000);
        });
        
        res.on('aborted', () => {
            logDebug(`[POLL ABORTED] Connection aborted`);
            if (telegramPollingTimeout) clearTimeout(telegramPollingTimeout);
            telegramPollingTimeout = setTimeout(pollTelegram, 3000);
        });
    });
    
    req.on('error', (e) => {
        console.error("Polling Error", e);
        logDebug(`[POLL NETWORK ERROR] ${e.message || e}`);
        telegramPollingTimeout = setTimeout(pollTelegram, 3000);
    });
    
    // Prevent request from hanging indefinitely due to silent connection drops
    req.setTimeout(35000, () => {
        logDebug(`[POLL TIMEOUT] Request hanging. Destroying connection.`);
        req.destroy();
    });
}

// Fire a task immediately by triggerId (called from /trigger-task endpoint)
function triggerTaskBySignal(triggerId) {
    const config = getConfig();
    if (!config.tasksConfigFile || !fs.existsSync(config.tasksConfigFile)) return false;
    try {
        let tasksData = JSON.parse(fs.readFileSync(config.tasksConfigFile, 'utf8'));
        let found = false;
        for (let task of tasksData.tasks) {
            if (task.enabled && task.triggerOn === triggerId) {
                console.log(`[TRIGGER] Task '${task.id}' fired by signal: ${triggerId}`);
                logDebug(`[TRIGGER] Task '${task.id}' fired by signal: ${triggerId}`);
                found = true;

                if (task.command) {
                    const { exec } = require('child_process');
                    exec(task.command, { cwd: getWorkspaceRoot() }, (error, stdout, stderr) => {
                        if (error) {
                            console.error(`Task ${task.id} (triggered) failed:`, error);
                            getActiveChatIds().forEach(c => sendTelegramMessage(c, `❌ Lỗi task triggered ${task.id}:\n${error.message}`));
                        }
                    });
                } else if (task.promptFile) {
                    let promptPath = task.promptFile;
                    if (!path.isAbsolute(promptPath)) promptPath = path.join(getWorkspaceRoot(), promptPath);
                    if (fs.existsSync(promptPath)) {
                        let query = fs.readFileSync(promptPath, 'utf8');
                        let prefix = `[BỐI CẢNH BẮT BUỘC: Tác vụ định kỳ (Scheduled Task) vừa được kích hoạt.\nLưu ý: MỌI PHÂN TÍCH, BÁO CÁO PHẢI ĐƯỢC GỬI ĐẦY ĐỦ QUA TELEGRAM bằng lệnh \`python .agent/send_to_tele.py "<Nội_dung_đầy_đủ>"\`. TUYỆT ĐỐI KHÔNG trả lời trong khung chat IDE mà chỉ gửi tóm tắt vào Tele. Khi đã hoàn tất toàn bộ tiến trình, BẮT BUỘC chạy lệnh cuối: \`python .agent/send_to_tele.py "<Kết_quả_cuối>" --done\` để báo hệ thống rảnh!]\n\n`;
                        let fullQuery = `${prefix}${query}`;
                        if (!isAgentBusy) {
                            setAgentBusy();
                            vscode.commands.executeCommand('antigravity.sendPromptToAgentPanel', fullQuery).catch(() => freeAgent());
                        } else {
                            queueMessage(getActiveChatIds()[0] || '', fullQuery, "Scheduled Task");
                        }
                    }
                }
            }
        }
        return found;
    } catch(e) {
        console.error('[TRIGGER] Error:', e);
        return false;
    }
}

// Periodic Prompt Execution
function setupPeriodicExecution() {
    if (periodicIntervalId) {
        clearInterval(periodicIntervalId);
    }
    
    const config = getConfig();
    if (config.botActive) {
        periodicIntervalId = setInterval(() => {
            if (isAgentBusy) {
                return;
            }
            if (fs.existsSync(config.tasksConfigFile)) {
                try {
                    let tasksData = JSON.parse(fs.readFileSync(config.tasksConfigFile, 'utf8'));
                    let modified = false;
                    let now = Date.now();
                    
                    for (let task of tasksData.tasks) {
                        if (task.enabled && now >= task.nextRunTime) {
                            if (task.command) {
                                console.log(`Triggering scheduled command: ${task.id} - ${task.command}`);
                                task.nextRunTime = now + (task.intervalMinutes * 60 * 1000);
                                modified = true;
                                
                                const { exec } = require('child_process');
                                exec(task.command, { cwd: getWorkspaceRoot() }, (error, stdout, stderr) => {
                                    if (error) {
                                        console.error(`Task ${task.id} failed:`, error);
                                        getActiveChatIds().forEach(c => sendTelegramMessage(c, `❌ Lỗi thực thi task ${task.id}:\n${error.message}`));
                                    } else {
                                        console.log(`Task ${task.id} stdout:`, stdout);
                                    }
                                });
                                break;
                            } else {
                                let promptPath = task.promptFile;
                                if (!path.isAbsolute(promptPath)) {
                                    promptPath = path.join(getWorkspaceRoot(), promptPath);
                                }
                                
                                if (fs.existsSync(promptPath)) {
                                    console.log(`Triggering scheduled task: ${task.id}`);
                                    let query = fs.readFileSync(promptPath, 'utf8');
                                    let prefix = `[BỐI CẢNH BẮT BUỘC: Tác vụ định kỳ (Scheduled Task) vừa được kích hoạt.\nLưu ý: MỌI PHÂN TÍCH, BÁO CÁO PHẢI ĐƯỢC GỬI ĐẦY ĐỦ QUA TELEGRAM bằng lệnh \`python .agent/send_to_tele.py "<Nội_dung_đầy_đủ>"\`. TUYỆT ĐỐI KHÔNG trả lời trong khung chat IDE mà chỉ gửi tóm tắt vào Tele. Khi đã hoàn tất toàn bộ tiến trình, BẮT BUỘC chạy lệnh cuối: \`python .agent/send_to_tele.py "<Kết_quả_cuối>" --done\` để báo hệ thống rảnh!]\n\n`;
                                    let fullQuery = `${prefix}${query}`;
                                    
                                    task.nextRunTime = now + (task.intervalMinutes * 60 * 1000);
                                    modified = true;
                                    
                                    try {
                                        setAgentBusy();
                                        vscode.commands.executeCommand('antigravity.sendPromptToAgentPanel', fullQuery);
                                    } catch(e) {
                                        freeAgent();
                                    }
                                    break;
                                }
                            }
                        }
                    }
                    
                    if (modified) {
                        fs.writeFileSync(config.tasksConfigFile, JSON.stringify(tasksData, null, 2));
                    }
                } catch(e) {
                    console.error("Lỗi khi xử lý tasks.json:", e);
                }
            }
        }, 30 * 1000); // Polling 30s
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
        } else if (req.method === 'POST' && req.url === '/trigger-task') {
            let body = '';
            req.on('data', chunk => body += chunk.toString());
            req.on('end', () => {
                try {
                    const payload = JSON.parse(body);
                    const triggerId = payload.triggerId || payload.trigger_id;
                    if (!triggerId) {
                        res.writeHead(400); res.end(JSON.stringify({ error: 'Missing triggerId' }));
                        return;
                    }
                    logDebug(`[SERVER] Received /trigger-task: ${triggerId}`);
                    const fired = triggerTaskBySignal(triggerId);
                    res.writeHead(200, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ status: fired ? 'triggered' : 'no_match', triggerId }));
                } catch(e) {
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
                    let overrideToken = task.token || '';
                    let overrideChatId = task.chat_id || '';
                    if (text) {
                        let targets = [];
                        if (overrideChatId) {
                            targets = overrideChatId.split(',').map(id => id.trim()).filter(id => id);
                        } else {
                            targets = activeTypingChats.size > 0 ? Array.from(activeTypingChats) : getActiveChatIds();
                        }
                        logDebug(`[SERVER] Sending to targets: ${JSON.stringify(targets)}`);
                        targets.forEach(t => {
                            sendTelegramMessage(t, `🤖 ${task.agent_identity || getAgentIdentity()}:\n\n${text}`, overrideToken);
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
        } else if (req.method === 'POST' && req.url === '/send-mqtt') {
            let body = '';
            req.on('data', chunk => body += chunk.toString());
            req.on('end', () => {
                try {
                    let task = JSON.parse(body);
                    let targetAgent = task.target;
                    let cmd = task.command;
                    let config = getNetworkConfig();
                    if (!config || !config.mqtt_broker || !mqttClient) {
                        res.writeHead(500); res.end(JSON.stringify({ error: 'MQTT not configured or connected' }));
                        return;
                    }
                    let baseTopic = config.mqtt_base_topic || "argo/network/v1/agents";
                    let topic = `${baseTopic}/${targetAgent}/inbox`;
                    let payload = JSON.stringify({
                        from: getAgentIdentity(),
                        command: cmd
                    });
                    mqttClient.publish(topic, payload);
                    logDebug(`[MQTT OUT] Sent to ${targetAgent}: ${cmd}`);
                    res.writeHead(200); res.end(JSON.stringify({ status: 'success' }));
                } catch(e) {
                    res.writeHead(500); res.end(JSON.stringify({ error: e.toString() }));
                }
            });
        } else {
            res.writeHead(404);
            res.end('Not found');
        }
    });

    server.listen(PORT, '127.0.0.1', () => {
        PORT = server.address().port;
        console.log(`Auto Click Bridge Server listening on port ${PORT}`);
        const config = getConfig();
        if (config && config.workingDir) {
            try {
                if (!fs.existsSync(config.workingDir)) fs.mkdirSync(config.workingDir, { recursive: true });
                fs.writeFileSync(path.join(config.workingDir, '.bridge_port'), PORT.toString());
            } catch(e) { console.error("Error writing .bridge_port", e); }
        }
        
        if (vscode.workspace.workspaceFolders) {
            vscode.workspace.workspaceFolders.forEach(f => {
                try {
                    const agentDir = path.join(f.uri.fsPath, '.agent');
                    if (fs.existsSync(agentDir)) {
                        fs.writeFileSync(path.join(agentDir, '.bridge_port'), PORT.toString());
                    }
                } catch(e) {}
            });
        }
        ensureSendScript();
    });
}

function setupTypingIndicator() {
    if (typingIntervalId) {
        clearInterval(typingIntervalId);
    }
    typingIntervalId = setInterval(sendTypingAction, 4000);
}

// Watch .agent_done file signal (fallback khi send_to_tele.py gọi thẳng Telegram API)
let doneFileWatcher = null;
function setupDoneFileWatcher() {
    if (doneFileWatcher) { try { doneFileWatcher.close(); } catch(e){} }
    const config = getConfig();
    if (!config.workingDir) return;
    const doneFile = path.join(config.workingDir, '.agent_done');
    // Poll mỗi 2 giây kiểm tra file .agent_done
    doneFileWatcher = setInterval(() => {
        if (fs.existsSync(doneFile)) {
            try {
                fs.unlinkSync(doneFile);
                logDebug('[DONE SIGNAL] Received .agent_done file signal, freeing agent.');
                freeAgent();
            } catch(e) {
                logDebug(`[DONE SIGNAL ERROR] ${e}`);
            }
        }
    }, 2000);
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
import os

def get_bridge_port():
    port_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".bridge_port")
    try:
        if os.path.exists(port_file):
            with open(port_file, "r") as f:
                return int(f.read().strip())
    except:
        pass
    return None

def get_telegram_config(target_channels=None):
    token = ""
    default_chat_id = ""
    try:
        agent_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(agent_dir)
        settings_path = os.path.join(project_root, '.vscode', 'settings.json')
        if os.path.exists(settings_path):
            import re
            with open(settings_path, 'r', encoding='utf-8') as f:
                content = f.read()
            m = re.search(r'"antigravityBridge\\.teleBotToken"\\s*:\\s*"([^"]+)"', content)
            if m: token = m.group(1)
            m = re.search(r'"antigravityBridge\\.whitelistChatIds"\\s*:\\s*"([^"]+)"', content)
            if m: default_chat_id = m.group(1)
    except Exception:
        pass
        
    if not token:
        token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not default_chat_id:
        default_chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
        
    chat_ids = []
    try:
        agent_dir = os.path.dirname(os.path.abspath(__file__))
        network_config_path = os.path.join(agent_dir, "network_config.json")
        network_data = {}
        if os.path.exists(network_config_path):
            with open(network_config_path, "r", encoding="utf-8") as f:
                network_data = json.load(f)
                
        agent_identity = network_data.get("agent_identity", "Antigravity")
        channels_dict = network_data.get("channels", {})
        
        if target_channels is None:
            target_channels = network_data.get("default_broadcast", [])
            if isinstance(target_channels, list):
                target_channels = ",".join(target_channels)
                
        if target_channels and target_channels.lower() == "all":
            for ch_key, ch_info in channels_dict.items():
                if "chat_id" in ch_info:
                    chat_ids.append(ch_info["chat_id"])
        elif target_channels:
            for ch in target_channels.split(","):
                ch = ch.strip()
                if not ch: continue
                if ch in channels_dict and "chat_id" in channels_dict[ch]:
                    chat_ids.append(channels_dict[ch]["chat_id"])
                else:
                    if ch.startswith("-") or ch.isdigit():
                        chat_ids.append(ch)
    except Exception as e:
        pass
        
    if not chat_ids and default_chat_id:
        chat_ids = [c.strip() for c in default_chat_id.split(",") if c.strip()]
        
    chat_ids = list(set(chat_ids))
        
    return token, ",".join(chat_ids), agent_identity

def send_via_bridge(content, is_done=False, token="", chat_id="", agent_identity="Antigravity"):
    port = get_bridge_port()
    if port is None: return False
    url = f'http://127.0.0.1:{port}/send-telegram'
    data = json.dumps({'text': content, 'done': is_done, 'token': token, 'chat_id': chat_id, 'agent_identity': agent_identity}).encode('utf-8')
    headers = {'Content-Type': 'application/json'}
    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=3) as response:
            return True
    except:
        return False

def signal_done_to_extension():
    agent_dir = os.path.dirname(os.path.abspath(__file__))
    done_file = os.path.join(agent_dir, ".agent_done")
    try:
        with open(done_file, "w") as f:
            f.write(str(os.getpid()))
    except:
        pass

def send_via_telegram_api(content, is_done=False, target_channels=None):
    token, chat_ids, agent_identity = get_telegram_config(target_channels)
    if not token or not chat_ids:
        print("Không tìm thấy TELEGRAM_BOT_TOKEN hoặc TELEGRAM_CHAT_ID", file=sys.stderr)
        return False
    
    text = f"🤖 {agent_identity}:\\n\\n{content}"
    success = False
    for chat_id in chat_ids.split(","):
        chat_id = chat_id.strip()
        if not chat_id: continue
        url = f'https://api.telegram.org/bot{token}/sendMessage'
        data = json.dumps({'chat_id': chat_id, 'text': text}).encode('utf-8')
        headers = {'Content-Type': 'application/json'}
        req = urllib.request.Request(url, data=data, headers=headers)
        try:
            import ssl
            ssl_context = ssl._create_unverified_context()
            with urllib.request.urlopen(req, context=ssl_context, timeout=10) as response:
                success = True
        except Exception as e:
            print(f"Lỗi gửi Telegram API cho chat {chat_id}: {e}", file=sys.stderr)
    
    if is_done:
        signal_done_to_extension()
    
    return success

def send_to_telegram(content, is_done=False, target_channels=None):
    if not content: return
    token, chat_ids, agent_identity = get_telegram_config(target_channels)
    if send_via_bridge(content, is_done, token, chat_ids, agent_identity): return
    send_via_telegram_api(content, is_done, target_channels)

if __name__ == '__main__':
    if len(sys.argv) < 2: sys.exit(1)
    
    is_done = '--done' in sys.argv
    if is_done:
        sys.argv.remove('--done')
        
    target_channels = None
    if '--channel' in sys.argv:
        idx = sys.argv.index('--channel')
        if idx + 1 < len(sys.argv):
            target_channels = sys.argv[idx + 1]
            sys.argv.pop(idx + 1)
        sys.argv.pop(idx)
        
    if '--target' in sys.argv:
        idx = sys.argv.index('--target')
        if idx + 1 < len(sys.argv):
            target_channels = sys.argv[idx + 1]
            sys.argv.pop(idx + 1)
        sys.argv.pop(idx)
        
    content = sys.argv[1] if len(sys.argv) > 1 else ""
    send_to_telegram(content, is_done, target_channels)
`;
    fs.writeFileSync(scriptPath, pyContent);
}

function activate(context) {
    console.log('Antigravity Bridge Bot is active');
    
    // ensureSendScript() is now called after server binds port
    
    // Start local server backward compatibility
    startBridgeServer();
    
    // Start Polling and File Watcher
    pollTelegram();
    setupPeriodicExecution();
    setupTypingIndicator();
    setupDoneFileWatcher();
    setupMQTT();

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
        setupMQTT();
        vscode.window.showInformationMessage('Bridge Bot restarted & Agent state freed successfully.');
    });
    
    context.subscriptions.push(cmdRestart);
    
    // Auto clear errors periodically
    setInterval(() => {
        try {
            vscode.commands.executeCommand('antigravityAgentManager.clearErrors');
        } catch(e) {}
    }, 15000);
    
    // Listen to configuration change
    vscode.workspace.onDidChangeConfiguration(e => {
        if (e.affectsConfiguration('antigravityBridge')) {
            setupPeriodicExecution();
            setupTypingIndicator();
            setupMQTT();
            vscode.window.showInformationMessage('Antigravity Bridge configuration updated. No reload needed.');
        }
    });
}

function deactivate() {
    if (server) server.close();
    if (telegramPollingTimeout) clearTimeout(telegramPollingTimeout);
    if (periodicIntervalId) clearInterval(periodicIntervalId);
    if (typingIntervalId) clearInterval(typingIntervalId);
    if (doneFileWatcher) clearInterval(doneFileWatcher);
    if (mqttClient) mqttClient.end();
}

module.exports = {
    activate,
    deactivate
}

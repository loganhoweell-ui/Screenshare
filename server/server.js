const WebSocket = require('ws');
const http = require('http');
const fs = require('fs');
const path = require('path');

const SECRET = process.env.SECRET || 'changeme';
const PORT = process.env.PORT || 3000;

let latestFrame = null;
let broadcasterWs = null;
const viewers = new Set();

const server = http.createServer((req, res) => {
    const url = new URL(req.url, `http://${req.headers.host}`);
    if (url.pathname === '/') {
        res.writeHead(200, { 'Content-Type': 'text/html' });
        res.end(fs.readFileSync(path.join(__dirname, 'index.html')));
    } else {
        res.writeHead(404); res.end();
    }
});

const wss = new WebSocket.Server({ server, maxPayload: 10 * 1024 * 1024 });

wss.on('connection', (ws, req) => {
    const url = new URL(req.url, 'http://localhost');
    const role = url.searchParams.get('role') || 'viewer';
    const secret = url.searchParams.get('secret');

    if (secret !== SECRET) {
        ws.close(1008, 'Invalid secret');
        return;
    }

    if (role === 'broadcaster') {
        broadcasterWs = ws;
        console.log('[broadcaster] Connected');

        ws.on('message', (data, isBinary) => {
            if (!isBinary) return;
            latestFrame = data;
            for (const viewer of viewers) {
                if (viewer.readyState === WebSocket.OPEN) {
                    viewer.send(data, { binary: true });
                }
            }
        });

        ws.on('close', () => {
            broadcasterWs = null;
            latestFrame = null;
            console.log('[broadcaster] Disconnected');
            const msg = Buffer.from(JSON.stringify({ type: 'offline' }));
            for (const v of viewers) {
                if (v.readyState === WebSocket.OPEN) v.send(msg);
            }
        });

    } else {
        viewers.add(ws);
        console.log(`[viewer] +1  (${viewers.size} watching)`);

        if (latestFrame) ws.send(latestFrame, { binary: true });

        // Forward viewer input events to the broadcaster
        ws.on('message', (data) => {
            if (broadcasterWs && broadcasterWs.readyState === WebSocket.OPEN) {
                broadcasterWs.send(data.toString());
            }
        });

        ws.on('close', () => {
            viewers.delete(ws);
            console.log(`[viewer] -1  (${viewers.size} watching)`);
        });
    }
});

server.listen(PORT, () => {
    console.log(`\nScreenshare server  →  http://localhost:${PORT}/?secret=${SECRET}\n`);
});

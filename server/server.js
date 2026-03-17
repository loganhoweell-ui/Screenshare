const WebSocket = require('ws');
const http = require('http');
const fs = require('fs');
const path = require('path');

const SECRET = process.env.SECRET || 'changeme';
const PORT = process.env.PORT || 3000;

let latestFrame = null;   // raw binary Buffer
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

const wss = new WebSocket.Server({ server, maxPayload: 10 * 1024 * 1024 }); // 10MB max frame

wss.on('connection', (ws, req) => {
    const url = new URL(req.url, 'http://localhost');
    const role = url.searchParams.get('role') || 'viewer';
    const secret = url.searchParams.get('secret');

    if (secret !== SECRET) {
        ws.close(1008, 'Invalid secret');
        return;
    }

    if (role === 'broadcaster') {
        console.log('[broadcaster] Connected');

        ws.on('message', (data, isBinary) => {
            if (!isBinary) return;
            latestFrame = data;

            // Blast to all viewers
            for (const viewer of viewers) {
                if (viewer.readyState === WebSocket.OPEN) {
                    viewer.send(data, { binary: true });
                }
            }
        });

        ws.on('close', () => {
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

        // Send the most recent frame immediately so viewer doesn't wait
        if (latestFrame) ws.send(latestFrame, { binary: true });

        ws.on('close', () => {
            viewers.delete(ws);
            console.log(`[viewer] -1  (${viewers.size} watching)`);
        });
    }
});

server.listen(PORT, () => {
    console.log(`\nScreenshare server  →  http://localhost:${PORT}/?secret=${SECRET}\n`);
});

import WebSocket from 'ws';
const ws = new WebSocket('ws://localhost:3000/live?activity=Explain%20It&topic=Buoyancy&subject=Physics');

ws.on('open', () => {
  console.log('[Client] Connected to server.ts proxy');
  setTimeout(() => {
    ws.send(JSON.stringify({ text: "Hello! Can you hear me?" }));
    console.log('[Client] Sent dummy text chunk to trigger response');
  }, 3000);
});

ws.on('message', (data) => {
  const parsed = JSON.parse(data.toString());
  if (parsed.audio) {
    console.log('[Client] Received AUDIO chunk of length:', parsed.audio.length);
  }
  if (parsed.modelTranscript) {
    console.log('[Client] Received MODEL TRANSCRIPT:', parsed.modelTranscript);
  }
});

ws.on('error', (err) => console.error('[Client] WS Error:', err));
ws.on('close', () => console.log('[Client] Disconnected'));

setTimeout(() => { ws.close(); }, 15000);

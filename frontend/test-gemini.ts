import { GoogleGenAI } from "@google/genai";
import * as dotenv from "dotenv";
dotenv.config();

const ai = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY });
async function run() {
  try {
    const session = await ai.live.connect({
      model: "gemini-3.1-flash-live-preview",
      callbacks: {
        onmessage: (msg) => console.log("Received msg:", JSON.stringify(msg).substring(0, 100))
      }
    });
    console.log("Connected successfully!");
    
    try {
      session.sendRealtimeInput({ text: "Hello!" });
      console.log("Sent via sendRealtimeInput");
    } catch(e) {
      console.error("sendRealtimeInput error:", e);
    }

    try {
      session.sendClientContent({ turns: [{ role: "user", parts: [{ text: "Hello again!" }] }] });
      console.log("Sent via sendClientContent()");
    } catch(e) {
      console.error("sendClientContent() error:", e);
    }
    
    setTimeout(() => session.close(), 5000);
  } catch(e) {
    console.error("Connection Error:", e);
  }
}
run();

import { GoogleGenAI } from "@google/genai";
import * as dotenv from "dotenv";
dotenv.config();

const ai = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY });
async function run() {
  try {
    const session = await ai.live.connect({
      model: "gemini-2.0-flash-exp",
      callbacks: {
        onmessage: (msg) => console.log("Received msg from 2.0:", JSON.stringify(msg).substring(0, 100))
      }
    });
    console.log("Connected successfully to 2.0!");
    session.sendRealtimeInput({ text: "Hello!" });
    console.log("Sent Hello");
    setTimeout(() => session.close(), 5000);
  } catch(e) {
    console.error("Connection Error:", e);
  }
}
run();

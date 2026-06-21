import { GoogleGenAI, Modality } from "@google/genai";
import * as dotenv from "dotenv";
dotenv.config();

const apiKey = process.env.GEMINI_API_KEY;
if (!apiKey) {
  console.error("No API key configured");
  process.exit(1);
}

const ai = new GoogleGenAI({ apiKey });

async function run() {
  try {
    console.log("Calling generateContent with gemini-3.1-flash-tts-preview...");
    const response = await ai.models.generateContent({
      model: "gemini-3.1-flash-tts-preview",
      contents: [{ parts: [{ text: "Hello from Mootion tutor!" }] }],
      config: {
        responseModalities: [Modality.AUDIO],
        speechConfig: {
          voiceConfig: {
            prebuiltVoiceConfig: { voiceName: 'Kore' },
          },
        },
      },
    });

    console.log("Response received.");
    console.log("Candidates length:", response.candidates?.length);
    const candidate = response.candidates?.[0];
    console.log("Candidate content parts:", candidate?.content?.parts?.length);
    const part = candidate?.content?.parts?.[0];
    console.log("Part keys:", part ? Object.keys(part) : "no part");
    if (part?.inlineData) {
      console.log("Found inlineData! mimeType:", part.inlineData.mimeType, "data length:", part.inlineData.data?.length);
    } else {
      console.log("No inlineData found in candidate part.");
    }
  } catch (error) {
    console.error("TTS run error:", error);
  }
}
run();

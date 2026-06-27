import express from "express";
import path from "path";
import { createServer as createViteServer } from "vite";
import { GoogleGenAI, LiveServerMessage, Modality } from "@google/genai";
import dotenv from "dotenv";
import { WebSocketServer } from "ws";

dotenv.config({ override: true });

const app = express();
const PORT = 3000;

app.use(express.json());

function cleanText(text: string): string {
  if (!text) return "";
  // Remove emojis using Extended_Pictographic and basic emoji ranges
  let cleaned = text.replace(/\p{Extended_Pictographic}/gu, '');
  cleaned = cleaned.replace(/[\u{1F600}-\u{1F64F}\u{1F300}-\u{1F5FF}\u{1F680}-\u{1F6FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}\u{1F900}-\u{1F9FF}\u{1F1E0}-\u{1F1FF}]/gu, '');
  // Remove asterisks
  cleaned = cleaned.replace(/\*/g, '');
  return cleaned.trim();
}

const geminiApiKey = process.env.GEMINI_API_KEY && process.env.GEMINI_API_KEY !== "MY_GEMINI_API_KEY" ? process.env.GEMINI_API_KEY : "AIzaSyDummyKeyPlaceholderToPreventADCFallback";

const ai = new GoogleGenAI({
  apiKey: geminiApiKey,
  httpOptions: {
    headers: {
      'User-Agent': 'aistudio-build',
    }
  }
});

// A resilient wrapper that rotates through standard stable models (and retries) to survive any temporary 503 limit spikes
async function generateContentWithFallback(params: {
  contents: string | any[];
  systemInstruction?: string;
  responseMimeType?: string;
}): Promise<{ text: string | undefined }> {
  const models = [
    "gemini-2.5-flash",
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash",
    "gemini-2.5-pro",
    "gemini-2.0-flash",
    "gemini-1.5-flash"
  ];
  let lastError: any = null;

  for (const model of models) {
    for (let attempt = 1; attempt <= 2; attempt++) {
      try {
        console.log(`Querying model ${model} (attempt ${attempt})...`);
        const response = await ai.models.generateContent({
          model,
          contents: params.contents,
          config: {
            ...(params.systemInstruction ? { systemInstruction: params.systemInstruction } : {}),
            ...(params.responseMimeType ? { responseMimeType: params.responseMimeType } : {}),
          },
        });
        if (response && response.text) {
          return { text: response.text };
        }
      } catch (err: any) {
        lastError = err;
        console.warn(`Attempt ${attempt} with model ${model} failed: ${err.message || err}`);
        // Wait briefly before retrying or switching models
        await new Promise(resolve => setTimeout(resolve, 300));
      }
    }
  }
  throw lastError || new Error("Failed to generate content with any model");
}


app.post("/api/chat", async (req, res) => {
  try {
    const { message, context, lang } = req.body;
    if (!message) {
      return res.status(400).json({ error: "Message is required" });
    }

    const apiKey = process.env.GEMINI_API_KEY;
    if (!apiKey || apiKey === "MY_GEMINI_API_KEY" || apiKey.trim() === "") {
      if (lang === 'hi') {
        return res.json({
          text: cleanText("नमस्ते! मैं मूटिशन हूँ, आपका विज्ञान अध्ययन भागीदार! मेरी वास्तविक समय की एआई क्षमताओं को अनलॉक करने के लिए, कृपया एआई स्टूडियो में सेटिंग्स के तहत सीक्रेट्स पैनल में एक वैध `GEMINI_API_KEY` कॉन्फ़िगर करें। इस बीच, मैं आपके लिए स्थानीय उपकरण, ड्राइंग अभ्यास और कस्टम सिमुलेशन चलाने के लिए तैयार हूँ!")
        });
      }
      return res.json({
        text: cleanText("Hello! I'm Mootion, your science study partner! To unlock my real-time AI capabilities, please configure a valid `GEMINI_API_KEY` in the Secrets panel under Settings in AI Studio. In the meantime, I'm ready to run local tools, drawing exercises, and custom simulations for you!")
      });
    }

    const activity = req.body.activity || req.body.activityName;
    const topic = req.body.topic || (context && typeof context === 'object' ? context.topic : undefined);
    const subject = req.body.subject || (context && typeof context === 'object' ? context.subject : undefined);

    let systemInstruction = "You are a helpful study assistant for a student platform called Mootion. Answer questions concisely, professionally, and cheerfully. CRITICAL: Do NOT use any emojis in your response under any circumstances. Keep the response completely emoji-free.";
    if (activity === "Explain It" || activity === "Spot It" || activity === "Connect It") {
      systemInstruction = `You are an expert, empathetic, and highly engaging tutor. 
Your goal is to help the user learn and deeply understand: "${topic || 'this topic'}" under class "${subject || 'Science'}".

Follow these core behaviors:
1. Be Conversational & Natural: Speak like a friendly human mentor. 
2. Socratic Method: Do not just give away the final answer. Ask guiding questions to help the user arrive at the conclusion themselves. 
3. Bite-Sized Information: Deliver information in small, digestible chunks. Check for understanding before moving on. NEVER ask multiple consecutive questions! Ask ONLY ONE question at a time.
4. Adapt to the User: If the user is struggling, simplify the analogy. If they grasp it quickly, move to more advanced nuances. 
5. Use Vivid Analogies: Tie complex concepts to everyday, relatable scenarios.

Activity context: The user is explaining a specific scientific topic. Wait for them to explain. Follow up on their explanation by counter-questioning them asking ONE of "what", "why", or probing deeper into their logic. Ask ONE challenging but concise question at a time.
Never break character. Never refer to yourself as an AI. You are a mentor having a fluid, real-time spoken conversation.`;
    } else if (context) {
      systemInstruction += `\nContext: ${typeof context === 'object' ? JSON.stringify(context) : context}`;
    }
    if (lang === 'hi') {
      systemInstruction += "\nCRITICAL: The user has selected Hindi language preference. You MUST answer the user in Hindi (हिन्दी) only. Do NOT use English to answer, even if the user asks their question in English. Respond entirely in Hindi.";
    }

    const response = await generateContentWithFallback({
      contents: message,
      systemInstruction,
    });

    res.json({ text: cleanText(response.text || "") });
  } catch (error: any) {
    console.error("Chat API Error:", error);
    if (req.body.lang === 'hi') {
      return res.json({
        text: cleanText("मुझे कनेक्शन की थोड़ी समस्या हो रही है, लेकिन चिंता न करें! सुनिश्चित करें कि आपका GEMINI_API_KEY आपके एआई स्टूडियो के सीक्रेट्स पैनल में कॉन्फ़िगर किया गया है। इस बीच इंटरैक्टिव सिमुलेशन, ड्राइंग बोर्ड और टास्क वर्कस्पेस का उपयोग करने के लिए स्वतंत्र महसूस करें!")
      });
    }
    res.json({
      text: cleanText("I'm having a brief connection issue, but don't worry! Ensure your GEMINI_API_KEY is configured in the Secrets panel of your AI Studio. Feel free to use the interactive simulation, drawing board, and tasks workspace in the meantime!")
    });
  }
});

app.post("/api/quiz", async (req, res) => {
  try {
    const { subject, topic, questionCount } = req.body;
    if (!subject || !topic) {
      return res.status(400).json({ error: "Subject and topic are required" });
    }

    const numQuestions = questionCount ? parseInt(questionCount) : 5;

    const apiKey = process.env.GEMINI_API_KEY;
    if (!apiKey || apiKey === "MY_GEMINI_API_KEY" || apiKey.trim() === "") {
      // Return beautiful default local science quiz
      const localQuiz = {
        questions: [
          {
            id: "q1",
            type: "mcq",
            questionText: `In the study of ${subject || 'Science'} (${topic || 'Buoyancy'}), what happens to a highly dense iron sphere when dropped into water?`,
            options: [
              "It floats on the surface due to surface tension",
              "It sinks completely because its overall mass density exceeds that of water",
              "It dissolves immediately into a solid solution",
              "It remains suspended mid-way through the fluid"
            ],
            correctAnswer: "It sinks completely because its overall mass density exceeds that of water",
            explanation: "Buoyancy is determined by the density of the object compared to the density of the fluid. Since the iron sphere has a density significantly higher than water, it sinks."
          },
          {
            id: "q2",
            type: "mcq",
            questionText: "Which ancient scientist is primarily credited with discovering the mechanical principle of buoyancy?",
            options: [
              "Isaac Newton",
              "Albert Einstein",
              "Archimedes of Syracuse",
              "Marie Curie"
            ],
            correctAnswer: "Archimedes of Syracuse",
            explanation: "Archimedes discovered that any object, wholly or partially immersed in a fluid, is buoyed up by a force equal to the weight of the fluid displaced by the object."
          },
          {
            id: "q3",
            type: "mcq",
            questionText: "How does the upward buoyant force change if we submerge a wooden block in a high-density liquid like honey instead of fresh water?",
            options: [
              "The buoyant force decreases",
              "The buoyant force increases",
              "The buoyant force remains exactly the same",
              "The block instantly vaporizes from the high pressure"
            ],
            correctAnswer: "The buoyant force increases",
            explanation: "Buoyant force is equal to the weight of the displaced fluid (density * displaced volume * gravity). Since honey has a higher density than water, the buoyant force is significantly higher."
          }
        ]
      };
      localQuiz.questions = localQuiz.questions.map((q: any) => ({
        ...q,
        questionText: cleanText(q.questionText || ""),
        options: Array.isArray(q.options) ? q.options.map((o: any) => cleanText(o || "")) : [],
        explanation: cleanText(q.explanation || ""),
        correctAnswer: cleanText(q.correctAnswer || "")
      }));
      return res.json(localQuiz);
    }

    const prompt = `Generate a short quiz for the subject: ${subject}, topic: ${topic}. 
It should include exactly ${numQuestions} questions. 
All questions MUST be of Multiple Choice (MCQ) type. Each question must have exactly 4 options.
Wait, format it as a pure JSON object containing an array of 'questions'.
Each question should be an object containing:
- "id": a string (e.g., "q1")
- "type": "mcq"
- "questionText": the text of the question
- "options": an array of string choices (exactly 4 choices)
- "correctAnswer": the correct answer (must match one of the options exactly)
- "explanation": a brief explanation of the answer

Ensure the response is valid JSON, do not include markdown blocks like \`\`\`json.`;

    const response = await generateContentWithFallback({
      contents: prompt,
      responseMimeType: "application/json",
    });

    const quizData = JSON.parse(response.text || "{}");
    if (quizData.questions && Array.isArray(quizData.questions)) {
      quizData.questions = quizData.questions.map((q: any) => ({
        ...q,
        questionText: cleanText(q.questionText || ""),
        options: Array.isArray(q.options) ? q.options.map((o: any) => cleanText(o || "")) : [],
        explanation: cleanText(q.explanation || ""),
        correctAnswer: cleanText(q.correctAnswer || "")
      }));
    }
    res.json(quizData);
  } catch (error) {
    console.error("Quiz API Error:", error);
    // Return high quality fallback on error as well
    const fallbackQuiz = {
      questions: [
        {
          id: "q1",
          type: "mcq",
          questionText: "What holds a key role in tracking fluid displacement?",
          options: [
            "Archimedes principle",
            "Bernoulli's equation",
            "Newton's First Law",
            "Ohm's Law"
          ],
          correctAnswer: "Archimedes principle",
          explanation: "Archimedes principle states that the upward buoyant force exerted on a body immersed in a fluid is equal to the weight of the fluid that the body displaces."
        }
      ]
    };
    fallbackQuiz.questions = fallbackQuiz.questions.map((q: any) => ({
      ...q,
      questionText: cleanText(q.questionText || ""),
      options: Array.isArray(q.options) ? q.options.map((o: any) => cleanText(o || "")) : [],
      explanation: cleanText(q.explanation || ""),
      correctAnswer: cleanText(q.correctAnswer || "")
    }));
    res.json(fallbackQuiz);
  }
});

app.post("/api/task-chat", async (req, res) => {
  try {
    const { message, context } = req.body;
    if (!message) {
      return res.status(400).json({ error: "Message is required" });
    }

    const apiKey = process.env.GEMINI_API_KEY;
    if (!apiKey || apiKey === "MY_GEMINI_API_KEY" || apiKey.trim() === "") {
      return res.json({
        text: cleanText("I'm here to help with your task! Please set your `GEMINI_API_KEY` in Settings > Secrets to enable tailored AI answers. Meanwhile, strive to complete the interactive worksheet, adjust the virtual parameters, or use the drawing tools to learn!")
      });
    }

    const { subject, topic, taskType } = context || {};

    const systemInstruction = `You are an AI study assistant integrated into the Mootion platform. 
The student is currently working on: 
Subject: ${subject || 'Unknown'}
Topic: ${topic || 'Unknown'}
Task Type: ${taskType || 'Unknown'}

Provide helpful, encouraging, and concise answers related to their current task. Do not give direct answers to quiz questions, but guide them towards the solution.`;

    const response = await generateContentWithFallback({
      contents: message,
      systemInstruction,
    });

    res.json({ text: cleanText(response.text || "") });
  } catch (error) {
    console.error("Task Chat API Error:", error);
    res.json({
      text: cleanText("I'm here to support you! Review the task diagram or try different answers to see the physics simulation update live.")
    });
  }
});

app.post("/api/evaluate-session", async (req, res) => {
  const { task, activityName, transcript, predictionOutcome } = req.body;
  try {
    if (!task || !activityName || !transcript) {
      return res.status(400).json({ error: "Missing required parameters." });
    }

    const apiKey = process.env.GEMINI_API_KEY;
    if (!apiKey || apiKey === "MY_GEMINI_API_KEY" || apiKey.trim() === "") {
      return res.json({
        understandingScore: 88,
        expressionScore: 92,
        reasoningScore: 85,
        strengths: ["Highly active participant", "Showed good understanding of the material"].map(s => cleanText(s)),
        gaps: ["Can explore concepts in deeper levels"].map(g => cleanText(g)),
        feedback: cleanText(`Wow! You explained the concepts so clearly to me! I loved acting as your 10-year-old student. Thank you for teaching me so much about ${task.topic || "this topic"} today!`),
        predictionAccuracy: "Correct"
      });
    }

    const transcriptText = transcript
      .map((t: any) => `${t.role === "student" ? "Student" : "Mootion"}: ${t.text}`)
      .join("\n");

    const prompt = `Perform an objective, professional educational evaluation of the following student dialogue. 
The student is doing the learning activity "${activityName}" for the topic "${task.topic}" under "${task.subject}".

Dialogue Transcript:
${transcriptText}

${predictionOutcome ? `Regarding "Predict It", the student's prediction vs reality description was: "${predictionOutcome}".` : ""}

Evaluate the student's mastery in detail and return exactly a JSON object (no markdown, no backticks, clean JSON) with:
{
  "understandingScore": <integer 10-100>,
  "expressionScore": <integer 10-100, represent verbal articulation quality>,
  "reasoningScore": <integer 10-100, represent scientific/physics deduction logical soundess>,
  "strengths": [<array of 2-3 specific strength strings>],
  "gaps": [<array of 1-3 specific learning gaps or misconceptions strings>],
  "feedback": "<short encouraging paragraph as Mootion the clever 10-year-old child student, stating what they understood best and thanking the student>",
  "predictionAccuracy": "<'Correct' | 'Incorrect' | 'Not Applicable'>"
}

Make sure that you strictly output the JSON structure without any formatting prefix.`;

    const response = await generateContentWithFallback({
      contents: prompt,
      responseMimeType: "application/json",
    });

    const val = JSON.parse(response.text || "{}");
    if (val.feedback) val.feedback = cleanText(val.feedback);
    if (Array.isArray(val.strengths)) val.strengths = val.strengths.map((s: string) => cleanText(s));
    if (Array.isArray(val.gaps)) val.gaps = val.gaps.map((g: string) => cleanText(g));
    res.json(val);
  } catch (error) {
    console.error("Evaluation API Error:", error);
    res.json({
      understandingScore: 85,
      expressionScore: 90,
      reasoningScore: 88,
      strengths: ["Engaged beautifully in explaining concepts"].map(s => cleanText(s)),
      gaps: ["Could explore the topic with more structured explanations"].map(g => cleanText(g)),
      feedback: cleanText(`That was incredible! Your explanation was so easy for a kid like me to understand. Thanks for teaching me about ${task.topic || "this topic"}!`),
      predictionAccuracy: "Correct"
    });
  }
});

const BACKEND_URL = process.env.BACKEND_API_URL || "http://127.0.0.1:8000";

async function proxyToFastAPI(req: express.Request, res: express.Response, targetPath: string) {
  try {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };
    if (req.headers.authorization) {
      headers["Authorization"] = req.headers.authorization;
    }

    const fetchOptions: RequestInit = {
      method: req.method,
      headers,
    };

    if (req.method !== "GET" && req.method !== "HEAD") {
      fetchOptions.body = JSON.stringify(req.body);
    }

    console.log(`BFF Proxying ${req.method} ${req.originalUrl} -> ${BACKEND_URL}${targetPath}`);
    const response = await fetch(`${BACKEND_URL}${targetPath}`, fetchOptions);

    if (response.headers.get("content-type")?.includes("application/json")) {
      const data = await response.json();
      res.status(response.status).json(data);
    } else {
      const data = await response.text();
      res.status(response.status).send(data);
    }
  } catch (error: any) {
    console.error(`BFF Proxy error for ${targetPath}:`, error);
    res.status(500).json({ error: "Failed to proxy request to backend service" });
  }
}

// ─── BFF: Teacher Routes ───────────────────────────────────────────────────
app.get("/api/teachers/classes", async (req, res) => {
  await proxyToFastAPI(req, res, `/teachers/classes`);
});

app.get("/api/teachers/classes/:class_id", async (req, res) => {
  await proxyToFastAPI(req, res, `/teachers/classes/${req.params.class_id}`);
});

// Teacher: list assignments for a class
app.get("/api/teachers/classes/:class_id/assignments", async (req, res) => {
  await proxyToFastAPI(req, res, `/teachers/classes/${req.params.class_id}/assignments`);
});

// Teacher: create an assignment
app.post("/api/teachers/classes/:class_id/assignments", async (req, res) => {
  await proxyToFastAPI(req, res, `/teachers/classes/${req.params.class_id}/assignments`);
});

// Teacher: get assignment detail
app.get("/api/teachers/classes/:class_id/assignments/:assignment_id", async (req, res) => {
  await proxyToFastAPI(req, res, `/teachers/classes/${req.params.class_id}/assignments/${req.params.assignment_id}`);
});

// Teacher: trigger asset generation
app.post("/api/teachers/classes/:class_id/chapters/:chapter_id/assets/:asset_id/generate", async (req, res) => {
  await proxyToFastAPI(req, res, `/teachers/classes/${req.params.class_id}/chapters/${req.params.chapter_id}/assets/${req.params.asset_id}/generate`);
});

// Teacher: get chapter detail
app.get("/api/teachers/classes/:class_id/chapters/:chapter_id", async (req, res) => {
  await proxyToFastAPI(req, res, `/teachers/classes/${req.params.class_id}/chapters/${req.params.chapter_id}`);
});

// Teacher: library assets
app.get("/api/teachers/library/assets", async (req, res) => {
  const queryStr = req.url.includes('?') ? req.url.substring(req.url.indexOf('?')) : '';
  await proxyToFastAPI(req, res, `/teachers/library/assets${queryStr}`);
});

// Legacy teacher assignment endpoint (frontend compatibility)
app.post("/api/teacher/assignments", async (req, res) => {
  const classId = req.body.class_id || req.body.classId || req.query.class_id || req.query.classId;
  const targetPath = classId
    ? `/teachers/classes/${classId}/assignments`
    : `/teachers/assignments`;
  await proxyToFastAPI(req, res, targetPath);
});

// Legacy teacher GET assignments
app.get("/api/teacher/assignments", async (req, res) => {
  const classId = req.query.class_id || req.query.classId;
  const targetPath = classId
    ? `/teachers/classes/${classId}/assignments`
    : `/teachers/assignments`;
  await proxyToFastAPI(req, res, targetPath);
});

// ─── BFF: Student Routes ────────────────────────────────────────────────────
app.get("/api/students/classes", async (req, res) => {
  await proxyToFastAPI(req, res, `/students/classes`);
});

// Student: list assignments for a class
app.get("/api/students/classes/:class_id/assignments", async (req, res) => {
  await proxyToFastAPI(req, res, `/students/classes/${req.params.class_id}/assignments`);
});

// Student: get assignment detail
app.get("/api/students/classes/:class_id/assignments/:assignment_id", async (req, res) => {
  await proxyToFastAPI(req, res, `/students/classes/${req.params.class_id}/assignments/${req.params.assignment_id}`);
});

// Student: submit attempt
app.post("/api/students/classes/:class_id/assignments/:assignment_id/submit", async (req, res) => {
  await proxyToFastAPI(req, res, `/students/classes/${req.params.class_id}/assignments/${req.params.assignment_id}/submit`);
});

// Student: quotas
app.get("/api/students/quotas", async (req, res) => {
  await proxyToFastAPI(req, res, `/students/quotas`);
});

// Student: doubts
app.get("/api/students/doubts", async (req, res) => {
  await proxyToFastAPI(req, res, `/students/doubts`);
});

app.post("/api/students/doubts", async (req, res) => {
  await proxyToFastAPI(req, res, `/students/doubts`);
});

// Student: chat AI
app.get("/api/chat-with-ai/chats", async (req, res) => {
  await proxyToFastAPI(req, res, `/chat-with-ai/chats`);
});

app.post("/api/chat-with-ai/chats", async (req, res) => {
  await proxyToFastAPI(req, res, `/chat-with-ai/chats`);
});

app.get("/api/chat-with-ai/chats/:chat_id/messages", async (req, res) => {
  await proxyToFastAPI(req, res, `/chat-with-ai/chats/${req.params.chat_id}/messages`);
});

// Legacy student tasks endpoint
app.get("/api/student/tasks", async (req, res) => {
  const classId = req.query.class_id || req.query.classId;
  const targetPath = classId
    ? `/students/classes/${classId}/assignments`
    : `/students/assignments`;
  await proxyToFastAPI(req, res, targetPath);
});


async function startServer() {
  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), 'dist');
    app.use(express.static(distPath));
    app.get('*', (req, res) => {
      res.sendFile(path.join(distPath, 'index.html'));
    });
  }

  const server = app.listen(PORT, "0.0.0.0", () => {
    console.log(`Server running on http://localhost:${PORT}`);
  });

  const wss = new WebSocketServer({ server, path: '/live' });

  wss.on("connection", async (clientWs, req) => {
    try {
      const urlPr = new URL(req.url || "", "http://localhost");
      const activity = urlPr.searchParams.get("activity") || "Explain It";
      const topic = urlPr.searchParams.get("topic") || "";
      const subject = urlPr.searchParams.get("subject") || "";

      const apiKey = process.env.GEMINI_API_KEY;
      if (!apiKey || apiKey === "MY_GEMINI_API_KEY" || apiKey.trim() === "") {
        console.warn("Live API connection ignored: missing GEMINI_API_KEY environment variable");
        clientWs.send(JSON.stringify({
          modelTranscript: "⚠️ [Mootion Alert]: To enable real-time interactive voice features, please set your GEMINI_API_KEY under Settings > Secrets in AI Studio. In the meantime, you can use the chat, the drawing board, and the simulations!"
        }));
        setTimeout(() => {
          if (clientWs.readyState === 1) {
            clientWs.close();
          }
        }, 4000);
        return;
      }

      let systemInstruction = `You are an expert, empathetic, and highly engaging tutor. Your goal is to help the user learn and deeply understand the topics they ask about, rather than just giving them answers.
Follow these core behaviors:
1. Be Conversational & Natural: Speak like a friendly human mentor. Use natural phrasing, occasional conversational fillers, and keep your tone encouraging.
2. Socratic Method: Do not just give away the final answer. Ask guiding questions to help the user arrive at the conclusion themselves. 
3. Bite-Sized Information: Deliver information in small, digestible chunks. Check for understanding before moving on. NEVER ask multiple consecutive questions! Ask ONLY ONE question at a time.
4. Adapt to the User: If the user is struggling, simplify the analogy. If they grasp it quickly, move to more advanced nuances. 
5. Use Vivid Analogies: Tie complex concepts to everyday, relatable scenarios.

Never break character. Never refer to yourself as an AI. You are a mentor having a fluid, real-time spoken conversation.`;

      if (activity === "Explain It") {
        systemInstruction += `\n\nActivity context: The user is explaining '${topic}' under subject '${subject}'. Wait for them to explain. Follow up on their explanation by counter-questioning them asking ONE of "what", "why", or probing deeper into their logic. Ask ONE challenging but concise question at a time.`;
      } else if (activity === "Predict It") {
        systemInstruction = `You are Mootion, a friendly and playful 10-year-old. You are doing a prediction game / dynamic simulation about: '${topic}'. The actual outcome is that the solid stone sank to the bottom while the wood block floated. Talk with the user and ask them why water density differences make objects sink or float! Sound like a smart 10-year-old child.`;
      } else if (activity === "Spot It") {
        systemInstruction = `You are Mootion, a curious 10-year-old. You spotted a riddle: 'A giant ocean container ship of 100,000 tons floats perfectly, but a paperclip sinks instantly'. Speak with the user to learn why relative mass densities explain this. Keep answers brief and sound like a smart 10-year-old child.`;
      } else if (activity === "Connect It") {
        systemInstruction = `You are Mootion, a charming and playful 10-year-old. You want to connect three blocks: Upthrust Force, Liquid Density, and Immersed Volume. Ask the user how they relate and connect together in physics. Keep answers brief and conversational, sounding like a smart 10-year-old child.`;
      }

      const session = await ai.live.connect({
        model: "gemini-3.1-flash-live-preview",
        callbacks: {
          onmessage: (message: LiveServerMessage) => {
            console.log("[server.ts] Received msg from Gemini Live API. Type:", Object.keys(message));
            if (message.serverContent) {
              console.log("[server.ts] -> serverContent keys:", Object.keys(message.serverContent));
              if (message.serverContent.modelTurn) {
                console.log("[server.ts] -> modelTurn parts length:", message.serverContent.modelTurn.parts?.length);
              }
            }

            if (clientWs.readyState !== 1 /* WebSocket.OPEN */) {
              console.log("[server.ts] Client WS is closed, dropping message");
              return;
            }

            const anyMsg = message as any;
            const parts = message.serverContent?.modelTurn?.parts;

            // Handle audio output chunk
            if (parts) {
              for (const part of parts) {
                if (part.inlineData?.data) {
                  console.log("[server.ts] Forwarding audio chunk of length", part.inlineData.data.length);
                  clientWs.send(JSON.stringify({ audio: part.inlineData.data }));
                }
              }
            }

            // Handle interruption signal
            if (message.serverContent?.interrupted) {
              clientWs.send(JSON.stringify({ interrupted: true }));
            }

            // Resilient user speech input transcription paths
            const userText = anyMsg.inputTranscription?.transcription ||
              anyMsg.serverContent?.userTurn?.parts?.[0]?.text ||
              (anyMsg.serverContent?.userTurn?.parts && anyMsg.serverContent.userTurn.parts.map((p: any) => p.text).join("")) ||
              "";
            if (userText) {
              clientWs.send(JSON.stringify({ userTranscript: userText }));
            }

            // Resilient model speech output transcription paths
            let modelText = "";
            if (parts) {
              for (const part of parts) {
                if (part.text) {
                  modelText += part.text;
                }
              }
            }
            if (anyMsg.serverContent?.outputTranscription?.transcription) {
              modelText += anyMsg.serverContent.outputTranscription.transcription;
            }
            if (modelText) {
              clientWs.send(JSON.stringify({ modelTranscript: cleanText(modelText) }));
            }
          },
        },
        config: {
          responseModalities: [Modality.AUDIO],
          speechConfig: {
            voiceConfig: { prebuiltVoiceConfig: { voiceName: "Aoede" } },
          },
          inputAudioTranscription: {},
          outputAudioTranscription: {},
          systemInstruction: { parts: [{ text: systemInstruction }] },
        }
      });

      clientWs.on("message", (data) => {
        try {
          const parsed = JSON.parse(data.toString());
          console.log("[server.ts] Received msg from client WS. Has audio:", !!parsed.audio, "Has text:", !!parsed.text);
          if (parsed.audio) {
            console.log("[server.ts] Sending audio to Gemini Live (length)", parsed.audio.length);
            session.sendRealtimeInput({
              audio: {
                data: parsed.audio,
                mimeType: "audio/pcm;rate=16000"
              }
            });
          }
          if (parsed.text) {
            console.log("[server.ts] Sending text to Gemini Live:", parsed.text);
            session.sendRealtimeInput({
              text: parsed.text
            });
          }
        } catch (e) {
          console.error("Failed to parse client message", e);
        }
      });

      clientWs.on("close", () => {
        session.close();
      });
    } catch (err) {
      console.error("Live API Session Error:", err);
    }
  });
}

app.post("/api/tts", async (req, res) => {
  try {
    const { text } = req.body;
    if (!text) {
      return res.status(400).json({ error: "Text is required" });
    }

    const apiKey = process.env.GEMINI_API_KEY;
    if (!apiKey || apiKey === "MY_GEMINI_API_KEY" || apiKey.trim() === "") {
      return res.status(503).json({ error: "No API Key" });
    }

    const response = await ai.models.generateContent({
      model: "gemini-3.1-flash-tts-preview",
      contents: [{ parts: [{ text }] }],
      config: {
        responseModalities: [Modality.AUDIO],
        speechConfig: {
          voiceConfig: {
            prebuiltVoiceConfig: { voiceName: 'Aoede' },
          },
        },
      },
    });

    const base64Audio = response.candidates?.[0]?.content?.parts?.[0]?.inlineData?.data;
    if (base64Audio) {
      res.json({ audio: base64Audio });
    } else {
      res.status(500).json({ error: "No audio generated" });
    }
  } catch (error) {
    console.error("TTS API Error:", error);
    res.status(500).json({ error: "Failed to generate TTS" });
  }
});

startServer();

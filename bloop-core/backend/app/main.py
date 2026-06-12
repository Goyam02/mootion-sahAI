from fastapi import FastAPI
from api.sad_talker_video import router as sad_talker_router

from api.qa import router as qa
from api.tts import router as tts_router
from api.flashcards import router as flashcards
from api.quiz import router as quiz
from api.play.teach_ai import router as teach_ai
from api.roadmap import router as roadmap_router
from api.play.find_mistake import router as find_mistake
from api.play.complete_missing_link import router as complete_missing_link
from api.manim_generator import router as manim_generator
from api.chat_history import router as chat_history_router
from api.model_finder import router as model_finder_router
from core.database import engine, Base
from fastapi.middleware.cors import CORSMiddleware

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Bloop!")

app.include_router(sad_talker_router)
app.include_router(qa)
app.include_router(tts_router)
app.include_router(flashcards)
app.include_router(quiz)
app.include_router(teach_ai)
app.include_router(roadmap_router)
app.include_router(find_mistake)
app.include_router(complete_missing_link)
app.include_router(manim_generator)
app.include_router(chat_history_router)
app.include_router(model_finder_router)  # Include the model finder router
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow frontend origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def health():
    return {
        "status": "ok"
    }
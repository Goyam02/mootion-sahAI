from services.model_finder.find_model import find_model
from fastapi import APIRouter

router = APIRouter(prefix="/3d", tags=["3D Model Finder"])

@router.get("/api/find-model")
def get_model(query: str):
    return find_model(query)

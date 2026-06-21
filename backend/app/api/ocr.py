from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import require_student


router = APIRouter(prefix="/ocr", tags=["ocr"])


@router.post("/extract-text")
async def extract_text(
    file: UploadFile = File(...),
    user=Depends(require_student),
    db: Session = Depends(get_db),
):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are supported")

    if not settings.azure_vision_endpoint or not settings.azure_vision_api_key:
        raise HTTPException(status_code=501, detail="Azure Computer Vision is not configured on the server")

    image_bytes = await file.read()

    if len(image_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image must be under 10MB")

    try:
        from azure.ai.vision.imageanalysis import ImageAnalysisClient
        from azure.ai.vision.imageanalysis.models import VisualFeatures
        from azure.core.credentials import AzureKeyCredential

        client = ImageAnalysisClient(
            endpoint=settings.azure_vision_endpoint,
            credential=AzureKeyCredential(settings.azure_vision_api_key),
        )

        result = client.analyze(
            image_data=image_bytes,
            visual_features=[VisualFeatures.READ],
        )

        extracted_lines = []
        if result.read is not None:
            for block in result.read.blocks:
                for line in block.lines:
                    extracted_lines.append(line.text)

        extracted_text = "\n".join(extracted_lines).strip()

        if not extracted_text:
            return {"text": "", "message": "No text could be extracted from the image."}

        return {"text": extracted_text, "message": "Text extracted successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR processing failed: {str(e)}")

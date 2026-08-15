from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from .. import models, schemas
from ..services.ai.commentary_service import generate_commentary, get_latest_commentary

router = APIRouter(prefix="/ai", tags=["AI"])

@router.post("/commentary", response_model=schemas.AICommentaryResponse)
def create_commentary(
    request: schemas.AICommentaryRequest,
    db: Session = Depends(get_db)
):
    try:
        commentary = generate_commentary(db, force=request.force)
        return commentary
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la génération : {e}")

@router.get("/commentary/latest", response_model=schemas.AICommentaryResponse)
def latest_commentary(db: Session = Depends(get_db)):
    commentary = get_latest_commentary(db)
    if not commentary:
        raise HTTPException(status_code=404, detail="Aucun commentaire IA disponible.")
    return commentary
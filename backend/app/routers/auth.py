from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from .. import models, schemas
from ..services.auth import authenticate_user, create_access_token, get_current_user, require_admin, hash_password

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=schemas.TokenResponse)
def login(payload: schemas.UserLogin, db: Session = Depends(get_db)):
    user = authenticate_user(db, payload.username, payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nom d'utilisateur ou mot de passe incorrect"
        )
    token = create_access_token(user)
    return {
        "access_token": token,
        "token_type": "bearer",
        "username": user.username,
        "is_admin": user.is_admin
    }


@router.get("/me", response_model=schemas.UserResponse)
def read_users_me(current_user: models.User = Depends(get_current_user)):
    return current_user


@router.get("/users", response_model=List[schemas.UserListItem])
def list_users(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin)
):
    return db.query(models.User).order_by(models.User.username).all()


@router.post("/users", response_model=schemas.UserListItem, status_code=201)
def create_user(
    payload: schemas.UserCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin)
):
    existing = db.query(models.User).filter(models.User.username == payload.username).first()
    if existing:
        raise HTTPException(status_code=409, detail="Ce nom d'utilisateur existe déjà.")
    user = models.User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        is_admin=payload.is_admin
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.delete("/users/{user_id}", status_code=204)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin)
):
    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable.")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Vous ne pouvez pas supprimer votre propre compte.")
    if user.username == "admin":
        raise HTTPException(status_code=400, detail="Le compte admin ne peut pas être supprimé.")
    count = db.query(models.User).count()
    if count <= 1:
        raise HTTPException(status_code=400, detail="Impossible de supprimer le dernier utilisateur.")
    db.delete(user)
    db.commit()
    return None
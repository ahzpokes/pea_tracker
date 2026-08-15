from dotenv import load_dotenv
load_dotenv()

import os
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .database import Base, engine, SessionLocal
from . import models
from .routers import dashboard, etfs, prices, settings, charts, signals, ai, auth
from .services.auth import get_current_user, require_admin, hash_password

app = FastAPI(title="PEA Dual Momentum API", version="0.1.0")

# Configuration CORS
# En production, restreignez à votre domaine exact
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Création des tables
Base.metadata.create_all(bind=engine)


def init_default_settings():
    """Initialise les paramètres IA depuis .env s'ils n'existent pas en base."""
    db = SessionLocal()
    try:
        defaults = [
            ("AI_PROVIDER", os.getenv("AI_PROVIDER", "local")),
            ("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY", "")),
            ("NVIDIA_API_KEY", os.getenv("NVIDIA_API_KEY", "")),
            ("AI_MODEL", os.getenv("AI_MODEL", "")),
        ]
        for key, value in defaults:
            existing = db.query(models.Setting).filter_by(setting_key=key).first()
            if not existing:
                db.add(models.Setting(setting_key=key, setting_value=value))
        db.commit()
    finally:
        db.close()


def init_default_user():
    """Crée l'utilisateur admin par défaut si absent."""
    db = SessionLocal()
    try:
        existing = db.query(models.User).filter(models.User.username == "admin").first()
        if not existing:
            default_password = os.getenv("DEFAULT_ADMIN_PASSWORD", "admin123")
            db.add(models.User(
                username="admin",
                password_hash=hash_password(default_password),
                is_admin=True
            ))
            db.commit()
    finally:
        db.close()


# Initialisation au démarrage
init_default_settings()
init_default_user()

# Routes non protégées
app.include_router(auth.router, prefix="/api")

# Routes protégées (authentification requise)
app.include_router(dashboard.router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(etfs.router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(prices.router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(charts.router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(signals.router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(ai.router, prefix="/api", dependencies=[Depends(get_current_user)])

# Paramètres réservés aux administrateurs
app.include_router(settings.router, prefix="/api", dependencies=[Depends(require_admin)])


@app.get("/api/health")
def health():
    return {"status": "ok"}


# Servir le frontend compilé (si le dossier dist existe)
FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.isdir(FRONTEND_DIST):
    # Montage des assets statiques (JS, CSS)
    app.mount(
        "/assets",
        StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")),
        name="assets"
    )

    # Route catch-all pour renvoyer index.html
    @app.get("/{path:path}")
    async def serve_frontend(path: str):
        full_path = os.path.join(FRONTEND_DIST, path)
        if path != "" and os.path.exists(full_path):
            return FileResponse(full_path)
        return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))
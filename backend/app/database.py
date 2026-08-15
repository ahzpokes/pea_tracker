import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# URL de base de données depuis l'environnement (par défaut SQLite local)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/pea_momentum.db")

# Pour PostgreSQL, on ne veut pas de connect_args spécifiques
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
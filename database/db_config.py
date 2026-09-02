from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import streamlit as st

# Récupération sécurisée depuis st.secrets avec repli local SQLite si Supabase est inaccessible
try:
    DATABASE_URL = st.secrets["DB_URL"]
    # Pour PostgreSQL/Supabase, on utilise connect_timeout
    connect_args = {"connect_timeout": 10}
except Exception:
    # Repli automatique sur SQLite local en cas de coupure 3G ou d'absence de secrets
    DATABASE_URL = "sqlite:///database.db"
    connect_args = {"timeout": 15}

# Configuration de l'engine avec gestion adaptée du dialecte (SQLite vs PostgreSQL)
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args=connect_args
    )
else:
    engine = create_engine(
        DATABASE_URL,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=300,
        connect_args=connect_args
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def init_db():
    # Importation explicite de tous les modèles (y compris ActivityLog) pour la création des tables
    from database.models import School, User, ActivityLog
    import bcrypt
    
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        super_admin_existe = db.query(User).filter(User.role == 'super_admin').first()
        if not super_admin_existe:
            ecole_defaut = db.query(School).first()
            if not ecole_defaut:
                ecole_defaut = School(
                    nom="Complexe Scolaire Privé Rahmat-FH",
                    code="CSP-RAHMAT",
                    devise="Excellence - Travail - Succès",
                    adresse="Niamey, Niger",
                    contacts="99797163"
                )
                db.add(ecole_defaut)
                db.commit()
                db.refresh(ecole_defaut)

            hashed_pw = bcrypt.hashpw("admin2026".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            admin_user = User(
                username="admin",
                password=hashed_pw,
                role="super_admin",
                school_id=ecole_defaut.id
            )
            db.add(admin_user)
            db.commit()
    finally:
        db.close()
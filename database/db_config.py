import os
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import streamlit as st

# Récupération sécurisée depuis st.secrets avec repli local SQLite si Supabase est inaccessible
try:
    DATABASE_URL = st.secrets["DB_URL"]
    connect_args = {"connect_timeout": 10}
except Exception:
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
    # Importation explicite de tous les modèles pour la création des tables
    from database.models import (
        School, User, Classe, Eleve, Matiere, CahierTexte, 
        Programme, Presence, Note, Enseignant, Affectation, 
        EmploiDuTemps, EcheancePaiement, PlanificationEvaluation, 
        ActivityLog, SystemLog, Paiement, Depense
    )
    import bcrypt
    
    # 1. Création initiale des tables de la base de données
    Base.metadata.create_all(bind=engine)
    
    # 2. Migrations automatiques exécutées AVANT toute requête ORM (évite les erreurs de colonnes manquantes)
    migrations = [
        "ALTER TABLE users ADD COLUMN changer_mdp_requis BOOLEAN DEFAULT 1;",
        "ALTER TABLE cahiers_texte ADD COLUMN duree FLOAT DEFAULT 1.0;",
        "ALTER TABLE users ADD COLUMN deleted_at TIMESTAMP;",
        "ALTER TABLE schools ADD COLUMN deleted_at TIMESTAMP;",
        "ALTER TABLE classes ADD COLUMN deleted_at TIMESTAMP;",
        "ALTER TABLE eleves ADD COLUMN deleted_at TIMESTAMP;"
    ]

    with engine.connect() as conn:
        for mig in migrations:
            try:
                conn.execute(text(mig))
                conn.commit()
            except Exception:
                conn.rollback() # Ignore si la colonne existe déjà

    # 3. Initialisation du Super Administrateur et de l'établissement par défaut
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
                school_id=ecole_defaut.id,
                changer_mdp_requis=False
            )
            db.add(admin_user)
            db.commit()
    finally:
        db.close()
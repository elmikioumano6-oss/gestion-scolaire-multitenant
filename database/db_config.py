import os
import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Forçage direct de l'URL sur le tunnel SSH local pour pointer vers la base de production du VPS
DATABASE_URL = "postgresql://erp_user:Rahmatfh2026@127.0.0.1:5432/school_erp"
connect_args = {"connect_timeout": 10}

# Configuration de l'engine PostgreSQL via le tunnel
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

    # 3. Initialisation ou mise à jour forcée du compte admin et de l'établissement par défaut
    db = SessionLocal()
    try:
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

        # Recherche ou création de l'utilisateur admin avec mise à jour garantie du mot de passe
        hashed_pw = bcrypt.hashpw("admin2026".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        admin_user = db.query(User).filter(User.username == "admin").first()
        if admin_user:
            admin_user.password = hashed_pw
            admin_user.role = "super_admin"
            admin_user.school_id = ecole_defaut.id
            admin_user.changer_mdp_requis = False
        else:
            admin_user = User(
                username="admin",
                password=hashed_pw,
                role="super_admin",
                school_id=ecole_defaut.id,
                changer_mdp_requis=False
            )
            db.add(admin_user)
        db.commit()
    except Exception as e:
        db.rollback()
        st.error(f"Erreur lors de l'initialisation de la base de données : {e}")
    finally:
        db.close()
import os
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import streamlit as st
from dotenv import load_dotenv

# Charger les variables d'environnement en forçant le remplacement du cache
load_dotenv(override=True)

# Récupération sécurisée et prioritaire via .env ou st.secrets, avec secours SQLite
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    try:
        DATABASE_URL = st.secrets["DB_URL"]
    except Exception:
        DATABASE_URL = "sqlite:///staging.db"

connect_args = {"connect_timeout": 10} if not DATABASE_URL.startswith("sqlite") else {"timeout": 15}

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

class TenantSession(Session):
    """Session SQLAlchemy personnalisée qui isole automatiquement les données par school_id."""
    def query(self, *entities, **kwargs):
        query = super().query(*entities, **kwargs)
        
        # Si on est dans Streamlit et qu'un tenant est actif (et pas super admin)
        try:
            school_id = st.session_state.get("school_id")
            is_super = st.session_state.get("is_super_admin", False)
            
            if school_id and not is_super:
                for entity in entities:
                    # On vérifie si l'entité possède un attribut/colonne school_id
                    if hasattr(entity, "school_id"):
                        query = query.filter(entity.school_id == school_id)
        except Exception:
            pass # Hors contexte Streamlit ou session non initialisée
            
        return query

# Utilisation de notre classe de session cloisonnée pour le multi-tenancy
SessionLocal = sessionmaker(class_=TenantSession, autocommit=False, autoflush=False, bind=engine)
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

    # 3. Initialisation ou mise à jour forcée des comptes et de l'établissement par défaut
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

        hashed_pw = bcrypt.hashpw("admin2026".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # --- Gestion du Super Admin Global ---
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

        # --- Gestion garantie de l'Administrateur local du CSP Rahmat-FH ---
        admin_rahmat = db.query(User).filter(User.username == "admin_rahmat").first()
        if admin_rahmat:
            admin_rahmat.role = "directeur"
            admin_rahmat.school_id = ecole_defaut.id
            admin_rahmat.changer_mdp_requis = False
        else:
            admin_rahmat = User(
                username="admin_rahmat",
                password=hashed_pw,
                role="directeur",
                school_id=ecole_defaut.id,
                changer_mdp_requis=False
            )
            db.add(admin_rahmat)

        db.commit()
    except Exception as e:
        db.rollback()
        st.error(f"Erreur lors de l'initialisation de la base de données : {e}")
    finally:
        db.close()
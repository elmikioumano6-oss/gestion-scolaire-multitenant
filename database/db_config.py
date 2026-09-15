import os
from sqlalchemy import create_engine, text, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import streamlit as st
from dotenv import load_dotenv

# Charger les variables d'environnement en forçant le remplacement du cache
load_dotenv(override=True)

# Récupération sécurisée et prioritaire via .env ou st.secrets (Zéro hardcode de production)
DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("DB_URL")

if not DATABASE_URL:
    try:
        DATABASE_URL = st.secrets["DB_URL"]
    except Exception:
        DATABASE_URL = None

if not DATABASE_URL:
    raise ValueError(
        "🚨 ERREUR CRITIQUE DE SÉCURITÉ : Aucune URL de base de données n'a été trouvée "
        "dans les variables d'environnement (.env) ou les secrets Streamlit."
    )

# Sécurité anti-localhost : Si l'URL contient localhost, on la force en 127.0.0.1 (IPv4 locale)
if "localhost" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("localhost", "127.0.0.1")

connect_args = {"connect_timeout": 30} if not DATABASE_URL.startswith("sqlite") else {"timeout": 30}

# Configuration de l'engine avec un pool renforcé pour les connexions persistantes
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args=connect_args
    )
else:
    engine = create_engine(
        DATABASE_URL,
        pool_size=20,
        max_overflow=40,
        pool_pre_ping=True,
        pool_recycle=1800,
        connect_args=connect_args
    )

class TenantSession(Session):
    """Session SQLAlchemy personnalisée qui isole automatiquement les données par school_id."""
    def query(self, *entities, **kwargs):
        query = super().query(*entities, **kwargs)
        
        try:
            school_id = st.session_state.get("school_id")
            is_super = st.session_state.get("is_super_admin", False)
            
            if school_id and not is_super:
                for entity in entities:
                    from database.models import User
                    if hasattr(entity, "school_id") and entity != User:
                        query = query.filter(entity.school_id == school_id)
        except Exception:
            pass
            
        return query

# Synchronisation automatique de la variable RLS PostgreSQL à chaque début de transaction
@event.listens_for(Session, "after_begin")
def receive_after_begin(session, transaction, connection):
    try:
        if DATABASE_URL and not DATABASE_URL.startswith("sqlite"):
            school_id = st.session_state.get("school_id")
            is_super = st.session_state.get("is_super_admin", False)
            if school_id and not is_super:
                connection.execute(text(f"SET LOCAL app.current_school_id = '{school_id}';"))
            else:
                connection.execute(text("SET LOCAL app.current_school_id = '';"))
    except Exception:
        pass

# Utilisation de la session cloisonnée pour le multi-tenancy
SessionLocal = sessionmaker(class_=TenantSession, autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def init_db():
    from database.models import (
        School, User, Classe, Eleve, Matiere, CahierTexte,  
        Programme, Presence, Note, Enseignant, Affectation,  
        EmploiDuTemps, EcheancePaiement, PlanificationEvaluation,  
        ActivityLog, SystemLog, Paiement, Depense
    )
    import bcrypt
    
    # 1. Création initiale des tables de la base de données
    Base.metadata.create_all(bind=engine)
    
    # 2. Migrations automatiques exécutées de manière robuste
    migrations = [
        "ALTER TABLE users ADD COLUMN changer_mdp_requis BOOLEAN DEFAULT 1;",
        "ALTER TABLE cahiers_texte ADD COLUMN duree FLOAT DEFAULT 1.0;",
        "ALTER TABLE users ADD COLUMN deleted_at TIMESTAMP;",
        "ALTER TABLE schools ADD COLUMN deleted_at TIMESTAMP;",
        "ALTER TABLE schools ADD COLUMN subdomain VARCHAR;",
        "ALTER TABLE classes ADD COLUMN deleted_at TIMESTAMP;",
        "ALTER TABLE eleves ADD COLUMN deleted_at TIMESTAMP;"
    ]

    with engine.connect() as conn:
        for mig in migrations:
            try:
                conn.execute(text(mig))
                conn.commit()
            except Exception:
                conn.rollback()

    # 3. Initialisation initiale sécurisée (création unique si inexistant, sans écrasement forcé)
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

        # Création du Super Admin uniquement s'il n'existe pas du tout
        admin_user = db.query(User).filter(User.username == "admin").first()
        if not admin_user:
            default_hashed_pw = bcrypt.hashpw("admin2026".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            admin_user = User(
                username="admin",
                password=default_hashed_pw,
                role="super_admin",
                school_id=ecole_defaut.id,
                changer_mdp_requis=True # Exige un changement de mot de passe à la première connexion
            )
            db.add(admin_user)

        # Création de l'administrateur local uniquement s'il n'existe pas
        admin_rahmat = db.query(User).filter(User.username == "admin_rahmat").first()
        if not admin_rahmat:
            default_hashed_pw = bcrypt.hashpw("admin2026".encode('utf-8'), bcrypt.gensalt()).degre() if 'degre' in locals() else bcrypt.hashpw("admin2026".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            admin_rahmat = User(
                username="admin_rahmat",
                password=default_hashed_pw,
                role="directeur",
                school_id=ecole_defaut.id,
                changer_mdp_requis=True
            )
            db.add(admin_rahmat)

        db.commit()
    except Exception as e:
        db.rollback()
        st.error(f"Erreur lors de l'initialisation de la base de données : {e}")
    finally:
        db.close()
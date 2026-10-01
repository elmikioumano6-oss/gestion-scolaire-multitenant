import os
from contextlib import contextmanager
from sqlalchemy import create_engine, text, event, exc
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import streamlit as st
from dotenv import load_dotenv
import bcrypt

load_dotenv(override=True)

DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("DB_URL")

if not DATABASE_URL:
    try:
        DATABASE_URL = st.secrets["DB_URL"]
    except Exception:
        DATABASE_URL = None

if not DATABASE_URL:
    DATABASE_URL = "postgresql://erp_user:Rahmatfh2026@127.0.0.1:5432/school_erp"

if "localhost" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("localhost", "127.0.0.1")

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"timeout": 15}
    )
    
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()
        
else:
    engine = create_engine(
        DATABASE_URL,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=1800,
        connect_args={"connect_timeout": 10}
    )

    @event.listens_for(engine, "checkout")
    def ping_connection(dbapi_connection, connection_record, connection_proxy):
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("SELECT 1")
        except Exception:
            raise exc.DisconnectionError()
        cursor.close()

class TenantSession(Session):
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

SessionLocal = sessionmaker(class_=TenantSession, autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

@contextmanager
def get_db_session():
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

def init_db():
    try:
        from database.models import (
            School, User, Classe, Eleve, Matiere, CahierTexte,  
            Programme, Presence, Note, Enseignant, Affectation,  
            EmploiDuTemps, EcheancePaiement, PlanificationEvaluation,  
            ActivityLog, SystemLog, Paiement, Depense
        )
        
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))

        Base.metadata.create_all(bind=engine)
        
        migrations = [
            "ALTER TABLE users ADD COLUMN changer_mdp_requis BOOLEAN DEFAULT 1;",
            "ALTER TABLE cahiers_texte ADD COLUMN duree FLOAT DEFAULT 1.0;",
            "ALTER TABLE users ADD COLUMN deleted_at TIMESTAMP;",
            "ALTER TABLE schools ADD COLUMN deleted_at TIMESTAMP;",
            "ALTER TABLE schools ADD COLUMN subdomain VARCHAR;",
            "ALTER TABLE classes ADD COLUMN deleted_at TIMESTAMP;",
            "ALTER TABLE eleves ADD COLUMN deleted_at TIMESTAMP;",
            "ALTER TABLE matieres ADD COLUMN volume_horaire FLOAT DEFAULT 0.0;"
        ]

        with engine.connect() as conn:
            for mig in migrations:
                try:
                    conn.execute(text(mig))
                    conn.commit()
                except Exception:
                    conn.rollback()

        with get_db_session() as db:
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
                db.flush()

            admin_user = db.query(User).filter(User.username == "admin").first()
            if not admin_user:
                default_hashed_pw = bcrypt.hashpw("admin2026".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                admin_user = User(
                    username="admin",
                    password=default_hashed_pw,
                    role="super_admin",
                    school_id=ecole_defaut.id,
                    changer_mdp_requis=True
                )
                db.add(admin_user)

            admin_rahmat = db.query(User).filter(User.username == "admin_rahmat").first()
            if not admin_rahmat:
                default_hashed_pw = bcrypt.hashpw("admin2026".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                admin_rahmat = User(
                    username="admin_rahmat",
                    password=default_hashed_pw,
                    role="directeur",
                    school_id=ecole_defaut.id,
                    changer_mdp_requis=True
                )
                db.add(admin_rahmat)

    except Exception as e:
        st.error(
            "❌ **Impossible de joindre la base de données via le tunnel SSH ou le serveur PostgreSQL.**\n\n"
            f"Détails techniques : `{e}`\n\n"
            "👉 *Veuillez vérifier que votre script de tunnel SSH est bien actif et que le port local est correct.*"
        )
        st.stop()
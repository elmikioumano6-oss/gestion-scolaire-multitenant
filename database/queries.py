import streamlit as st
from database.db_config import SessionLocal
from database.models import Classe, Matiere, School

@st.cache_data(ttl=600) # Le cache expire automatiquement toutes les 10 minutes
def get_classes_cached(school_id: int):
    db = SessionLocal()
    try:
        # Grâce au TenantSession, le filtrage par school_id est automatique, 
        # mais on peut le préciser explicitement pour la sécurité du cache
        classes = db.query(Classe).filter(Classe.school_id == school_id).all()
        # On convertit en structures simples si nécessaire pour le cache, 
        # ou l'on retourne les objets gérés par SQLAlchemy
        return [(c.id, c.nom) for c in classes]
    finally:
        db.close()

@st.cache_data(ttl=600)
def get_matieres_cached(school_id: int):
    db = SessionLocal()
    try:
        matieres = db.query(Matiere).filter(Matiere.school_id == school_id).all()
        return [(m.id, m.nom) for m in matieres]
    finally:
        db.close()
import streamlit as st
from database.db_config import SessionLocal
from database.models import Classe, Matiere, School

@st.cache_data(ttl=600)
def get_classes_cached(school_id: int):
    db = SessionLocal()
    try:
        # On filtre par école et on exclue les classes archivées (Soft Delete)
        query = db.query(Classe).filter(Classe.school_id == school_id)
        if hasattr(Classe, 'deleted_at'):
            query = query.filter(Classe.deleted_at.is_(None))
            
        classes = query.all()
        
        # Sécurité pour récupérer le bon libellé (nom ou libelle)
        resultats = []
        for c in classes:
            nom_classe = getattr(c, 'libelle', None) or getattr(c, 'nom', 'Classe sans nom')
            resultats.append((c.id, nom_classe))
            
        return resultats
    finally:
        db.close()

@st.cache_data(ttl=600)
def get_matieres_cached(school_id: int):
    db = SessionLocal()
    try:
        query = db.query(Matiere).filter(Matiere.school_id == school_id)
        if hasattr(Matiere, 'deleted_at'):
            query = query.filter(Matiere.deleted_at.is_(None))
            
        matieres = query.all()
        
        resultats = []
        for m in matieres:
            nom_matiere = getattr(m, 'libelle', None) or getattr(m, 'nom', 'Matière sans nom')
            resultats.append((m.id, nom_matiere))
            
        return resultats
    finally:
        db.close()

def clear_cache_queries():
    """Vide le cache global des requêtes dès qu'une modification est enregistrée."""
    st.cache_data.clear()
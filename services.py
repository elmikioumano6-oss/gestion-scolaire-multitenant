import streamlit as st
from database.db_config import SessionLocal
from database.models import Classe, Matiere, Enseignant, AnneeScolaire

@st.cache_data(ttl=300)
def get_classes_cached(school_id):
    """Récupère la liste des classes d'un établissement avec mise en cache de 5 minutes."""
    if not school_id:
        return []
    db = SessionLocal()
    try:
        classes = db.query(Classe).filter(Classe.school_id == school_id).all()
        # On retourne des structures légères ou des dictionnaires/tuples pour faciliter le cache si besoin, 
        # mais ici les objets SQLAlchemy sérialisables ou listes d'attributs conviennent.
        # Pour éviter les problèmes de session fermée, on extrait les données utiles.
        return [{"id": c.id, "nom": c.nom, "niveau": getattr(c, "niveau", "")} for c in classes]
    except Exception:
        return []
    finally:
        db.close()


@st.cache_data(ttl=300)
def get_matieres_cached(school_id):
    """Récupère la liste des matières d'un établissement avec mise en cache."""
    if not school_id:
        return []
    db = SessionLocal()
    try:
        matieres = db.query(Matiere).filter(Matiere.school_id == school_id).all()
        return [{"id": m.id, "nom": m.nom, "code": getattr(m, "code", "")} for m in matieres]
    except Exception:
        return []
    finally:
        db.close()


@st.cache_data(ttl=300)
def get_enseignants_cached(school_id):
    """Récupère la liste des enseignants d'un établissement avec mise en cache."""
    if not school_id:
        return []
    db = SessionLocal()
    try:
        enseignants = db.query(Enseignant).filter(Enseignant.school_id == school_id).all()
        return [{"id": e.id, "nom": e.nom, "prenom": getattr(e, "prenom", "")} for e in enseignants]
    except Exception:
        return []
    finally:
        db.close()


@st.cache_data(ttl=600)
def get_annees_scolaires_cached(school_id):
    """Récupère les années scolaires disponibles pour un établissement."""
    if not school_id:
        return []
    db = SessionLocal()
    try:
        annees = db.query(AnneeScolaire).filter(AnneeScolaire.school_id == school_id).all()
        return [{"id": a.id, "libelle": a.libelle, "active": a.active} for a in annees]
    except Exception:
        return []
    finally:
        db.close()
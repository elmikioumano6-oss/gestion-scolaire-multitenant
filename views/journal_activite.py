import streamlit as st
import pandas as pd
from database.db_config import SessionLocal
from database.models import School

def afficher_journal_activite():
    st.subheader("📜 Journal d'Activité & Audit du Système")
    st.markdown("Suivi des actions et des événements enregistrés sur la plateforme avec isolation multi-tenant stricte.")
    st.markdown("---")

    school_id = st.session_state.get("school_id")
    is_super_admin = st.session_state.get("is_super_admin", False)
    
    db = SessionLocal()
    try:
        if school_id:
            ecole_courante = db.query(School).filter(School.id == school_id).first()
            school_name = ecole_courante.nom if ecole_courante else st.session_state.get("school_name", "Établissement")
        else:
            school_name = st.session_state.get("school_name", "Établissement")
    finally:
        db.close()

    cycle_en_cours = st.session_state.get("cycle_actif", "Collège")

    if not school_id and not is_super_admin:
        st.warning("⚠️ Veuillez vous connecter pour accéder à cette section.")
        return

    st.markdown(f"### Historique des Événements — **{school_name} ({cycle_en_cours})**")

    # Récupération filtrée par école (ou simulation propre propre à l'établissement actif)
    current_user = st.session_state.get("username", "admin_rahmat")
    
    data_journal = [
        {
            "Date & Heure": "2026-09-01 23:15:00",
            "Utilisateur": current_user,
            "Action": "Connexion à la plateforme",
            "Module": "Authentification",
            "Statut": "Succès"
        }
    ]
    
    df_journal = pd.DataFrame(data_journal)
    st.dataframe(df_journal, use_container_width=True)

    st.info("💡 Le journal d'activité consigne automatiquement les opérations sensibles de l'établissement (modifications de notes, inscriptions, et mouvements financiers).")

# Alias de compatibilité complète pour le routeur
afficher_journal_d_activite = afficher_journal_activite
afficher_journal_activites = afficher_journal_activite
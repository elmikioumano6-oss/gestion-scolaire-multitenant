import streamlit as st
import pandas as pd
from database.db_config import SessionLocal
from database.models import School, User, JournalActivite

def afficher_journal_activite():
    st.subheader("📜 Journal d'Activité & Audit du Système")
    st.markdown("Suivi des actions et des événements enregistrés sur la plateforme avec isolation multi-tenant stricte.")
    st.markdown("---")

    school_id = st.session_state.get("school_id")
    is_super_admin = st.session_state.get("is_super_admin", False)
    school_name = st.session_state.get("school_name", "Établissement")

    if not school_id and not is_super_admin:
        st.warning("⚠️ Veuillez vous connecter pour accéder à cette section.")
        return

    db = SessionLocal()
    try:
        if is_super_admin:
            st.markdown("### 🌐 Vue Globale Super Administrateur")
            ecoles = db.query(School).all()
            options_ecoles = {"Toutes les écoles (Vue Globale)": None}
            for ecole in ecoles:
                options_ecoles[ecole.nom] = ecole.id
            
            choix_ecole_nom = st.selectbox("Filtrer par établissement", list(options_ecoles.keys()))
            selected_school_id = options_ecoles[choix_ecole_nom]
            
            query = db.query(JournalActivite)
            if selected_school_id is not None:
                query = query.filter(JournalActivite.school_id == selected_school_id)
                st.markdown(f"### Historique des Événements — **{choix_ecole_nom}**")
            else:
                st.markdown("### Historique Global — **Toutes les Écoles**")
        else:
            st.markdown(f"### Historique des Événements — **{school_name}**")
            query = db.query(JournalActivite).filter(JournalActivite.school_id == school_id)

        logs = query.order_by(JournalActivite.timestamp.desc()).all()

        if not logs:
            st.info("Aucun événement enregistré dans le journal d'activité pour le moment.")
        else:
            data_logs = []
            for l in logs:
                data_logs.append({
                    "Date & Heure": l.timestamp.strftime("%d/%m/%Y %H:%M:%S") if hasattr(l, 'timestamp') and l.timestamp else "N/D",
                    "Utilisateur": getattr(l, 'username', 'N/D'),
                    "Action": getattr(l, 'action', 'N/D'),
                    "Module": getattr(l, 'module', 'N/D'),
                    "Statut": getattr(l, 'statut', 'Succès')
                })
            st.dataframe(pd.DataFrame(data_logs), use_container_width=True)

        st.info("💡 Le journal d'activité consigne automatiquement les opérations sensibles de l'établissement (modifications de notes, inscriptions, et mouvements financiers).")

    finally:
        db.close()

# Alias de compatibilité
afficher_journal_activite = afficher_journal_activite
afficher_audit = afficher_journal_activite
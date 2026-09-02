import streamlit as st
import pandas as pd
from database.db_config import SessionLocal
from database.models import School, ActivityLog

def afficher_journal_activite():
    st.subheader("📜 Journal d'Activité & Audit du Système")
    st.markdown("Suivi des actions et des événements enregistrés sur la plateforme avec isolation multi-tenant stricte.")
    st.markdown("---")

    db = SessionLocal()
    try:
        is_super = st.session_state.get("is_super_admin", False)
        
        # Si c'est le Super Admin, on ajoute un sélecteur pour toutes les écoles
        if is_super:
            st.markdown("### 🔍 Filtrer par Établissement (Mode Super Admin)")
            ecoles = db.query(School).all()
            if not ecoles:
                st.info("Aucun établissement enregistré sur la plateforme.")
                return
            
            options_ecoles = {f"{e.nom} (Code: {e.code})": e.id for e in ecoles}
            choix_nom = st.selectbox("Sélectionner l'établissement à auditer", options=list(options_ecoles.keys()))
            selected_school_id = options_ecoles[choix_nom]
            
            st.markdown(f"#### Historique des Événements — {choix_nom}")
            logs = db.query(ActivityLog).filter(ActivityLog.school_id == selected_school_id).order_by(ActivityLog.id.desc()).all()
            
        else:
            # Pour un administrateur d'école classique
            school_id = st.session_state.get("school_id")
            ecole = db.query(School).filter(School.id == school_id).first()
            nom_ecole = ecole.nom if ecole else "Mon Établissement"
            
            st.markdown(f"#### Historique des Événements — {nom_ecole}")
            logs = db.query(ActivityLog).filter(ActivityLog.school_id == school_id).order_by(ActivityLog.id.desc()).all()

        if not logs:
            st.info("📭 Aucune activité enregistrée pour le moment pour cet établissement.")
        else:
            data = []
            for log in logs:
                data.append({
                    "Date & Heure": getattr(log, 'timestamp', getattr(log, 'date_heure', 'N/D')),
                    "Utilisateur": getattr(log, 'username', getattr(log, 'utilisateur', 'N/D')),
                    "Action": getattr(log, 'action', 'N/D'),
                    "Module": getattr(log, 'module', 'N/D'),
                    "Statut": getattr(log, 'statut', 'Succès')
                })
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True)

        st.markdown("---")
        st.markdown("💡 *Le journal d'activité consigne automatiquement les opérations sensibles de chaque établissement (modifications de notes, inscriptions, paiements de scolarité et connexions).*")

    finally:
        db.close()

afficher_journal_activite_global = afficher_journal_activite
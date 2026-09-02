import streamlit as st
import pandas as pd
from datetime import datetime
from database.db_config import SessionLocal
from database.models import School, ActivityLog

def afficher_personnels():
    st.subheader("👥 Personnels et Rôles (RBAC)")
    st.markdown("Gestion des comptes, des habilitations et des accès du personnel par cycle et par établissement.")
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

    st.markdown(f"### Gestion des accès en cours — **{school_name} ({cycle_en_cours})**")

    comptes_actifs = [
        {
            "Nom / Identifiant": "admin",
            "Rôle": "super_admin",
            "Dernière activité": "2026-09-02 12:35:43.825479"
        },
        {
            "Nom / Identifiant": "admin_rahmat",
            "Rôle": "directeur",
            "Dernière activité": str(datetime.utcnow())
        }
    ]

    df_rbac = pd.DataFrame(comptes_actifs)
    st.dataframe(df_rbac, use_container_width=True)

    db = SessionLocal()
    try:
        target_school_id = school_id or 1
        db.add(ActivityLog(
            school_id=target_school_id,
            timestamp=datetime.utcnow(),
            username=st.session_state.get("username", "admin"),
            action="Consultation du module Personnels et Rôles (RBAC)",
            module="Personnels et rôles",
            statut="Succès"
        ))
        db.commit()
    finally:
        db.close()

# Alias de compatibilité exhaustive pour garantir l'appel par le routeur app.py
afficher_personnels_et_roles = afficher_personnels
afficher_personnels_roles = afficher_personnels
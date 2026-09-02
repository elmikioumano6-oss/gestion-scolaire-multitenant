import streamlit as st
import pandas as pd
from database.db_config import SessionLocal
from database.models import User, School

def afficher_personnels_roles():
    st.subheader("👥 Personnels et Rôles (RBAC)")
    st.markdown("Gestion des comptes, des habilitations et des accès du personnel par cycle et par établissement.")
    st.markdown("---")

    school_id = st.session_state.get("school_id")
    is_super_admin = st.session_state.get("is_super_admin", False)
    
    # Récupération dynamique du nom de l'école active
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

    db = SessionLocal()
    try:
        query = db.query(User)
        if not is_super_admin and school_id:
            query = query.filter(User.school_id == school_id)
        users = query.all()

        st.markdown(f"### Gestion des accès en cours — **{school_name} ({cycle_en_cours})**")

        if not users:
            st.info("Aucun personnel enregistré pour le moment dans cet établissement.")
        else:
            data_users = []
            for u in users:
                data_users.append({
                    "Nom / Identifiant": getattr(u, 'username', 'Utilisateur'),
                    "Rôle": getattr(u, 'role', 'Personnel'),
                    "Dernière activité": str(getattr(u, 'derniere_activite', '—'))
                })
            df_users = pd.DataFrame(data_users)
            st.dataframe(df_users, use_container_width=True)

    finally:
        db.close()

# Alias de compatibilité complète pour le routeur
afficher_personnels = afficher_personnels_roles
afficher_personnel_et_roles = afficher_personnels_roles
afficher_personnels_et_roles = afficher_personnels_roles
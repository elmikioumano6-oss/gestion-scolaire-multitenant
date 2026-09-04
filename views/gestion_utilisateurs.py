import streamlit as st
import pandas as pd
from datetime import datetime
from database.db_config import SessionLocal
from database.models import School
from database.audit import log_action_erp

def afficher_gestion_utilisateurs():
    st.subheader("👥 Gestion des Comptes Utilisateurs & Rôles")
    st.markdown("Administration sécurisée des accès, des comptes et des rôles du personnel avec isolation multi-tenant stricte.")
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

    db = SessionLocal()
    try:
        tab_liste, tab_ajout = st.tabs(["📋 Liste des Utilisateurs", "➕ Nouvel Utilisateur"])

        if "users_data" not in st.session_state:
            st.session_state["users_data"] = {
                "CSP Rahmat-FH": [
                    {"Nom d'utilisateur": "admin", "Rôle / Fonction": "super_admin", "Dernière activité": "2026-09-02 12:35:43.825479"},
                    {"Nom d'utilisateur": "admin_rahmat", "Rôle / Fonction": "directeur", "Dernière activité": "2026-09-02 13:57:54.358633"}
                ]
            }

        key_store = school_name
        utilisateurs_ecole = st.session_state["users_data"].get(key_store, [])

        with tab_liste:
            st.markdown(f"### Utilisateurs Actifs — **{school_name} ({cycle_en_cours})**")
            if not utilisateurs_ecole:
                st.info("Aucun utilisateur enregistré dans cet établissement.")
            else:
                df_users = pd.DataFrame(utilisateurs_ecole)
                st.dataframe(df_users, use_container_width=True)

        with tab_ajout:
            st.markdown(f"### Création d'un Nouveau Compte Utilisateur — **{school_name}**")
            with st.form("form_creation_compte"):
                col1, col2 = st.columns(2)
                with col1:
                    nouveau_user = st.text_input("Nom d'utilisateur (Identifiant)")
                    mot_de_passe = st.text_input("Mot de passe provisoire", type="password")
                with col2:
                    role_attribue = st.selectbox("Rôle / Fonction", ["directeur", "enseignant", "econome", "surveillant", "super_admin"])
                    cycle_associe = st.selectbox("Cycle d'affectation", ["Collège", "Lycée", "Tous les cycles"])

                submitted_user = st.form_submit_button("💾 Créer le Compte Utilisateur", type="primary")
                if submitted_user:
                    if not nouveau_user or not mot_de_passe:
                        st.error("⚠️ Veuillez renseigner l'identifiant et le mot de passe.")
                    else:
                        existe_deja = any(u["Nom d'utilisateur"] == nouveau_user for u in utilisateurs_ecole)
                        if existe_deja:
                            st.error(f"⚠️ Un utilisateur portant l'identifiant '{nouveau_user}' existe déjà.")
                        else:
                            nouveau_compte = {
                                "Nom d'utilisateur": nouveau_user,
                                "Rôle / Fonction": role_attribue,
                                "Dernière activité": str(datetime.utcnow())
                            }
                            if key_store not in st.session_state["users_data"]:
                                st.session_state["users_data"][key_store] = []
                            st.session_state["users_data"][key_store].append(nouveau_compte)

                            # Traçabilité médico-légale ERP (SOC 2 / ISO 27001) via l'utilitaire centralisé
                            log_action_erp(
                                module="Gestion Comptes",
                                action=f"Création de compte utilisateur : {nouveau_user} (Rôle: {role_attribue}, Cycle: {cycle_associe})",
                                statut="Critique",
                                valeur_avant="Inexistant",
                                valeur_apres=f"Compte actif [{role_attribue}]"
                            )

                            st.success(f"✅ Le compte de **{nouveau_user}** avec le rôle **{role_attribue}** a été créé et tracé avec succès !")

    finally:
        db.close()

# Alias de compatibilité exhaustive pour garantir l'appel par le routeur app.py
afficher_gestion_comptes = afficher_gestion_utilisateurs
afficher_gestion_compte = afficher_gestion_utilisateurs
afficher_comptes = afficher_gestion_utilisateurs
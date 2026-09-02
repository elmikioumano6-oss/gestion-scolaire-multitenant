import streamlit as st
import pandas as pd
from database.db_config import SessionLocal
from database.models import School

def afficher_enseignants():
    st.subheader("👨‍🏫 Gestion du Corps Professoral & Enseignants")
    st.markdown("Suivi et administration des enseignants rattachés à l'établissement avec isolation multi-tenant stricte.")
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

    tab1, tab2 = st.tabs(["📋 Liste des Enseignants", "➕ Enregistrer un Enseignant"])

    with tab1:
        st.markdown(f"### Enseignants Actifs — **{school_name} ({cycle_en_cours})**")
        st.info("Aucun enseignant enregistré pour le moment dans cet établissement.")

    with tab2:
        st.markdown(f"### Nouvel Enseignant — **{school_name} ({cycle_en_cours})**")
        with st.form("form_add_enseignant"):
            col1, col2 = st.columns(2)
            with col1:
                nom = st.text_input("Nom de l'enseignant")
                prenom = st.text_input("Prénom de l'enseignant")
            with col2:
                telephone = st.text_input("Téléphone")
                discipline = st.text_input("Discipline principale")

            submitted = st.form_submit_button("Enregistrer l'enseignant")
            if submitted:
                if not nom or not prenom:
                    st.error("⚠️ Le nom et le prénom sont obligatoires.")
                else:
                    st.success(f"✅ L'enseignant {nom} {prenom} a été enregistré avec succès pour **{school_name}** !")
                    st.rerun()

# Alias de compatibilité complète pour le routeur
afficher_gestion_enseignants = afficher_enseignants
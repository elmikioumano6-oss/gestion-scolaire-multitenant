import streamlit as st
import os
from database.db_config import SessionLocal
from database.models import School

def afficher_parametres():
    st.subheader("⚙️ Paramètres & Configuration de l'Établissement")
    st.markdown("Personnalisation des informations institutionnelles et des paramètres spécifiques à l'établissement.")
    st.markdown("---")

    school_id = st.session_state.get("school_id")
    is_super_admin = st.session_state.get("is_super_admin", False)

    if not school_id and not is_super_admin:
        st.warning("⚠️ Veuillez vous connecter pour accéder à cette section.")
        return

    db = SessionLocal()
    try:
        target_id = school_id
        if is_super_admin and not target_id:
            ecoles = db.query(School).all()
            if not ecoles:
                st.warning("Aucune école enregistrée.")
                return
            choix_ecole = st.selectbox("Sélectionner l'établissement à configurer", options=[e.nom for e in ecoles])
            ecole_courante = next((e for e in ecoles if e.nom == choix_ecole), ecoles[0])
            target_id = ecole_courante.id
        else:
            ecole_courante = db.query(School).filter(School.id == target_id).first()

        if not ecole_courante:
            st.error("Établissement introuvable.")
            return

        with st.form("form_parametres_ecole"):
            st.markdown(f"### 🏫 Modification des informations : {ecole_courante.nom}")
            
            nouveau_nom = st.text_input("Nom de l'établissement", value=ecole_courante.nom)
            nouvelle_devise = st.text_input("Devise de l'établissement", value=ecole_courante.devise or "Excellence - Travail - Succès")
            nouvelle_adresse = st.text_input("Adresse / Quartier", value=getattr(ecole_courante, 'adresse', 'Quartier, Niamey - Niger'))
            nouveaux_contacts = st.text_input("Numéros de téléphone (séparés par des /)", value=getattr(ecole_courante, 'contacts', 'N/D'))

            submitted = st.form_submit_button("Enregistrer les modifications")
            if submitted:
                ecole_courante.nom = nouveau_nom.strip()
                ecole_courante.devise = nouvelle_devise.strip()
                ecole_courante.adresse = nouvelle_adresse.strip()
                ecole_courante.contacts = nouveaux_contacts.strip()
                
                db.commit()
                st.success("✅ Paramètres mis à jour avec succès !")
                st.rerun()

    finally:
        db.close()

# Alias de compatibilité complète pour le routeur
afficher_parametre = afficher_parametres
afficher_configuration = afficher_parametres
afficher_gestion_parametres = afficher_parametres
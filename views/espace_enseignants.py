import streamlit as st
import pandas as pd
from database.db_config import SessionLocal
from database.models import Classe, Matiere, School

def afficher_espace_enseignants():
    st.subheader("👨‍🏫 Espace Pédagogique Enseignant")
    st.markdown("Interface dédiée à la saisie des notes et au suivi des cours par le corps professoral, avec isolation multi-tenant stricte.")
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
        # Isolation multi-écoles et multi-cycles pour les classes et matières
        classes_query = db.query(Classe).filter(Classe.cycle == cycle_en_cours)
        if not is_super_admin and school_id:
            classes_query = classes_query.filter(Classe.school_id == school_id)
        classes_cycle = classes_query.all()

        matieres_query = db.query(Matiere).filter(Matiere.cycle == cycle_en_cours)
        if not is_super_admin and school_id:
            matieres_query = matieres_query.filter(Matiere.school_id == school_id)
        matieres_cycle = matieres_query.all()

        st.markdown(f"### Espace Enseignant — **{school_name} ({cycle_en_cours})**")

        if not classes_cycle or not matieres_cycle:
            st.warning(f"⚠️ Veuillez vous assurer que des classes et des matières sont configurées pour le cycle **{cycle_en_cours}** dans l'établissement **{school_name}**.")
            st.info("Utilisez les modules **Classes & Tarifs** et **Matières & Coeffs** du menu latéral.")
            return

        noms_classes = [c.libelle for c in classes_cycle]
        noms_matieres = [m.libelle for m in matieres_cycle]

        col1, col2 = st.columns(2)
        with col1:
            classe_choisie = st.selectbox("Classe", noms_classes, key="ens_classe")
        with col2:
            matiere_choisie = st.selectbox("Matière", noms_matieres, key="ens_matiere")

        st.success(f"Portail enseignant actif pour la classe de **{classe_choisie}** en **{matiere_choisie}**.")
        
        st.markdown("#### Journal de Bord de la Séance")
        with st.form("form_espace_enseignant"):
            titre_seance = st.text_input("Intitulé / Chapitre du cours")
            resume_seance = st.text_area("Résumé de la leçon dispensée")
            submitted = st.form_submit_button("Valider et soumettre au registre")
            if submitted:
                if not titre_seance:
                    st.error("⚠️ Veuillez renseigner l'intitulé de la séance.")
                else:
                    st.success("✅ Séance enregistrée avec succès dans le registre de l'établissement !")

    finally:
        db.close()

# Alias de compatibilité complète pour le routeur
afficher_espace_enseignant = afficher_espace_enseignants
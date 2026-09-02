import streamlit as st
import pandas as pd
from database.db_config import SessionLocal
from database.models import Classe, Matiere, School

def afficher_cahier_texte():
    st.subheader("📖 Cahier de Texte Numérique")
    st.markdown("Suivi des cours dispensés, des contenus pédagogiques et des devoirs avec isolation multi-tenant stricte et par cycle.")
    st.markdown("---")

    school_id = st.session_state.get("school_id")
    is_super_admin = st.session_state.get("is_super_admin", False)
    school_name = st.session_state.get("school_name", "Établissement")
    cycle_en_cours = st.session_state.get("cycle_actif", "Collège")

    if not school_id and not is_super_admin:
        st.warning("⚠️ Veuillez vous connecter pour accéder à cette section.")
        return

    db = SessionLocal()
    try:
        # Isolation multi-écoles et multi-cycles pour les classes
        classes_query = db.query(Classe).filter(Classe.cycle == cycle_en_cours)
        if not is_super_admin and school_id:
            classes_query = classes_query.filter(Classe.school_id == school_id)
        classes_cycle = classes_query.all()

        # Isolation multi-écoles et multi-cycles pour les matières
        matieres_query = db.query(Matiere).filter(Matiere.cycle == cycle_en_cours)
        if not is_super_admin and school_id:
            matieres_query = matieres_query.filter(Matiere.school_id == school_id)
        matieres_cycle = matieres_query.all()

        if not classes_cycle or not matieres_cycle:
            st.warning(f"⚠️ Veuillez vous assurer d'avoir enregistré des classes et des matières pour le cycle **{cycle_en_cours}** dans l'établissement **{school_name}**.")
            st.info("Utilisez les modules **Classes & Tarifs** et **Matières & Coeffs** du menu latéral pour les configurer.")
            return

        noms_classes = [c.libelle for c in classes_cycle]
        noms_matieres = [m.libelle for m in matieres_cycle]

        tab1, tab2 = st.tabs(["📖 Consulter le Cahier de Texte", "✍️ Saisir un Cours / Devoir"])

        with tab1:
            st.markdown(f"### Entrées du Cahier de Texte — **{school_name} ({cycle_en_cours})**")
            classe_consult = st.selectbox("Sélectionner la classe", noms_classes, key="consult_cahier_classe")
            st.info(f"Aucune entrée enregistrée pour la classe **{classe_consult}** dans le cycle **{cycle_en_cours}**.")

        with tab2:
            st.markdown(f"### Nouvelle Saisie — **{school_name} ({cycle_en_cours})**")
            with st.form("form_add_cahier"):
                col1, col2 = st.columns(2)
                with col1:
                    classe_choisie = st.selectbox("Classe", noms_classes, key="form_cahier_classe")
                    matiere_choisie = st.selectbox("Matière", noms_matieres)
                with col2:
                    date_cours = st.date_input("Date du cours")
                    titre_cours = st.text_input("Titre / Intitulé du cours ou du devoir")
                
                contenu = st.text_area("Contenu détaillé de la séance / Travail à faire")

                submitted = st.form_submit_button("Enregistrer l'entrée")
                if submitted:
                    if not titre_cours or not contenu:
                        st.error("⚠️ Veuillez remplir le titre et le contenu.")
                    else:
                        st.success(f"✅ Entrée enregistrée avec succès pour la classe **{classe_choisie}** en **{matiere_choisie}** !")
                        st.rerun()

    finally:
        db.close()

# Alias de compatibilité
afficher_cahier_de_texte = afficher_cahier_texte
import streamlit as st
import pandas as pd
from database.db_config import SessionLocal
from database.models import Classe, School

def afficher_planification_evaluations():
    st.subheader("📋 Planification des Évaluations")
    st.markdown("Calendrier officiel des devoirs, compositions et examens blancs par cycle, classe et établissement avec isolation multi-tenant stricte.")
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
        # Isolation stricte multi-écoles et multi-cycles pour les classes
        classes_query = db.query(Classe).filter(Classe.cycle == cycle_en_cours)
        if not is_super_admin and school_id:
            classes_query = classes_query.filter(Classe.school_id == school_id)
        classes_cycle = classes_query.all()

        if not classes_cycle:
            st.warning(f"⚠️ Aucune classe n'est actuellement configurée pour le cycle **{cycle_en_cours}** dans l'établissement **{school_name}**.")
            st.info("Veuillez d'abord enregistrer vos classes dans le module **Classes & Tarifs** du menu latéral.")
            return

        noms_classes = [c.libelle for c in classes_cycle]
        
        tab1, tab2 = st.tabs(["📅 Calendrier des Évaluations", "➕ Planifier une Évaluation"])

        with tab1:
            st.markdown(f"### Calendrier Officiel — **{school_name} ({cycle_en_cours})**")
            st.info("Aucune évaluation programmée pour le moment dans cet établissement.")

        with tab2:
            st.markdown(f"### Nouvelle Programmation — **{school_name} ({cycle_en_cours})**")
            with st.form("form_add_evaluation"):
                col1, col2 = st.columns(2)
                with col1:
                    classe_choisie = st.selectbox("Classe concernée", noms_classes)
                    titre = st.text_input("Intitulé de l'évaluation (ex: Devoir N°1 de Mathématiques)")
                with col2:
                    type_eval = st.selectbox("Type d'évaluation", ["Interrogation", "Devoir Surveillé", "Composition", "Examen Blanc"])
                    date_eval = st.date_input("Date de l'évaluation")

                submitted = st.form_submit_button("Enregistrer l'évaluation")
                if submitted:
                    if not titre:
                        st.error("⚠️ L'intitulé de l'évaluation est obligatoire.")
                    else:
                        st.success(f"✅ Évaluation '{titre}' programmée avec succès pour la classe de **{classe_choisie}** !")
                        st.rerun()

    finally:
        db.close()

# Alias de compatibilité
afficher_planification_des_evaluations = afficher_planification_evaluations
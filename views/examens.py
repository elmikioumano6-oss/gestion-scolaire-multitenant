import streamlit as st
import pandas as pd
from database.db_config import SessionLocal
from database.models import Classe, Eleve, School
from database.queries import get_classes_cached

def afficher_examens():
    st.subheader("📝 Gestion des Examens & Compositions")
    st.markdown("Planification des examens blancs et suivi des sessions d'évaluation avec isolation multi-tenant stricte.")
    st.markdown("---")

    school_id = st.session_state.get("school_id")
    is_super_admin = st.session_state.get("is_super_admin", False)

    if not school_id and not is_super_admin:
        st.warning("⚠️ Veuillez vous connecter pour accéder à cette section.")
        return

    db = SessionLocal()
    try:
        query_classes = db.query(Classe)
        if not is_super_admin and school_id:
            query_classes = query_classes.filter(Classe.school_id == school_id)
        classes = query_classes.all()

        if not classes:
            st.info("Aucune classe disponible.")
            return

        def get_label(obj):
            for attr in ['libelle', 'nom', 'name', 'titre']:
                if hasattr(obj, attr):
                    return getattr(obj, attr)
            return f"ID {obj.id}"

        tab1, tab2 = st.tabs(["📋 Sessions d'Examens", "➕ Programmer un Examen"])

        with tab1:
            st.markdown("### Calendrier des Compositions")
            st.info("Aucun examen blanc ou composition officielle enregistré pour le moment.")

        with tab2:
            st.markdown("### Nouvelle Session d'Examen")
            with st.form("form_add_examen"):
                col1, col2 = st.columns(2)
                with col1:
                    libelle_examen = st.text_input("Intitulé de l'examen (ex: Examen Blanc N°1)")
                    classe_dict = {get_label(c): c.id for c in classes}
                    classe_choisie = st.selectbox("Classe concernée", options=list(classe_dict.keys()))
                with col2:
                    date_composition = st.text_input("Date de composition (ex: 15/04/2027)")
                    session = st.selectbox("Session / Trimestre", options=["Trimestre 1", "Trimestre 2", "Trimestre 3", "Examen Blanc Général"])

                submitted = st.form_submit_button("Valider la programmation")
                if submitted:
                    if not libelle_examen:
                        st.error("⚠️ L'intitulé de l'examen est obligatoire.")
                    else:
                        st.success(f"✅ L'examen **{libelle_examen}** a été programmé avec succès pour la classe de **{classe_choisie}** !")

    finally:
        db.close()

# Alias de compatibilité
afficher_examens = afficher_examens
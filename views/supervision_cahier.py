import streamlit as st
import pandas as pd
from database.db_config import SessionLocal
from database.models import Classe, School

def afficher_supervision_cahier():
    st.subheader("📋 Contrôle d'Inspection Pédagogique & Registre Officiel")
    st.markdown("Portail officiel d'audit de l'avancement des programmes, du volume horaire et de la conformité des enseignements.")
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
        # Isolation stricte multi-écoles et multi-cycles pour les classes
        classes_query = db.query(Classe).filter(Classe.cycle == cycle_en_cours)
        if not is_super_admin and school_id:
            classes_query = classes_query.filter(Classe.school_id == school_id)
        classes_cycle = classes_query.all()

        st.markdown(f"### Supervision — **{school_name} ({cycle_en_cours})**")

        if not classes_cycle:
            st.warning(f"⚠️ Aucune classe enregistrée pour le cycle **{cycle_en_cours}** dans l'établissement **{school_name}**.")
            st.info("Veuillez d'abord enregistrer vos classes dans le module **Classes & Tarifs** du menu latéral.")
            return

        noms_classes = [c.libelle for c in classes_cycle]
        classe_suivie = st.selectbox("Sélectionner la classe à inspecter", noms_classes)
        
        st.info(f"Registre d'inspection actif pour la classe de **{classe_suivie}** à **{school_name}**.")
        
        # Tableau de suivi d'inspection vide ou rempli dynamiquement
        df_suivi = pd.DataFrame(columns=["Matière", "Enseignant", "Progression (%)", "Dernier Chapitre Visé", "Observation Inspecteur"], data=[
            ["—", "—", "0%", "—", "En attente de saisie"]
        ])
        st.dataframe(df_suivi, use_container_width=True)

    finally:
        db.close()

# Alias de compatibilité
afficher_supervision_cahier = afficher_supervision_cahier
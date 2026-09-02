import streamlit as st
import pandas as pd
from database.db_config import SessionLocal
from database.models import Classe, Matiere, School

def afficher_supervision_progression():
    st.subheader("📚 Pilotage, Suivi & Avancement des Programmes")
    st.markdown("Tableau de bord exécutif de la Direction des Études : analyse globale de la couverture des programmes officiels et des volumes horaires par discipline avec isolation multi-tenant stricte.")
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

        st.markdown(f"### Suivi des Programmes — **{school_name} ({cycle_en_cours})**")

        if not classes_cycle:
            st.warning(f"⚠️ Aucune classe disponible pour le cycle **{cycle_en_cours}** dans l'établissement **{school_name}**. Veuillez d'abord en créer dans le menu 'Classes & Tarifs'.")
            return

        noms_classes = [c.libelle for c in classes_cycle]
        classe_choisie = st.selectbox("Sélectionner la classe à auditer", noms_classes)

        st.success(f"Tableau de bord d'avancement des programmes actif pour la classe de **{classe_choisie}**.")
        
        if matieres_cycle:
            data_prog = []
            for m in matieres_cycle:
                data_prog.append({
                    "Discipline / Matière": getattr(m, 'libelle', 'Matière'),
                    "Coefficient": getattr(m, 'coefficient', 1),
                    "Progression Estimée": "0%",
                    "Statut": "Normal"
                })
            df_prog = pd.DataFrame(data_prog)
            st.dataframe(df_prog, use_container_width=True)
        else:
            st.info("Aucune matière enregistrée pour ce cycle. Utilisez le menu 'Matières & Coeffs' pour en ajouter.")

    finally:
        db.close()

# Alias de compatibilité complète pour le routeur
afficher_suivi_programmes = afficher_supervision_progression
afficher_suivi_des_programmes = afficher_supervision_progression
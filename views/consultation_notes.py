import streamlit as st
import pandas as pd
from database.db_config import SessionLocal
from database.models import Classe, Eleve, School

def afficher_consultation_notes():
    st.subheader("📊 Consultation Détaillée des Notes")
    st.markdown("Recherche et affichage des notes par élève et par classe avec isolation multi-tenant stricte et par cycle.")
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
        # Isolation multi-écoles et multi-cycles pour les classes
        classes_query = db.query(Classe).filter(Classe.cycle == cycle_en_cours)
        if not is_super_admin and school_id:
            classes_query = classes_query.filter(Classe.school_id == school_id)
        classes_cycle = classes_query.all()

        st.markdown(f"### Consultation des Notes — **{school_name} ({cycle_en_cours})**")

        if not classes_cycle:
            st.warning(f"⚠️ Aucune classe disponible pour le cycle **{cycle_en_cours}** dans l'établissement **{school_name}**.")
            st.info("Veuillez d'abord enregistrer vos classes dans le module **Classes & Tarifs** du menu latéral.")
            return

        noms_classes = [c.libelle for c in classes_cycle]
        classe_choisie = st.selectbox("Sélectionner la classe à consulter", noms_classes)

        classe_obj = next((c for c in classes_cycle if c.libelle == classe_choisie), None)
        if classe_obj:
            eleves_query = db.query(Eleve).filter(Eleve.classe_id == classe_obj.id)
            if not is_super_admin and school_id:
                eleves_query = eleves_query.filter(Eleve.school_id == school_id)
            eleves = eleves_query.all()

            if not eleves:
                st.info(f"Aucun élève enregistré dans la classe **{classe_choisie}**.")
            else:
                st.success(f"Résultats affichés pour la classe de **{classe_choisie}** ({len(eleves)} élèves).")
                
                data_consult = []
                for e in eleves:
                    data_consult.append({
                        "Nom & Prénom": f"{e.nom} {e.prenom}",
                        "Matricule": getattr(e, 'matricule', 'N/D'),
                        "Moyenne Trimestrielle": "—",
                        "Rang": "—",
                        "Mention": "—"
                    })
                df_consult = pd.DataFrame(data_consult)
                st.dataframe(df_consult, use_container_width=True)

    finally:
        db.close()

# Alias de compatibilité complète pour le routeur
afficher_consultations_notes = afficher_consultation_notes
afficher_consultation_des_notes = afficher_consultation_notes
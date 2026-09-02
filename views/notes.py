import streamlit as st
import pandas as pd
from datetime import datetime
from database.db_config import SessionLocal
from database.models import Classe, Matiere, Eleve, School, ActivityLog

def afficher_notes():
    st.subheader("📝 Saisie des Notes & Évaluations")
    st.markdown("Interface dédiée à l'enregistrement et au suivi des notes par classe et par matière avec isolation multi-tenant stricte.")
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
        classes_query = db.query(Classe).filter(Classe.cycle == cycle_en_cours)
        if not is_super_admin and school_id:
            classes_query = classes_query.filter(Classe.school_id == school_id)
        classes_cycle = classes_query.all()

        matieres_query = db.query(Matiere).filter(Matiere.cycle == cycle_en_cours)
        if not is_super_admin and school_id:
            matieres_query = matieres_query.filter(Matiere.school_id == school_id)
        matieres_cycle = matieres_query.all()

        st.markdown(f"### Saisie des Notes — **{school_name} ({cycle_en_cours})**")

        if not classes_cycle or not matieres_cycle:
            st.warning(f"⚠️ Veuillez vous assurer que des classes et des matières sont configurées pour le cycle **{cycle_en_cours}** dans l'établissement **{school_name}**.")
            return

        noms_classes = [c.libelle for c in classes_cycle]
        noms_matieres = [m.libelle for m in matieres_cycle]

        col1, col2 = st.columns(2)
        with col1:
            classe_choisie = st.selectbox("Classe", noms_classes, key="notes_classe")
        with col2:
            matiere_choisie = st.selectbox("Matière", noms_matieres, key="notes_matiere")

        # Initialisation du stockage des notes en session state
        if "notes_evaluation_data" not in st.session_state:
            st.session_state["notes_evaluation_data"] = {}

        key_notes_store = f"{school_id}_{cycle_en_cours}_{classe_choisie}_{matiere_choisie}"
        notes_enregistrees = st.session_state["notes_evaluation_data"].get(key_notes_store, {})

        classe_obj = next((c for c in classes_cycle if c.libelle == classe_choisie), None)
        if classe_obj:
            eleves_query = db.query(Eleve).filter(Eleve.classe_id == classe_obj.id)
            if not is_super_admin and school_id:
                eleves_query = eleves_query.filter(Eleve.school_id == school_id)
            eleves = eleves_query.all()

            if not eleves:
                st.info(f"Aucun élève enregistré dans la classe **{classe_choisie}**.")
            else:
                st.success(f"Saisie active pour **{classe_choisie}** en **{matiere_choisie}** ({len(eleves)} élèves).")
                
                with st.form("form_saisie_notes"):
                    saisie_temporaire = {}
                    for e in eleves:
                        val_actuelle = notes_enregistrees.get(e.id, 0.0)
                        saisie_temporaire[e.id] = st.number_input(
                            f"Note pour {e.nom} {e.prenom} (sur 20)",
                            min_value=0.0,
                            max_value=20.0,
                            value=float(val_actuelle),
                            step=0.25,
                            key=f"note_eleve_{e.id}"
                        )
                    
                    submitted = st.form_submit_button("Enregistrer les notes")
                    if submitted:
                        target_school_id = school_id or 1
                        
                        # Sauvegarde dans le session state
                        st.session_state["notes_evaluation_data"][key_notes_store] = saisie_temporaire

                        # Traçabilité dans le journal d'activité
                        nouveau_log = ActivityLog(
                            school_id=target_school_id,
                            timestamp=datetime.utcnow(),
                            username=st.session_state.get("username", "admin"),
                            action=f"Enregistrement notes : {matiere_choisie} ({classe_choisie})",
                            module="Saisie des notes",
                            statut="Succès"
                        )
                        db.add(nouveau_log)
                        db.commit()

                        st.success("✅ Notes enregistrées et consignées avec succès pour cette évaluation !")
                        st.rerun()

    finally:
        db.close()

# Alias de compatibilité complète pour le routeur
afficher_saisie_notes = afficher_notes
afficher_gestion_notes = afficher_notes
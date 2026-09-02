import streamlit as st
import pandas as pd
from datetime import datetime
from database.db_config import SessionLocal
from database.models import Classe, Eleve, School, ActivityLog

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
                
                # Récupération des notes enregistrées en session pour les évaluer
                notes_store = st.session_state.get("notes_evaluation_data", {})

                data_consult = []
                for e in eleves:
                    # Recherche de toutes les notes de cet élève à travers les matières stockées
                    notes_eleve = []
                    for key, evaluations in notes_store.items():
                        if f"_{classe_choisie}_" in key or str(school_id) in key:
                            if e.id in evaluations:
                                notes_eleve.append(evaluations[e.id])

                    moyenne = round(sum(notes_eleve) / len(notes_eleve), 2) if notes_eleve else "—"
                    
                    # Attribution d'une mention indicative si une moyenne existe
                    mention = "—"
                    if isinstance(moyenne, (int, float)):
                        if moyenne >= 16:
                            mention = "Très Bien"
                        elif moyenne >= 14:
                            mention = "Bien"
                        elif moyenne >= 12:
                            mention = "Assez Bien"
                        elif moyenne >= 10:
                            mention = "Passable"
                        else:
                            mention = "Insuffisant"

                    data_consult.append({
                        "Nom & Prénom": f"{e.nom} {e.prenom}",
                        "Matricule": getattr(e, 'matricule', 'N/D'),
                        "Moyenne Trimestrielle": moyenne,
                        "Rang": "En attente",
                        "Mention": mention
                    })

                df_consult = pd.DataFrame(data_consult)
                st.dataframe(df_consult, use_container_width=True)

                # Traçabilité dans le journal d'activité
                target_school_id = school_id or 1
                nouveau_log = ActivityLog(
                    school_id=target_school_id,
                    timestamp=datetime.utcnow(),
                    username=st.session_state.get("username", "admin"),
                    action=f"Consultation des notes - Classe {classe_choisie}",
                    module="Consultation des notes",
                    statut="Succès"
                )
                db.add(nouveau_log)
                db.commit()

    finally:
        db.close()

# Alias de compatibilité complète pour le routeur
afficher_consultations_notes = afficher_consultation_notes
afficher_consultation_des_notes = afficher_consultation_notes
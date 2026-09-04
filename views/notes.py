import streamlit as st
import pandas as pd
from datetime import datetime
from database.db_config import SessionLocal
from database.models import Classe, Matiere, Eleve, Note, School, ActivityLog
from database.audit import log_action_erp

def afficher_notes():
    st.subheader("📝 Saisie Globale des Notes (Mode Grille Matricielle)")
    st.markdown("Interface matricielle : les élèves en lignes, les matières en colonnes, avec sélection de la période et du type d'évaluation (incluant Compo 1 et Compo 2) pour une persistance directe en base de données.")
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
        target_school_id = school_id
        if is_super_admin and not target_school_id:
            ecole_defaut = db.query(School).first()
            target_school_id = ecole_defaut.id if ecole_defaut else 1

        classes_query = db.query(Classe).filter(Classe.cycle == cycle_en_cours, Classe.deleted_at.is_(None))
        if not is_super_admin and school_id:
            classes_query = classes_query.filter(Classe.school_id == school_id)
        else:
            classes_query = classes_query.filter(Classe.school_id == target_school_id)
        classes_cycle = classes_query.all()

        matieres_query = db.query(Matiere).filter(Matiere.cycle == cycle_en_cours)
        if not is_super_admin and school_id:
            matieres_query = matieres_query.filter(Matiere.school_id == school_id)
        else:
            matieres_query = matieres_query.filter(Matiere.school_id == target_school_id)
        matieres_cycle = matieres_query.all()

        st.markdown(f"### Saisie Matricielle des Notes — **{school_name} ({cycle_en_cours})**")

        if not classes_cycle or not matieres_cycle:
            st.warning(f"⚠️ Veuillez vous assurer que des classes et des matières sont configurées pour le cycle **{cycle_en_cours}** dans l'établissement **{school_name}**.")
            return

        noms_classes = [c.libelle for c in classes_cycle]

        # Filtres globaux de la grille avec Compo 1 et Compo 2 ajoutés
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            classe_choisie = st.selectbox("Classe", noms_classes, key="notes_classe_matrix")
        with col_f2:
            semestre_choisi = st.selectbox("Période / Semestre", ["Semestre 1", "Semestre 2", "Trimestre 1", "Trimestre 2", "Trimestre 3"], key="notes_semestre_matrix")
        with col_f3:
            type_eval = st.selectbox("Type d'évaluation", ["Interro 1", "Interro 2", "Devoir 1", "Devoir 2", "Compo 1", "Compo 2"], key="notes_type_eval_matrix")

        classe_obj = next((c for c in classes_cycle if c.libelle == classe_choisie), None)
        if classe_obj:
            eleves_query = db.query(Eleve).filter(Eleve.classe_id == classe_obj.id, Eleve.deleted_at.is_(None))
            if not is_super_admin and school_id:
                eleves_query = eleves_query.filter(Eleve.school_id == school_id)
            else:
                eleves_query = eleves_query.filter(Eleve.school_id == target_school_id)
            eleves = eleves_query.order_by(Eleve.nom).all()

            if not eleves:
                st.info(f"Aucun élève enregistré dans la classe **{classe_choisie}**.")
            else:
                st.success(f"Grille active pour **{classe_choisie}** | **{semestre_choisi}** | **{type_eval}** ({len(eleves)} élèves, {len(matieres_cycle)} matières).")

                # Récupération des notes existantes en base de données pour cette configuration
                notes_existantes = db.query(Note).join(Eleve).filter(
                    Note.school_id == target_school_id,
                    Eleve.classe_id == classe_obj.id,
                    Note.semestre == semestre_choisi,
                    Note.type_evaluation == type_eval
                ).all()

                dict_notes = {(n.eleve_id, n.matiere_id): n.valeur for n in notes_existantes}

                # Construction du tableau matriciel (élèves en lignes, matières en colonnes)
                data_matrice = []
                for e in eleves:
                    ligne = {
                        "eleve_id": e.id,
                        "Matricule": e.matricule,
                        "Nom & Prénom": f"{e.nom} {e.prenom}"
                    }
                    for mat in matieres_cycle:
                        ligne[mat.libelle] = float(dict_notes.get((e.id, mat.id), 0.0))
                    data_matrice.append(ligne)

                df_matrice = pd.DataFrame(data_matrice)

                column_config = {
                    "eleve_id": None,
                    "Matricule": st.column_config.TextColumn("Matricule", disabled=True),
                    "Nom & Prénom": st.column_config.TextColumn("Nom & Prénom", disabled=True),
                }
                for mat in matieres_cycle:
                    column_config[mat.libelle] = st.column_config.NumberColumn(
                        mat.libelle,
                        min_value=0.0,
                        max_value=20.0,
                        step=0.25,
                        format="%.2f"
                    )

                edited_df = st.data_editor(
                    df_matrice,
                    column_config=column_config,
                    hide_index=True,
                    use_container_width=True,
                    key=f"editor_matrix_{classe_choisie}_{semestre_choisi}_{type_eval}"
                )

                if st.button("💾 Enregistrer toutes les notes de la classe", type="primary"):
                    modifications_count = 0
                    for _, row in edited_df.iterrows():
                        eleve_id = row["eleve_id"]
                        nom_eleve = row["Nom & Prénom"]
                        for mat in matieres_cycle:
                            valeur_saisie = float(row[mat.libelle])
                            ancienne_valeur = dict_notes.get((eleve_id, mat.id), 0.0)

                            if ancienne_valeur != valeur_saisie:
                                note_obj = db.query(Note).filter(
                                    Note.school_id == target_school_id,
                                    Note.eleve_id == eleve_id,
                                    Note.matiere_id == mat.id,
                                    Note.semestre == semestre_choisi,
                                    Note.type_evaluation == type_eval
                                ).first()

                                if note_obj:
                                    note_obj.valeur = valeur_saisie
                                    action_desc = f"Modification de note ({type_eval} - {mat.libelle}) pour {nom_eleve}"
                                    statut_log = "Critique"
                                else:
                                    note_obj = Note(
                                        school_id=target_school_id,
                                        eleve_id=eleve_id,
                                        matiere_id=mat.id,
                                        valeur=valeur_saisie,
                                        semestre=semestre_choisi,
                                        type_evaluation=type_eval
                                    )
                                    db.add(note_obj)
                                    action_desc = f"Attribution de note ({type_eval} - {mat.libelle}) à {nom_eleve}"
                                    statut_log = "Succès"

                                modifications_count += 1

                                # Traçabilité médico-légale granulaire ERP (SOC 2 / ISO 27001)
                                log_action_erp(
                                    module="Saisie des notes",
                                    action=action_desc,
                                    statut=statut_log,
                                    valeur_avant=f"{ancienne_valeur} / 20",
                                    valeur_apres=f"{valeur_saisie} / 20"
                                )

                    db.commit()

                    st.success(f"✅ Enregistrement réussi ! {modifications_count} modification(s) tracée(s) avec le Diff Avant/Après dans l'ERP.")
                    st.rerun()

    finally:
        db.close()

# Alias de compatibilité complète pour le routeur
afficher_saisie_notes = afficher_notes
afficher_gestion_notes = afficher_notes
afficher_notes = afficher_notes
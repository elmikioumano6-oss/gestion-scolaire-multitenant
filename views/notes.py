from datetime import datetime
from database.audit import log_action_erp
from database.db_config import SessionLocal
from database.models import ActivityLog, Classe, Eleve, Matiere, Note, School
import pandas as pd
import streamlit as st
import unicodedata

SYNONYMES_MATIERES = {
    "sciences physiques": "physique chimie",
    "physique chimie": "physique chimie",
    "svt": "science de la vie et de la terre",
    "science de la vie et de la terre": "science de la vie et de la terre",
    "eps": "education physique et sportive",
    "education physique et sportive": "education physique et sportive",
    "economie familiale": "economie familiale et sociale",
    "economie familiale et sociale": "economie familiale et sociale",
    "histoire geographie": "histoire geographie",
    "histoire-geographie": "histoire geographie",
}

def normaliser_chaine(texte):
    if not texte or pd.isna(texte):
        return ""
    nfkd = unicodedata.normalize("NFKD", str(texte))
    sans_accent = "".join([c for c in nfkd if not unicodedata.combining(c)])
    nettoye = " ".join(sans_accent.lower().replace("-", " ").replace("_", " ").split())
    return SYNONYMES_MATIERES.get(nettoye, nettoye)

def afficher_notes():
    st.markdown("""
        <style>
            .main .block-container {
                max-width: 100% !important;
                padding-left: 1rem;
                padding-right: 1rem;
            }
        </style>
    """, unsafe_allow_html=True)

    st.subheader("📝 Saisie Globale des Notes (Mode Grille Matricielle)")
    st.markdown("Interface matricielle : les élèves en lignes, les matières en colonnes unifiées.")
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

        resolved_school_id = school_id if school_id else target_school_id

        classes_query = db.query(Classe).filter(Classe.cycle == cycle_en_cours, Classe.deleted_at.is_(None))

        if not is_super_admin and school_id:
            classes_query = classes_query.filter(Classe.school_id == school_id)
        else:
            classes_query = classes_query.filter(Classe.school_id == target_school_id)

        classes_cycle = classes_query.all()

        st.markdown(f"### Saisie Matricielle des Notes — **{school_name} ({cycle_en_cours})**")

        if not classes_cycle:
            st.warning(f"⚠️ Veuillez configurer des classes pour le cycle **{cycle_en_cours}**.")
            return

        noms_classes = [c.libelle for c in classes_cycle]
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            classe_choisie = st.selectbox("Classe", noms_classes, key="notes_classe_matrix")
        with col_f2:
            semestre_choisi = st.selectbox("Période / Semestre", ["Semestre 1", "Semestre 2", "Trimestre 1", "Trimestre 2", "Trimestre 3"], key="notes_semestre_matrix")
        with col_f3:
            type_eval = st.selectbox("Type d'évaluation", ["Interro 1", "Interro 2", "Devoir 1", "Devoir 2", "Compo"], key="notes_type_eval_matrix")

        classe_obj = next((c for c in classes_cycle if c.libelle == classe_choisie), None)
        if classe_obj:
            matieres_query = db.query(Matiere).filter(
                Matiere.classe_id == classe_obj.id,
                Matiere.school_id == resolved_school_id
            )
            if hasattr(Matiere, "deleted_at"):
                matieres_query = matieres_query.filter(Matiere.deleted_at.is_(None))
            matieres_classe = matieres_query.all()

            eleves_query = db.query(Eleve).filter(Eleve.classe_id == classe_obj.id, Eleve.deleted_at.is_(None))
            if not is_super_admin and school_id:
                eleves_query = eleves_query.filter(Eleve.school_id == school_id)
            else:
                eleves_query = eleves_query.filter(Eleve.school_id == target_school_id)
            eleves = eleves_query.order_by(Eleve.nom).all()

            if not matieres_classe:
                st.warning(f"Aucune matière configurée pour la classe de **{classe_choisie}**.")
            elif not eleves:
                st.info(f"Aucun élève enregistré dans la classe de **{classe_choisie}**.")
            else:
                st.success(f"Grille active pour **{classe_choisie}** | **{semestre_choisi}** | **{type_eval}** ({len(eleves)} élèves).")

                # Récupération sécurisée des notes existantes
                notes_existantes = db.query(Note).join(Eleve).filter(
                    Note.school_id == target_school_id,
                    Eleve.classe_id == classe_obj.id,
                    Note.semestre == semestre_choisi,
                    Note.type_evaluation == type_eval,
                ).all()

                dict_notes = {(n.eleve_id, n.matiere_id): float(n.valeur) if n.valeur is not None else 0.0 for n in notes_existantes}

                map_libelle_matiere = {}
                for mat in matieres_classe:
                    mat_lib = (mat.libelle if hasattr(mat, 'libelle') and mat.libelle else getattr(mat, 'nom', '')).title()
                    map_libelle_matiere[mat_lib] = mat.id

                data_matrice = []
                for e in eleves:
                    ligne = {"eleve_id": e.id, "Matricule": e.matricule, "Nom & Prénom": f"{e.nom} {e.prenom}"}
                    for mat_lib, mat_id in map_libelle_matiere.items():
                        val_note = dict_notes.get((e.id, mat_id), 0.0)
                        ligne[mat_lib] = val_note
                    data_matrice.append(ligne)

                df_matrice = pd.DataFrame(data_matrice)
                column_config = {
                    "eleve_id": None,
                    "Matricule": st.column_config.TextColumn("Matricule", disabled=True),
                    "Nom & Prénom": st.column_config.TextColumn("Nom & Prénom", disabled=True),
                }
                for mat_lib in map_libelle_matiere.keys():
                    max_val = 18.0 if "conduite" in mat_lib.lower() else 20.0
                    column_config[mat_lib] = st.column_config.NumberColumn(mat_lib, min_value=0.0, max_value=max_val, step=0.25, format="%.2f")

                editor_key = f"editor_matrix_{classe_obj.id}_{semestre_choisi}_{type_eval}"
                
                # --- UTILISATION D'UN FORMULAIRE STREAMLIT POUR GARANTIR LA SYNRONISATION ---
                with st.form(key=f"form_notes_{classe_obj.id}_{semestre_choisi}_{type_eval}"):
                    edited_df = st.data_editor(df_matrice, column_config=column_config, hide_index=True, use_container_width=True, key=editor_key)
                    submitted = st.form_submit_button("💾 Enregistrer toutes les notes de la classe", type="primary")

                if submitted:
                    modifications_count = 0
                    try:
                        for _, row in edited_df.iterrows():
                            eleve_id = int(row["eleve_id"])
                            nom_eleve = row["Nom & Prénom"]
                            
                            for mat_lib, mat_id in map_libelle_matiere.items():
                                valeur_saisie = float(row[mat_lib]) if pd.notna(row[mat_lib]) else 0.0
                                ancienne_valeur = dict_notes.get((eleve_id, mat_id), 0.0)

                                # On persiste si la note est modifiée ou si elle possède une valeur significative (> 0)
                                if ancienne_valeur != valeur_saisie or valeur_saisie > 0.0:
                                    note_obj = db.query(Note).filter(
                                        Note.school_id == target_school_id,
                                        Note.eleve_id == eleve_id,
                                        Note.matiere_id == mat_id,
                                        Note.semestre == semestre_choisi,
                                        Note.type_evaluation == type_eval,
                                    ).first()

                                    if note_obj:
                                        note_obj.valeur = valeur_saisie
                                        action_desc = f"Modification de note ({type_eval} - {mat_lib}) pour {nom_eleve}"
                                        statut_log = "Critique"
                                    else:
                                        note_obj = Note(
                                            school_id=target_school_id,
                                            eleve_id=eleve_id,
                                            matiere_id=mat_id,
                                            valeur=valeur_saisie,
                                            semestre=semestre_choisi,
                                            type_evaluation=type_eval,
                                        )
                                        db.add(note_obj)
                                        action_desc = f"Attribution de note ({type_eval} - {mat_lib}) à {nom_eleve}"
                                        statut_log = "Succès"

                                    modifications_count += 1
                                    try:
                                        log_action_erp(module="Saisie des notes", action=action_desc, statut=statut_log, valeur_avant=f"{ancienne_valeur} / 20", valeur_apres=f"{valeur_saisie} / 20")
                                    except Exception:
                                        pass

                        db.commit()
                        st.success(f"✅ Enregistrement réussi ! {modifications_count} valeur(s) enregistrée(s) en base de données.")
                        st.balloons()
                    except Exception as e:
                        db.rollback()
                        st.error(f"❌ Erreur critique lors de l'enregistrement : {e}")

    finally:
        db.close()

# Expositions de compatibilité pour le routeur
afficher_saisie_notes = afficher_notes
afficher_gestion_notes = afficher_notes
afficher_notes = afficher_notes
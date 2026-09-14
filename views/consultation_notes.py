from datetime import datetime
from io import BytesIO
from database.db_config import SessionLocal
from database.models import ActivityLog, Classe, Eleve, Matiere, Note, School
from database.queries import get_classes_cached, get_matieres_cached
import pandas as pd
import streamlit as st


def afficher_consultation_notes():
    st.subheader("📊 Consultation Détaillée des Notes & Résultats")
    st.markdown(
        "Recherche et affichage dynamique des notes par évaluation, ou des"
        " moyennes par semestre et annuelle avec isolation multi-tenant et"
        " persistance en base de données."
    )
    st.markdown("---")

    school_id = st.session_state.get("school_id")
    is_super_admin = st.session_state.get("is_super_admin", False)

    db = SessionLocal()
    try:
        if school_id:
            ecole_courante = (
                db.query(School).filter(School.id == school_id).first()
            )
            school_name = (
                ecole_courante.nom
                if ecole_courante
                else st.session_state.get("school_name", "Établissement")
            )
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

        # Isolation multi-écoles et multi-cycles pour les classes et matières
        classes_query = db.query(Classe).filter(Classe.cycle == cycle_en_cours)
        matieres_query = db.query(Matiere).filter(Matiere.cycle == cycle_en_cours)

        if not is_super_admin and school_id:
            classes_query = classes_query.filter(Classe.school_id == school_id)
            matieres_query = matieres_query.filter(Matiere.school_id == school_id)
        else:
            classes_query = classes_query.filter(
                Classe.school_id == target_school_id
            )
            matieres_query = matieres_query.filter(
                Matiere.school_id == target_school_id
            )

        classes_cycle = classes_query.all()
        matieres_cycle = matieres_query.all()

        st.markdown(
            f"### Consultation des Notes — **{school_name} ({cycle_en_cours})**"
        )

        if not classes_cycle:
            st.warning(
                f"⚠️ Aucune classe disponible pour le cycle **{cycle_en_cours}** dans"
                f" l'établissement **{school_name}**."
            )
            st.info(
                "Veuillez d'abord enregistrer vos classes dans le module **Classes &"
                " Tarifs** du menu latéral."
            )
            return

        noms_classes = [c.libelle for c in classes_cycle]

        # --- FILTRES DE CONSULTATION (Compo unique par semestre) ---
        col_c1, col_c2, col_c3 = st.columns(3)
        with col_c1:
            classe_choisie = st.selectbox(
                "Sélectionner la classe", noms_classes, key="consult_notes_classe"
            )
        with col_c2:
            semestre_choisi = st.selectbox(
                "Semestre / Période",
                [
                    "Semestre 1",
                    "Semestre 2",
                    "Trimestre 1",
                    "Trimestre 2",
                    "Trimestre 3",
                ],
                key="consult_notes_semestre",
            )
        with col_c3:
            type_vue = st.selectbox(
                "Type d'affichage / Évaluation",
                [
                    "Interro 1",
                    "Interro 2",
                    "Devoir 1",
                    "Devoir 2",
                    "Compo",
                    "Moyen-S1",
                    "Moyen-S2",
                    "Moyen-an",
                ],
                key="consult_notes_vue",
            )

        classe_obj = next(
            (c for c in classes_cycle if c.libelle == classe_choisie), None
        )
        if classe_obj:
            eleves_query = db.query(Eleve).filter(Eleve.classe_id == classe_obj.id)
            if not is_super_admin and school_id:
                eleves_query = eleves_query.filter(Eleve.school_id == school_id)
            else:
                eleves_query = eleves_query.filter(
                    Eleve.school_id == target_school_id
                )
            eleves = eleves_query.order_by(Eleve.nom).all()

            if not eleves:
                st.info(
                    f"Aucun élève enregistré dans la classe de **{classe_choisie}**."
                )
            else:
                st.success(
                    f"Résultats affichés pour la classe de **{classe_choisie}** — Vue"
                    f" : **{type_vue}** ({semestre_choisi}) [{len(eleves)} élèves]."
                )

                # --- 1. AFFICHAGE DES NOTES PAR ÉVALUATION (Matrice Élèves x Matières) ---
                if type_vue in [
                    "Interro 1",
                    "Interro 2",
                    "Devoir 1",
                    "Devoir 2",
                    "Compo",
                ]:
                    notes_db = (
                        db.query(Note)
                        .join(Eleve)
                        .filter(
                            Note.school_id == target_school_id,
                            Eleve.classe_id == classe_obj.id,
                            Note.semestre == semestre_choisi,
                            Note.type_evaluation == type_vue,
                        )
                        .all()
                    )

                    dict_notes = {
                        (n.eleve_id, n.matiere_id): n.valeur for n in notes_db
                    }

                    data_tableau = []
                    for e in eleves:
                        ligne = {
                            "Matricule": e.matricule,
                            "Nom & Prénom": f"{e.nom} {e.prenom}",
                        }
                        for mat in matieres_cycle:
                            mat_lib = mat.libelle if hasattr(mat, 'libelle') else getattr(mat, 'nom', '')
                            ligne[mat_lib] = dict_notes.get((e.id, mat.id), "—")
                        data_tableau.append(ligne)

                    df_res = pd.DataFrame(data_tableau)
                    st.dataframe(df_res, use_container_width=True)

                    # --- STATISTIQUES ET SYNTHÈSE PÉDAGOGIQUE ---
                    st.markdown("### 📈 Indicateurs & Synthèse Pédagogique")

                    stats_matieres = []
                    for mat in matieres_cycle:
                        mat_lib = mat.libelle if hasattr(mat, 'libelle') else getattr(mat, 'nom', '')
                        notes_mat = [
                            dict_notes.get((e.id, mat.id))
                            for e in eleves
                            if isinstance(dict_notes.get((e.id, mat.id)), (int, float))
                        ]
                        if notes_mat:
                            moy_mat = round(sum(notes_mat) / len(notes_mat), 2)
                            max_mat = max(notes_mat)
                            min_mat = min(notes_mat)
                        else:
                            moy_mat, max_mat, min_mat = "—", "—", "—"

                        stats_matieres.append({
                            "Matière": mat_lib,
                            "Moyenne de classe": moy_mat,
                            "Note Max": max_mat,
                            "Note Min": min_mat,
                        })

                    df_stats = pd.DataFrame(stats_matieres)
                    st.dataframe(df_stats, use_container_width=True)

                    # Bouton d'export officiel CSV
                    st.download_button(
                        label="📥 Télécharger le récapitulatif d'évaluation (CSV)",
                        data=df_res.to_csv(index=False).encode("utf-8"),
                        file_name=(
                            f"consultation_notes_{classe_choisie}_{type_vue}_"
                            f"{semestre_choisi.replace(' ', '')}.csv"
                        ),
                        mime="text/csv",
                    )

                # --- 2. AFFICHAGE DES MOYENNES (Moyen-S1, Moyen-S2, Moyen-an) ---
                else:
                    if type_vue == "Moyen-S1":
                        semestres_cibles = ["Semestre 1", "Trimestre 1", "Trimestre 2"]
                    elif type_vue == "Moyen-S2":
                        semestres_cibles = ["Semestre 2", "Trimestre 3"]
                    else:
                        semestres_cibles = None

                    query_notes = (
                        db.query(Note)
                        .join(Eleve)
                        .filter(
                            Note.school_id == target_school_id,
                            Eleve.classe_id == classe_obj.id,
                        )
                    )
                    if semestres_cibles:
                        query_notes = query_notes.filter(
                            Note.semestre.in_(semestres_cibles)
                        )

                    toutes_notes = query_notes.all()

                    stats_eleves = {}
                    for e in eleves:
                        stats_eleves[e.id] = {
                            "total_points": 0.0,
                            "total_coeffs": 0.0,
                            "nb_notes": 0,
                        }

                    dict_coeffs = {m.id: m.coefficient for m in matieres_cycle}

                    for n in toutes_notes:
                        if n.eleve_id in stats_eleves:
                            coeff = dict_coeffs.get(n.matiere_id, 1.0)
                            stats_eleves[n.eleve_id]["total_points"] += n.valeur * coeff
                            stats_eleves[n.eleve_id]["total_coeffs"] += coeff
                            stats_eleves[n.eleve_id]["nb_notes"] += 1

                    data_moyennes = []
                    for e in eleves:
                        st_el = stats_eleves[e.id]
                        if st_el["total_coeffs"] > 0:
                            moyenne = round(
                                st_el["total_points"] / st_el["total_coeffs"], 2
                            )
                        else:
                            moyenne = None

                        data_moyennes.append({
                            "eleve_id": e.id,
                            "Matricule": e.matricule,
                            "Nom & Prénom": f"{e.nom} {e.prenom}",
                            "Moyenne": moyenne,
                        })

                    data_moyennes.sort(
                        key=lambda x: x["Moyenne"] if x["Moyenne"] is not None else -1.0,
                        reverse=True,
                    )

                    tableau_final = []
                    for idx, item in enumerate(data_moyennes):
                        moy_val = item["Moyenne"]
                        moy_str = f"{moy_val:.2f}/20" if moy_val is not None else "—"
                        rang = f"{idx + 1}e" if moy_val is not None else "En attente"

                        if moy_val is not None:
                            if moy_val >= 16:
                                mention = "Très Bien"
                            elif moy_val >= 14:
                                mention = "Bien"
                            elif moy_val >= 12:
                                mention = "Assez Bien"
                            elif moy_val >= 10:
                                mention = "Passable"
                            else:
                                mention = "Insuffisant"
                        else:
                            mention = "—"

                        tableau_final.append({
                            "Rang": rang,
                            "Matricule": item["Matricule"],
                            "Nom & Prénom": item["Nom & Prénom"],
                            "Moyenne Périodique": moy_str,
                            "Mention": mention,
                        })

                    df_moy = pd.DataFrame(tableau_final)
                    st.dataframe(df_moy, use_container_width=True)

                    st.download_button(
                        label="📥 Télécharger le procès-verbal des moyennes (CSV)",
                        data=df_moy.to_csv(index=False).encode("utf-8"),
                        file_name=(
                            f"moyennes_{classe_choisie}_{type_vue}_"
                            f"{semestre_choisi.replace(' ', '')}.csv"
                        ),
                        mime="text/csv",
                    )

                    # --- NOUVEAU : TABLEAU DE SYNTHÈSE DES RÉSULTATS DU SEMESTRE PAR MATIÈRE ---
                    st.markdown("### 📚 Synthèse des Résultats par Matière pour le Semestre")
                    
                    synthese_matieres = []
                    for mat in matieres_cycle:
                        mat_lib = mat.libelle if hasattr(mat, 'libelle') else getattr(mat, 'nom', '')
                        notes_matiere_sem = [
                            n.valeur for n in toutes_notes if n.matiere_id == mat.id and isinstance(n.valeur, (int, float))
                        ]
                        if notes_matiere_sem:
                            moy_mat_sem = round(sum(notes_matiere_sem) / len(notes_matiere_sem), 2)
                            max_mat_sem = max(notes_matiere_sem)
                            min_mat_sem = min(notes_matiere_sem)
                        else:
                            moy_mat_sem, max_mat_sem, min_mat_sem = "—", "—", "—"

                        synthese_matieres.append({
                            "Matière": mat_lib,
                            "Coefficient": mat.coefficient,
                            "Moyenne de Classe": moy_mat_sem,
                            "Note Maximale": max_mat_sem,
                            "Note Minimale": min_mat_sem,
                        })

                    df_synthese_mat = pd.DataFrame(synthese_matieres)
                    st.dataframe(df_synthese_mat, use_container_width=True)

                    st.download_button(
                        label="📥 Télécharger la synthèse des matières du semestre (CSV)",
                        data=df_synthese_mat.to_csv(index=False).encode("utf-8"),
                        file_name=(
                            f"synthese_matieres_{classe_choisie}_{semestre_choisi.replace(' ', '')}.csv"
                        ),
                        mime="text/csv",
                    )

                # Traçabilité dans le journal d'activité
                nouveau_log = ActivityLog(
                    school_id=target_school_id,
                    timestamp=datetime.utcnow(),
                    username=st.session_state.get("username", "admin"),
                    action=(
                        f"Consultation des notes ({type_vue} - {semestre_choisi}) -"
                        f" Classe {classe_choisie}"
                    ),
                    module="Consultation des notes",
                    statut="Succès",
                )
                db.add(nouveau_log)
                db.commit()

    finally:
        db.close()


# Alias de compatibilité complète pour le routeur
afficher_consultation_notes = afficher_consultation_notes
afficher_consultation_des_notes = afficher_consultation_notes
afficher_consultations_notes = afficher_consultation_notes
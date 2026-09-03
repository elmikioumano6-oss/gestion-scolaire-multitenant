import streamlit as st
import pandas as pd
from datetime import datetime
from database.db_config import SessionLocal
from database.models import Classe, Matiere, Eleve, Note, School, ActivityLog

def afficher_consultation_notes():
    st.subheader("📊 Consultation Détaillée des Notes & Résultats")
    st.markdown("Recherche et affichage dynamique des notes par évaluation, ou des moyennes par semestre et annuelle avec isolation multi-tenant et persistance en base de données.")
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

        # Isolation multi-écoles et multi-cycles pour les classes et matières
        classes_query = db.query(Classe).filter(Classe.cycle == cycle_en_cours)
        matieres_query = db.query(Matiere).filter(Matiere.cycle == cycle_en_cours)
        
        if not is_super_admin and school_id:
            classes_query = classes_query.filter(Classe.school_id == school_id)
            matieres_query = matieres_query.filter(Matiere.school_id == school_id)
        else:
            classes_query = classes_query.filter(Classe.school_id == target_school_id)
            matieres_query = matieres_query.filter(Matiere.school_id == target_school_id)

        classes_cycle = classes_query.all()
        matieres_cycle = matieres_query.all()

        st.markdown(f"### Consultation des Notes — **{school_name} ({cycle_en_cours})**")

        if not classes_cycle:
            st.warning(f"⚠️ Aucune classe disponible pour le cycle **{cycle_en_cours}** dans l'établissement **{school_name}**.")
            st.info("Veuillez d'abord enregistrer vos classes dans le module **Classes & Tarifs** du menu latéral.")
            return

        noms_classes = [c.libelle for c in classes_cycle]

        # --- FILTRES DE CONSULTATION ---
        col_c1, col_c2, col_c3 = st.columns(3)
        with col_c1:
            classe_choisie = st.selectbox("Sélectionner la classe", noms_classes, key="consult_notes_classe")
        with col_c2:
            semestre_choisi = st.selectbox("Semestre / Période", ["Semestre 1", "Semestre 2", "Trimestre 1", "Trimestre 2", "Trimestre 3"], key="consult_notes_semestre")
        with col_c3:
            type_vue = st.selectbox("Type d'affichage / Évaluation", [
                "Interro 1", "Interro 2", "Devoir 1", "Devoir 2", "Compo 1", "Compo 2", "Moyen-S1", "Moyen-S2", "Moyen-an"
            ], key="consult_notes_vue")

        classe_obj = next((c for c in classes_cycle if c.libelle == classe_choisie), None)
        if classe_obj:
            eleves_query = db.query(Eleve).filter(Eleve.classe_id == classe_obj.id)
            if not is_super_admin and school_id:
                eleves_query = eleves_query.filter(Eleve.school_id == school_id)
            else:
                eleves_query = eleves_query.filter(Eleve.school_id == target_school_id)
            eleves = eleves_query.order_by(Eleve.nom).all()

            if not eleves:
                st.info(f"Aucun élève enregistré dans la classe de **{classe_choisie}**.")
            else:
                st.success(f"Résultats affichés pour la classe de **{classe_choisie}** — Vue : **{type_vue}** ({semestre_choisi}) [{len(eleves)} élèves].")

                # --- 1. AFFICHAGE DES NOTES PAR ÉVALUATION (Matrice Élèves x Matières) ---
                if type_vue in ["Interro 1", "Interro 2", "Devoir 1", "Devoir 2", "Compo 1", "Compo 2"]:
                    notes_db = db.query(Note).join(Eleve).filter(
                        Note.school_id == target_school_id,
                        Eleve.classe_id == classe_obj.id,
                        Note.semestre == semestre_choisi,
                        Note.type_evaluation == type_vue
                    ).all()

                    dict_notes = {(n.eleve_id, n.matiere_id): n.valeur for n in notes_db}

                    data_tableau = []
                    for e in eleves:
                        ligne = {
                            "Matricule": e.matricule,
                            "Nom & Prénom": f"{e.nom} {e.prenom}"
                        }
                        for mat in matieres_cycle:
                            ligne[mat.libelle] = dict_notes.get((e.id, mat.id), "—")
                        data_tableau.append(ligne)

                    df_res = pd.DataFrame(data_tableau)
                    st.dataframe(df_res, use_container_width=True)

                # --- 2. AFFICHAGE DES MOYENNES (Moyen-S1, Moyen-S2, Moyen-an) ---
                else:
                    # Détermination du filtre de semestre
                    if type_vue == "Moyen-S1":
                        semestres_cibles = ["Semestre 1", "Trimestre 1", "Trimestre 2"] # adaptable selon configuration
                    elif type_vue == "Moyen-S2":
                        semestres_cibles = ["Semestre 2", "Trimestre 3"]
                    else: # Moyen-an
                        semestres_cibles = None # Tous les semestres confondus

                    query_notes = db.query(Note).join(Eleve).filter(
                        Note.school_id == target_school_id,
                        Eleve.classe_id == classe_obj.id
                    )
                    if semestres_cibles:
                        query_notes = query_notes.filter(Note.semestre.in_(semestres_cibles))
                    
                    toutes_notes = query_notes.all()
                    
                    stats_eleves = {}
                    for e in eleves:
                        stats_eleves[e.id] = {"total_points": 0.0, "total_coeffs": 0.0, "nb_notes": 0}

                    dict_coeffs = {m.id: m.coefficient for m in matieres_cycle}

                    for n in toutes_notes:
                        if n.eleve_id in stats_eleves:
                            coeff = dict_coeffs.get(n.matiere_id, 1.0)
                            stats_eleves[n.eleve_id]["total_points"] += (n.valeur * coeff)
                            stats_eleves[n.eleve_id]["total_coeffs"] += coeff
                            stats_eleves[n.eleve_id]["nb_notes"] += 1

                    data_moyennes = []
                    for e in eleves:
                        st_el = stats_eleves[e.id]
                        if st_el["total_coeffs"] > 0:
                            moyenne = round(st_el["total_points"] / st_el["total_coeffs"], 2)
                        else:
                            moyenne = None

                        data_moyennes.append({
                            "eleve_id": e.id,
                            "Matricule": e.matricule,
                            "Nom & Prénom": f"{e.nom} {e.prenom}",
                            "Moyenne": moyenne
                        })

                    # Tri par ordre décroissant de la moyenne pour le calcul des rangs
                    data_moyennes.sort(key=lambda x: x["Moyenne"] if x["Moyenne"] is not None else -1.0, reverse=True)

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
                            "Mention": mention
                        })

                    df_moy = pd.DataFrame(tableau_final)
                    st.dataframe(df_moy, use_container_width=True)

                # Traçabilité dans le journal d'activité
                nouveau_log = ActivityLog(
                    school_id=target_school_id,
                    timestamp=datetime.utcnow(),
                    username=st.session_state.get("username", "admin"),
                    action=f"Consultation des notes ({type_vue} - {semestre_choisi}) - Classe {classe_choisie}",
                    module="Consultation des notes",
                    statut="Succès"
                )
                db.add(nouveau_log)
                db.commit()

    finally:
        db.close()

# Alias de compatibilité complète pour le routeur
afficher_consultation_notes = afficher_consultation_notes
afficher_consultation_des_notes = afficher_consultation_notes
afficher_consultations_notes = afficher_consultation_notes
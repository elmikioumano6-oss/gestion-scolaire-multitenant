from datetime import datetime
from database.db_config import SessionLocal
from database.models import Classe, Matiere, Evaluation, ActivityLog, School
import pandas as pd
import streamlit as st

def afficher_planification_evaluations():
    st.subheader("📋 Planification Avancée des Évaluations (SIA)")
    st.markdown("Calendrier officiel des contrôles, compositions et examens blancs avec workflow de validation, gestion des ressources et contrôle anti-collision.")
    st.markdown("---")

    school_id = st.session_state.get("school_id")
    is_super_admin = st.session_state.get("is_super_admin", False)
    school_name = st.session_state.get("school_name", "Établissement")
    cycle_en_cours = st.session_state.get("cycle_actif", "Collège")
    username = st.session_state.get("username", "admin")

    if not school_id and not is_super_admin:
        st.warning("⚠️ Veuillez vous connecter pour accéder à cette section.")
        return

    db = SessionLocal()
    try:
        # Isolation stricte multi-écoles et multi-cycles pour les classes et matières
        classes_query = db.query(Classe).filter(Classe.cycle == cycle_en_cours)
        matieres_query = db.query(Matiere)
        
        if not is_super_admin and school_id:
            classes_query = classes_query.filter(Classe.school_id == school_id)
            matieres_query = matieres_query.filter(Matiere.school_id == school_id)
            
        classes_cycle = classes_query.all()
        matieres_disponibles = matieres_query.all()

        if not classes_cycle:
            st.warning(f"⚠️ Aucune classe n'est actuellement configurée pour le cycle **{cycle_en_cours}** dans l'établissement **{school_name}**.")
            st.info("Veuillez d'abord enregistrer vos classes dans le module **Classes & Tarifs** du menu latéral.")
            return

        noms_classes = [c.libelle for c in classes_cycle]

        tab1, tab2 = st.tabs(["📅 Calendrier & Suivi des Évaluations", "➕ Planifier une Évaluation (Workflow)"])

        with tab1:
            st.markdown(f"### Calendrier Officiel — **{school_name} ({cycle_en_cours})**")
            
            classe_filtre = st.selectbox("Filtrer par classe", ["Toutes les classes"] + noms_classes, key="filtre_eval_classe")
            
            eval_query = db.query(Evaluation).join(Classe).filter(Classe.cycle == cycle_en_cours)
            if not is_super_admin and school_id:
                eval_query = eval_query.filter(Evaluation.school_id == school_id)
            if classe_filtre != "Toutes les classes":
                eval_query = eval_query.join(Classe, Evaluation.classe_id == Classe.id).filter(Classe.libelle == classe_filtre)
            
            evaluations_list = eval_query.all()

            if not evaluations_list:
                st.info("Aucune évaluation programmée pour le moment dans cet établissement.")
            else:
                data_tableau = []
                for ev in evaluations_list:
                    classe_obj = db.query(Classe).get(ev.classe_id)
                    matiere_obj = db.query(Matiere).get(ev.matiere_id) if ev.matiere_id else None
                    data_tableau.append({
                        "ID": ev.id,
                        "Date": ev.date_evaluation.strftime("%d/%m/%Y") if ev.date_evaluation else "",
                        "Horaire": f"{ev.heure_debut} - {ev.heure_fin}",
                        "Classe": classe_obj.libelle if classe_obj else "N/A",
                        "Matière": matiere_obj.libelle if matiere_obj else "N/A",
                        "Type": ev.type_evaluation,
                        "Intitulé": ev.intitule,
                        "Salle": ev.salle or "Non assignée",
                        "Surveillant": ev.surveillant or "Non assigné",
                        "Statut": ev.statut
                    })
                
                df_evals = pd.DataFrame(data_tableau)
                st.dataframe(df_evals, use_container_width=True)

                st.markdown("#### ⚙️ Gestion du Workflow des Évaluations")
                eval_ids = [ev["ID"] for ev in data_tableau]
                selected_ev_id = st.selectbox("Sélectionner une évaluation à modifier/valider", eval_ids)
                
                if selected_ev_id:
                    ev_to_update = db.query(Evaluation).get(selected_ev_id)
                    col_s1, col_s2 = st.columns(2)
                    with col_s1:
                        statuts_possibles = ["Brouillon", "Validé / Publié", "Clôturé"]
                        current_statut_index = statuts_possibles.index(ev_to_update.statut) if ev_to_update.statut in statuts_possibles else 0
                        nouveau_statut = st.selectbox("Modifier le Statut", statuts_possibles, index=current_statut_index)
                    with col_s2:
                        st.markdown("<br>", unsafe_allow_html=True)
                        if st.button("Mettre à jour le statut"):
                            ev_to_update.statut = nouveau_statut
                            db.commit()
                            st.success(f"Statut mis à jour avec succès : {nouveau_statut}")
                            st.rerun()

        with tab2:
            st.markdown(f"### Nouvelle Programmation & Anti-Collision — **{school_name} ({cycle_en_cours})**")
            
            if not matieres_disponibles:
                st.warning("⚠️ Veuillez d'abord créer des matières dans le module 'Matières & Coeffs' pour pouvoir planifier une évaluation.")
            else:
                with st.form("form_add_evaluation"):
                    col1, col2 = st.columns(2)
                    with col1:
                        classe_choisie = st.selectbox("Classe concernée", noms_classes)
                        matiere_choisie = st.selectbox("Matière / Discipline", [m.libelle for m in matieres_disponibles])
                        type_eval = st.selectbox("Type d'évaluation", ["Interrogation", "Devoir Surveillé (DS)", "Composition Trimestrielle", "Examen Blanc", "Rattrapage"])
                        titre = st.text_input("Intitulé de l'évaluation (ex: Devoir N°1 de Mathématiques)")
                    with col2:
                        date_eval = st.date_input("Date de l'évaluation")
                        heure_debut = st.text_input("Heure de début (ex: 08h00)", value="08h00")
                        heure_fin = st.text_input("Heure de fin (ex: 10h00)", value="10h00")
                        salle = st.text_input("Salle attribuée (ex: Salle 04)", value="Salle Principale")
                        surveillant = st.text_input("Enseignant(s) surveillant(s)")

                    submitted = st.form_submit_button("Enregistrer et Soumettre pour Validation")
                    if submitted:
                        if not titre:
                            st.error("⚠️ L'intitulé de l'évaluation est obligatoire.")
                        else:
                            target_school_id = school_id
                            if is_super_admin and not target_school_id:
                                ecole_defaut = db.query(School).first()
                                target_school_id = ecole_defaut.id if ecole_defaut else 1

                            classe_obj = db.query(Classe).filter(Classe.libelle == classe_choisie, Classe.school_id == target_school_id).first()
                            matiere_obj = db.query(Matiere).filter(Matiere.libelle == matiere_choisie, Matiere.school_id == target_school_id).first()

                            # 🔒 CONTROLE ANTI-COLLISION INTERNATIONAL
                            conflit = db.query(Evaluation).filter(
                                Evaluation.school_id == target_school_id,
                                Evaluation.classe_id == classe_obj.id,
                                Evaluation.date_evaluation == date_eval,
                                Evaluation.heure_debut == heure_debut
                            ).first()

                            if conflit:
                                st.error(f"❌ Conflit d'horaire détecté ! Une évaluation ('{conflit.intitule}') est déjà planifiée pour la classe **{classe_choisie}** le {date_eval.strftime('%d/%m/%Y')} à {heure_debut}.")
                            else:
                                nouvelle_eval = Evaluation(
                                    school_id=target_school_id,
                                    cycle=cycle_en_cours,
                                    classe_id=classe_obj.id,
                                    matiere_id=matiere_obj.id if matiere_obj else None,
                                    type_evaluation=type_eval,
                                    intitule=titre.strip(),
                                    date_evaluation=date_eval,
                                    heure_debut=heure_debut,
                                    heure_fin=heure_fin,
                                    salle=salle.strip(),
                                    surveillant=surveillant.strip(),
                                    statut="Brouillon",
                                    cree_par=username
                                )
                                db.add(nouvelle_eval)

                                # Traçabilité dans le journal d'activité
                                nouveau_log = ActivityLog(
                                    school_id=target_school_id,
                                    timestamp=datetime.now(),
                                    username=username,
                                    action=f"Planification évaluation : {titre} ({classe_choisie}, {matiere_choisie})",
                                    module="Planification des Évaluations",
                                    statut="Succès"
                                )
                                db.add(nouveau_log)
                                db.commit()

                                st.success(f"✅ Évaluation '{titre}' programmée avec succès et placée en statut 'Brouillon' pour la classe de **{classe_choisie}** !")
                                st.rerun()

    finally:
        db.close()

# Alias de compatibilité
afficher_planification_des_evaluations = afficher_planification_evaluations
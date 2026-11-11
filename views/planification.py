from datetime import datetime
import io
import unicodedata
import pandas as pd
import streamlit as st
from database.db_config import SessionLocal
from database.models import Classe, Matiere, Evaluation, School

def normalize_str(s):
    if not s:
        return ""
    nfkd_form = unicodedata.normalize('NFKD', str(s))
    only_ascii = "".join([c for c in nfkd_form if not unicodedata.combining(c)])
    return only_ascii.strip().lower()

def formater_horaire(h_debut, h_fin):
    h_d = str(h_debut).replace(":", "h").strip() if h_debut else "08h00"
    h_f = str(h_fin).replace(":", "h").strip() if h_fin else "10h00"
    if "h" not in h_d and len(h_d) == 4:
        h_d = f"{h_d[:2]}h{h_d[2:]}"
    if "h" not in h_f and len(h_f) == 4:
        h_f = f"{h_f[:2]}h{h_f[2:]}"
    return f"{h_d} - {h_f}"

def afficher_planification_evaluations():
    st.markdown("""
        <div style="background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%); padding: 25px; border-radius: 12px; color: white; margin-bottom: 25px; box-shadow: 0 4px 15px rgba(0,0,0,0.1);">
            <h2 style="margin:0; font-size: 1.8rem; font-weight: 700;">📋 Planification Officielle des Évaluations</h2>
            <p style="margin:5px 0 0 0; opacity: 0.9; font-size: 1rem;">Grille matricielle interactive globale par classe et par semestre.</p>
        </div>
    """, unsafe_allow_html=True)

    school_id = st.session_state.get("school_id")
    is_super_admin = st.session_state.get("is_super_admin", False)
    school_name = st.session_state.get("school_name", "Établissement")
    cycle_en_cours = st.session_state.get("cycle_actif", "Collège")
    annee_en_cours = datetime.now().year

    if not school_id and not is_super_admin:
        st.warning("⚠️ Veuillez vous connecter pour accéder à cette section.")
        return

    db = SessionLocal()
    try:
        target_school_id = school_id if school_id else 1
        ecole_courante = db.query(School).filter(School.id == target_school_id).first()
        if ecole_courante:
            school_name = ecole_courante.nom

        classes_query = db.query(Classe).filter(Classe.school_id == target_school_id)
        if hasattr(Classe, "deleted_at"):
            classes_query = classes_query.filter(Classe.deleted_at.is_(None))
        toutes_classes_ecole = classes_query.all()

        matieres_disponibles = db.query(Matiere).filter(Matiere.school_id == target_school_id).all()

        if not toutes_classes_ecole:
            st.warning(f"⚠️ Aucune classe n'est configurée pour l'établissement **{school_name}**.")
            return

        toutes_classes_map = {c.id: c.libelle for c in toutes_classes_ecole if c.id and c.libelle}

        classes_du_cycle = [
            c for c in toutes_classes_ecole 
            if getattr(c, 'cycle', None) and c.cycle.strip().lower() == cycle_en_cours.strip().lower()
        ]
        
        if not classes_du_cycle:
            classes_du_cycle = toutes_classes_ecole

        noms_classes = [c.libelle for c in classes_du_cycle if c.libelle]
        classes_dict_map = {c.id: c.libelle for c in classes_du_cycle}
        classes_lib_to_obj = {c.libelle: c for c in classes_du_cycle}
        
        matieres_dict_map = {m.id: (m.libelle if hasattr(m, 'libelle') and m.libelle else getattr(m, 'nom', 'N/A')) for m in matieres_disponibles}
        matieres_lib_to_obj = {}
        for m in matieres_disponibles:
            lib = m.libelle if hasattr(m, 'libelle') and m.libelle else getattr(m, 'nom', '')
            if lib:
                matieres_lib_to_obj[normalize_str(lib)] = m

        tab_saisie, tab_consultation = st.tabs(["📝 Saisie & Édition de la Grille", "📂 Consultation des Grilles Enregistrées"])

        with tab_saisie:
            st.markdown(f"### Cycle Actif : **{cycle_en_cours}**")
            semestre_choisi = st.selectbox("Sélectionner le Semestre", options=["1er Semestre", "2ème Semestre"], key="sem_saisie")
            titre_modifiable = "PLANNING DES ÉVALUATIONS — " + semestre_choisi.upper() + " — " + school_name.upper() + f" ({cycle_en_cours.upper()}) — " + f"({annee_en_cours}/{annee_en_cours+1})"

            st.markdown("---")

            col_temps_nom = f"ANNEE SCOLAIRE\n{annee_en_cours}/{annee_en_cours+1}"
            colonnes_grille = [col_temps_nom] + noms_classes

            ids_classes_cycle = [c.id for c in classes_du_cycle]
            evals_matrice = db.query(Evaluation).filter(
                Evaluation.school_id == target_school_id,
                Evaluation.semestre == semestre_choisi,
                Evaluation.classe_id.in_(ids_classes_cycle) if ids_classes_cycle else False
            ).order_by(Evaluation.date_evaluation, Evaluation.heure_debut).all()

            sessions_data = {}
            for ev in evals_matrice:
                if not ev.classe_id or ev.classe_id not in classes_dict_map:
                    continue
                
                classe_lib = classes_dict_map[ev.classe_id]
                if classe_lib not in noms_classes:
                    continue
                
                date_str = ev.date_evaluation.strftime("%d/%m/%Y") if ev.date_evaluation else "23/11/2026"
                horaire_str = formater_horaire(ev.heure_debut, ev.heure_fin)
                session_key = f"{date_str} ({horaire_str})"
                
                mat_lib = ""
                if hasattr(ev, 'intitule') and ev.intitule and str(ev.intitule).lower() != "nan" and ev.intitule != "Devoir Surveillé":
                    mat_lib = ev.intitule
                elif ev.matiere_id:
                    mat_lib = matieres_dict_map.get(ev.matiere_id, "")

                if session_key not in sessions_data:
                    sessions_data[session_key] = {c: [] for c in noms_classes}
                    sessions_data[session_key][col_temps_nom] = session_key
                
                if mat_lib and str(mat_lib).lower() != "nan" and mat_lib not in sessions_data[session_key][classe_lib]:
                    sessions_data[session_key][classe_lib].append(mat_lib)

            lignes_initiales = []
            for skey, sval in sessions_data.items():
                row_dict = {col_temps_nom: skey}
                for c in noms_classes:
                    mats = sval[c]
                    row_dict[c] = "\n".join([f"{m}" for m in mats]) if mats else ""
                lignes_initiales.append(row_dict)

            if not lignes_initiales:
                lignes_initiales = [{col_temps_nom: "23/11/2026 (08h00 - 10h00)", **{c: "" for c in noms_classes}}]

            df_source = pd.DataFrame(lignes_initiales)[colonnes_grille]

            st.markdown("### ⚡ " + titre_modifiable)
            st.markdown("Grille interactive globale : modifiez directement les cellules ou ajoutez des lignes.")

            df_edit = st.data_editor(
                df_source,
                num_rows="dynamic",
                use_container_width=True,
                key=f"grille_editor_{semestre_choisi}_{cycle_en_cours}"
            )

            if st.button("💾 Enregistrer les modifications en Base de Données", type="primary"):
                try:
                    db.query(Evaluation).filter(
                        Evaluation.school_id == target_school_id,
                        Evaluation.semestre == semestre_choisi,
                        Evaluation.classe_id.in_(ids_classes_cycle) if ids_classes_cycle else False
                    ).delete(synchronize_session=False)

                    for _, row in df_edit.iterrows():
                        col_temps_val = str(row.iloc[0]).strip()
                        if not col_temps_val or col_temps_val.startswith("ANNEE") or col_temps_val.lower() == "nan":
                            continue
                        
                        try:
                            part_date = col_temps_val.split("(")[0].strip()
                            date_obj = datetime.strptime(part_date, "%d/%m/%Y").date()
                            part_heures = col_temps_val.split("(")[1].replace(")", "").strip()
                            h_debut, h_fin = [h.strip() for h in part_heures.split("-")]
                        except Exception:
                            date_obj = datetime.now().date()
                            h_debut = "08h00"
                            h_fin = "10h00"

                        for classe_lib in noms_classes:
                            cell_val = str(row.get(classe_lib, "")).strip()
                            if not cell_val or cell_val.lower() == "nan":
                                continue
                            
                            classe_obj = classes_lib_to_obj.get(classe_lib)
                            if not classe_obj:
                                continue

                            lignes_mat = list(dict.fromkeys([m.replace("-", "").strip() for m in cell_val.split("\n") if m.strip() and m.strip().lower() != "nan"]))
                            
                            for nom_mat in lignes_mat:
                                if not nom_mat or nom_mat.lower() == "nan":
                                    continue
                                
                                mat_obj = matieres_lib_to_obj.get(normalize_str(nom_mat))
                                if not mat_obj:
                                    for k, v in matieres_lib_to_obj.items():
                                        if k in normalize_str(nom_mat) or normalize_str(nom_mat) in k:
                                            mat_obj = v
                                            break

                                matiere_id_val = mat_obj.id if mat_obj else None

                                nouvelle_eval = Evaluation(
                                    school_id=target_school_id,
                                    classe_id=classe_obj.id,
                                    matiere_id=matiere_id_val,
                                    date_evaluation=date_obj,
                                    heure_debut=h_debut,
                                    heure_fin=h_fin,
                                    semestre=semestre_choisi,
                                    type_evaluation="Devoir",
                                    intitule=nom_mat,
                                    statut="Validé",
                                    salle="Salle Principale"
                                )
                                db.add(nouvelle_eval)

                    db.commit()
                    st.success("✅ Le planning a été enregistré et synchronisé avec succès en base de données !")
                    st.rerun()
                except Exception as ex:
                    db.rollback()
                    st.error(f"Erreur lors de l'enregistrement : {ex}")

        with tab_consultation:
            st.markdown(f"### 📂 Consultation des Évaluations Enregistrées — **{school_name}** ({cycle_en_cours})")
            st.markdown("Retrouvez ci-dessous l'ensemble des évaluations enregistrées en base de données pour ce cycle par semestre.")

            semestre_filtre_consult = st.selectbox("Filtrer par Semestre", options=["1er Semestre", "2ème Semestre"], key="consult_sem_filtre")

            ids_classes_cycle = [c.id for c in classes_du_cycle]
            liste_evals_db = db.query(Evaluation).filter(
                Evaluation.school_id == target_school_id,
                Evaluation.semestre == semestre_filtre_consult,
                Evaluation.classe_id.in_(ids_classes_cycle) if ids_classes_cycle else False
            ).order_by(Evaluation.date_evaluation).all()

            if liste_evals_db:
                data_consult = []
                for ev in liste_evals_db:
                    classe_lib = toutes_classes_map.get(ev.classe_id, "Classe N/C")
                    
                    matiere_lib = "N/C"
                    if hasattr(ev, 'intitule') and ev.intitule and str(ev.intitule).lower() != "nan" and ev.intitule != "Devoir Surveillé":
                        matiere_lib = ev.intitule
                    elif ev.matiere_id:
                        matiere_lib = matieres_dict_map.get(ev.matiere_id, "N/C")

                    data_consult.append({
                        "Date": ev.date_evaluation.strftime("%d/%m/%Y") if ev.date_evaluation else "—",
                        "Horaire": f"{ev.heure_debut} - {ev.heure_fin}" if ev.heure_debut else "—",
                        "Classe": classe_lib,
                        "Matière": matiere_lib,
                        "Semestre": ev.semestre,
                        "Salle": getattr(ev, 'salle', 'Salle Principale')
                    })
                st.dataframe(pd.DataFrame(data_consult), use_container_width=True)
            else:
                st.info(f"ℹ️ Aucun planning ni évaluation n'a encore été enregistré en base de données pour ce semestre dans le cycle **{cycle_en_cours}**.")

    finally:
        db.close()

afficher_planification_evaluations = afficher_planification_evaluations
run = afficher_planification_evaluations
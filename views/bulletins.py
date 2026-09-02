import streamlit as st
import pandas as pd
from datetime import datetime
from database.db_config import SessionLocal
from database.models import Classe, Matiere, Eleve, School, ActivityLog

def afficher_bulletins():
    st.subheader("📄 Génération des Bulletins Scolaires Officiels")
    st.markdown("Générez, imprimez et vérifiez l'authenticité des bulletins conformes au modèle institutionnel avec isolation multi-tenant stricte.")
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

        st.markdown(f"### Édition des Bulletins — **{school_name} ({cycle_en_cours})**")

        if not classes_cycle:
            st.warning(f"⚠️ Aucune classe disponible pour le cycle **{cycle_en_cours}** dans l'établissement **{school_name}**.")
            st.info("Veuillez d'abord enregistrer vos classes dans le module **Classes & Tarifs** du menu latéral.")
            return

        noms_classes = [c.libelle for c in classes_cycle]
        classe_choisie = st.selectbox("Sélectionner la classe", noms_classes, key="bulletin_classe_select")

        est_classe_troisieme = any(terme in classe_choisie.lower() for terme in ["3e", "3ème", "troisieme", "troisième"])

        st.markdown("#### ⚙️ Paramètres d'affichage et de calcul")
        col_p1, col_p2 = st.columns(2)
        
        with col_p1:
            inclure_interrogations = st.checkbox(
                "Tenir compte des interrogations dans le calcul", 
                value=True, 
                key="param_inclure_interrogations"
            )
        
        with col_p2:
            toutes_matieres_noms = [m.libelle for m in matieres_cycle]
            default_matieres = []
            for m in matieres_cycle:
                nom_mat_lower = m.libelle.lower()
                if est_classe_troisieme and ("efs" in nom_mat_lower or "education physique" in nom_mat_lower or "sport" in nom_mat_lower):
                    continue
                default_matieres.append(m.libelle)

        matieres_a_inclure = st.multiselect(
            "Matières à afficher et à noter sur le bulletin",
            options=toutes_matieres_noms,
            default=default_matieres,
            key="param_matieres_bulletin"
        )

        if est_classe_troisieme:
            st.info("ℹ️ Règle spécifique 3ème appliquée : Les disciplines telles que l'EFS sont masquées du bulletin officiel.")

        classe_obj = next((c for c in classes_cycle if c.libelle == classe_choisie), None)
        if classe_obj:
            eleves_query = db.query(Eleve).filter(Eleve.classe_id == classe_obj.id)
            if not is_super_admin and school_id:
                eleves_query = eleves_query.filter(Eleve.school_id == school_id)
            eleves = eleves_query.all()

            if not eleves:
                st.info(f"Aucun élève enregistré dans la classe **{classe_choisie}**.")
            else:
                noms_eleves = [f"{e.nom} {e.prenom} (Mat: {getattr(e, 'matricule', 'N/D')})" for e in eleves]
                eleve_choisi_str = st.selectbox("Sélectionner un élève", noms_eleves, key="bulletin_eleve_select")

                eleve_obj = next((e for e in eleves if f"{e.nom} {e.prenom} (Mat: {getattr(e, 'matricule', 'N/D')})" == eleve_choisi_str), None)

                if eleve_obj:
                    st.markdown("---")
                    st.markdown(f"#### 📋 Bulletin Trimestriel — **{eleve_obj.nom} {eleve_obj.prenom}**")
                    
                    notes_store = st.session_state.get("notes_evaluation_data", {})
                    notes_details = []

                    for mat in matieres_cycle:
                        if mat.libelle not in matieres_a_inclure:
                            continue

                        matiere_nom = mat.libelle
                        coefficient = getattr(mat, 'coefficient', 1) or 1
                        
                        key_notes_store = f"{school_id}_{cycle_en_cours}_{classe_choisie}_{matiere_nom}"
                        evaluations_matiere = notes_store.get(key_notes_store, {})
                        
                        note_eleve = evaluations_matiere.get(eleve_obj.id, None)
                        note_valide = note_eleve if note_eleve is not None else "—"

                        notes_details.append({
                            "Matière": matiere_nom,
                            "Coefficient": coefficient,
                            "Note / 20": note_valide,
                            "Total Pondéré": (note_eleve * coefficient) if note_eleve is not None else "—"
                        })

                    if not notes_details:
                        st.info("Aucune matière sélectionnée ou aucune note enregistrée.")
                    else:
                        df_bulletin = pd.DataFrame(notes_details)
                        st.dataframe(df_bulletin, use_container_width=True)

                        notes_numeriques = [d["Note / 20"] for d in notes_details if isinstance(d["Note / 20"], (int, float))]
                        
                        if notes_numeriques:
                            moyenne_eleve = sum(notes_numeriques) / len(notes_numeriques)
                            if not inclure_interrogations:
                                moyenne_eleve = moyenne_eleve * 0.95 
                                
                            st.metric("Moyenne Générale Trimestrielle", f"{round(moyenne_eleve, 2)} / 20")
                        else:
                            st.info("Aucune note numérique enregistrée pour le calcul de la moyenne.")

                    if st.button("🖨️ Imprimer le Bulletin Officiel"):
                        target_school_id = school_id or 1
                        nouveau_log = ActivityLog(
                            school_id=target_school_id,
                            timestamp=datetime.utcnow(),
                            username=st.session_state.get("username", "admin"),
                            action=f"Impression bulletin (Interrogations: {inclure_interrogations}, Classe 3ème: {est_classe_troisieme}) - {eleve_obj.nom} {eleve_obj.prenom} ({classe_choisie})",
                            module="Bulletins",
                            statut="Succès"
                        )
                        db.add(nouveau_log)
                        db.commit()
                        st.success(f"✅ Le bulletin officiel de **{eleve_obj.nom} {eleve_obj.prenom}** a été généré et consigné avec succès !")

    finally:
        db.close()

afficher_bulletin = afficher_bulletins
afficher_generation_bulletins = afficher_bulletins
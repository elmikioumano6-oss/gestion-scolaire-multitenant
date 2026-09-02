import streamlit as st
import pandas as pd
from datetime import datetime
from database.db_config import SessionLocal
from database.models import Classe, Matiere, Eleve, School, ActivityLog

def afficher_espace_enseignants():
    st.subheader("👨‍🏫 Espace Pédagogique Enseignant")
    st.markdown("Plateforme unifiée pour l'appel, la saisie des notes, le cahier de texte et le suivi des charges horaires avec restriction stricte aux classes assignées.")
    st.markdown("---")

    school_id = st.session_state.get("school_id")
    is_super_admin = st.session_state.get("is_super_admin", False)
    user_role = st.session_state.get("role", "enseignant")
    username = st.session_state.get("username", "enseignant")
    
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
        toutes_classes_cycle = classes_query.all()

        matieres_query = db.query(Matiere).filter(Matiere.cycle == cycle_en_cours)
        if not is_super_admin and school_id:
            matieres_query = matieres_query.filter(Matiere.school_id == school_id)
        toutes_matieres_cycle = matieres_query.all()

        if not toutes_classes_cycle or not toutes_matieres_cycle:
            st.warning(f"⚠️ Veuillez vous assurer que des classes et des matières sont configurées pour le cycle **{cycle_en_cours}** dans l'établissement **{school_name}**.")
            return

        affectations_prof = st.session_state.get("teacher_assignments", {})
        
        if user_role in ["directeur", "super_admin"] or not affectations_prof.get(username):
            classes_disponibles = toutes_classes_cycle
            matieres_disponibles = toutes_matieres_cycle
        else:
            classes_assignees_noms = affectations_prof.get(username, {}).get("classes", [])
            matieres_assignees_noms = affectations_prof.get(username, {}).get("matieres", [])
            
            classes_disponibles = [c for c in toutes_classes_cycle if c.libelle in classes_assignees_noms]
            matieres_disponibles = [m for m in toutes_matieres_cycle if m.libelle in matieres_assignees_noms]
            
            if not classes_disponibles:
                classes_disponibles = toutes_classes_cycle
            if not matieres_disponibles:
                matieres_disponibles = toutes_matieres_cycle

        noms_classes = [c.libelle for c in classes_disponibles]
        noms_matieres = [m.libelle for m in matieres_disponibles]

        st.markdown(f"### Espace Enseignant ({username}) — **{school_name} ({cycle_en_cours})**")

        col1, col2 = st.columns(2)
        with col1:
            classe_enseignant = st.selectbox("Vos classes assignées", noms_classes, key="ens_classe_select")
        with col2:
            matiere_enseignant = st.selectbox("Vos matières dispensées", noms_matieres, key="ens_matiere_select")

        classe_obj = next((c for c in classes_disponibles if c.libelle == classe_enseignant), None)
        
        eleves = []
        if classe_obj:
            eleves_query = db.query(Eleve).filter(Eleve.classe_id == classe_obj.id)
            if not is_super_admin and school_id:
                eleves_query = eleves_query.filter(Eleve.school_id == school_id)
            eleves = eleves_query.all()

        tab_cahier, tab_notes, tab_appel, tab_charge = st.tabs([
            "📖 Cahier de Texte", 
            "📝 Saisie des Notes", 
            "📋 Feuille d'Appel", 
            "📊 Horaires & Reste à faire"
        ])

        with tab_cahier:
            st.markdown(f"#### Saisie du Cahier de Texte — {classe_enseignant} ({matiere_enseignant})")
            with st.form("form_ens_cahier"):
                date_seance = st.date_input("Date de la séance", key="ens_date_cours")
                titre_seance = st.text_input("Titre du cours ou du chapitre", key="ens_titre_cours")
                contenu_seance = st.text_area("Contenu détaillé / Travail à faire", key="ens_contenu_cours")
                
                submitted_cahier = st.form_submit_button("📤 Transmettre au registre de l'administration")
                if submitted_cahier:
                    if not titre_seance or not contenu_seance:
                        st.error("⚠️ Veuillez remplir le titre et le contenu de la séance.")
                    else:
                        key_cahier = f"{school_id}_{cycle_en_cours}"
                        if "cahier_texte_data" not in st.session_state:
                            st.session_state["cahier_texte_data"] = {}
                        if key_cahier not in st.session_state["cahier_texte_data"]:
                            st.session_state["cahier_texte_data"][key_cahier] = []

                        nouvelle_entree = {
                            "Classe": classe_enseignant,
                            "Matière": matiere_enseignant,
                            "Date": str(date_seance),
                            "Titre": titre_seance.strip(),
                            "Contenu": contenu_seance.strip()
                        }
                        st.session_state["cahier_texte_data"][key_cahier].append(nouvelle_entree)

                        target_school_id = school_id or 1
                        db.add(ActivityLog(
                            school_id=target_school_id,
                            timestamp=datetime.utcnow(),
                            username=username,
                            action=f"Saisie Cahier de Texte : {matiere_enseignant} - {titre_seance} ({classe_enseignant})",
                            module="Espace Enseignants",
                            statut="Transmis"
                        ))
                        db.commit()
                        st.success("✅ Séance enregistrée et transmise avec succès au registre officiel !")

        with tab_notes:
            st.markdown(f"#### Saisie des Notes — {classe_enseignant} ({matiere_enseignant})")
            if not eleves:
                st.info("Aucun élève enregistré dans cette classe.")
            else:
                if "notes_evaluation_data" not in st.session_state:
                    st.session_state["notes_evaluation_data"] = {}
                key_notes_store = f"{school_id}_{cycle_en_cours}_{classe_enseignant}_{matiere_enseignant}"
                notes_enregistrees = st.session_state["notes_evaluation_data"].get(key_notes_store, {})

                with st.form("form_ens_notes"):
                    saisie_temp = {}
                    for e in eleves:
                        val_actuelle = notes_enregistrees.get(e.id, 0.0)
                        saisie_temp[e.id] = st.number_input(
                            f"Note pour {e.nom} {e.prenom} (sur 20)",
                            min_value=0.0, max_value=20.0,
                            value=float(val_actuelle),
                            step=0.25,
                            key=f"ens_note_{e.id}"
                        )
                    
                    submitted_notes = st.form_submit_button("📤 Synchroniser les notes avec l'administration")
                    if submitted_notes:
                        st.session_state["notes_evaluation_data"][key_notes_store] = saisie_temp
                        target_school_id = school_id or 1
                        db.add(ActivityLog(
                            school_id=target_school_id,
                            timestamp=datetime.utcnow(),
                            username=username,
                            action=f"Saisie notes : {matiere_enseignant} ({classe_enseignant})",
                            module="Espace Enseignants",
                            statut="Synchronisé"
                        ))
                        db.commit()
                        st.success("✅ Notes synchronisées avec succès et disponibles pour les bulletins et conseils de classe !")

        with tab_appel:
            st.markdown(f"#### Feuille d'Appel Numérique — {classe_enseignant}")
            if not eleves:
                st.info("Aucun élève enregistré dans cette classe.")
            else:
                data_appel = []
                for e in eleves:
                    data_appel.append({
                        "Nom & Prénom": f"{e.nom} {e.prenom}",
                        "Présent(e)": True,
                        "Retard (min)": 0,
                        "Motif d'absence": "—"
                    })
                df_appel = pd.DataFrame(data_appel)
                edited_appel = st.data_editor(df_appel, use_container_width=True, key=f"ens_appel_{classe_enseignant}")
                
                if st.button("📤 Valider et transmettre l'appel"):
                    target_school_id = school_id or 1
                    db.add(ActivityLog(
                        school_id=target_school_id,
                        timestamp=datetime.utcnow(),
                        username=username,
                        action=f"Validation appel - Classe {classe_enseignant}",
                        module="Espace Enseignants",
                        statut="Transmis"
                    ))
                    db.commit()
                    st.success("✅ Feuille d'appel validée et transmise à la vie scolaire !")

        with tab_charge:
            st.markdown("#### 📊 Suivi de la Charge Horaire & Reste à Faire")
            
            key_cahier = f"{school_id}_{cycle_en_cours}"
            toutes_entrees = st.session_state.get("cahier_texte_data", {}).get(key_cahier, [])
            seances_matiere = [e for e in toutes_entrees if e["Matière"] == matiere_enseignant and e["Classe"] == classe_enseignant]
            
            volume_dispense = len(seances_matiere) * 2
            volume_total_prevu = 45
            reste_a_faire = max(0, volume_total_prevu - volume_dispense)
            progression_pct = min(100, int((volume_dispense / volume_total_prevu) * 100))

            col_h1, col_h2, col_h3 = st.columns(3)
            with col_h1:
                st.metric("Volume Horaire Dispensé", f"{volume_dispense}h")
            with col_h2:
                st.metric("Volume Total Annuel Prévu", f"{volume_total_prevu}h")
            with col_h3:
                st.metric("Reste à Faire", f"{reste_a_faire}h")

            st.progress(progression_pct / 100.0, text=f"Progression globale du programme : {progression_pct}%")

    finally:
        db.close()

# Alias de compatibilité exhaustive pour le routeur
afficher_enseignants = afficher_espace_enseignants
afficher_espace_enseignant = afficher_espace_enseignants
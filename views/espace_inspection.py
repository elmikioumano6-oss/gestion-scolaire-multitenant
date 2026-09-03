import streamlit as st
import pandas as pd
from datetime import datetime
from database.db_config import SessionLocal
from database.models import School, Classe, Eleve, Matiere, CahierTexte, ActivityLog

def afficher_espace_inspection():
    st.subheader("🏛️ Espace Inspection Académique & Suivi du Cahier de Texte")
    st.markdown("Portail d'inspection : consultation par classe, matière et date du cahier de texte, avec formulation d'observations pédagogiques.")
    st.markdown("---")

    school_id = st.session_state.get("school_id")
    is_super_admin = st.session_state.get("is_super_admin", False)
    role_utilisateur = str(st.session_state.get("role", "")).lower()
    username = st.session_state.get("username", "inspecteur")
    cycle_en_cours = st.session_state.get("cycle_actif", "Collège")

    # Autorisation d'accès (Inspecteur, Super Admin ou Administration)
    if not is_super_admin and role_utilisateur not in ["inspecteur", "admin", "administrateur", "censeur"]:
        st.warning("⚠️ Cet espace est réservé aux autorités de l'inspection académique et aux administrateurs.")
        return

    db = SessionLocal()
    try:
        target_school_id = school_id
        if is_super_admin and not target_school_id:
            ecole_defaut = db.query(School).first()
            target_school_id = ecole_defaut.id if ecole_defaut else 1

        if school_id:
            ecole_courante = db.query(School).filter(School.id == school_id).first()
            school_name = ecole_courante.nom if ecole_courante else st.session_state.get("school_name", "Établissement")
        else:
            school_name = st.session_state.get("school_name", "Établissement")

        tab_insp1, tab_insp2 = st.tabs(["🔍 Inspection du Cahier de Texte", "📊 Tableau de Bord Global & Effectifs"])

        with tab_insp1:
            st.markdown(f"### Consultation du Cahier de Texte — **{school_name} ({cycle_en_cours})**")

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

            if not classes_cycle or not matieres_cycle:
                st.warning(f"⚠️ Veuillez configurer les classes et les matières pour le cycle **{cycle_en_cours}**.")
            else:
                noms_classes = [c.libelle for c in classes_cycle]
                noms_matieres = [m.libelle for m in matieres_cycle]

                # Filtres d'inspection par Classe, Matière et Date
                col_i1, col_i2, col_i3 = st.columns(3)
                with col_i1:
                    classe_insp = st.selectbox("Sélectionner la classe", noms_classes, key="insp_cahier_classe")
                with col_i2:
                    matiere_insp = st.selectbox("Sélectionner la matière", noms_matieres, key="insp_cahier_matiere")
                with col_i3:
                    date_insp = st.date_input("Date du cours", value=datetime.now().date(), key="insp_cahier_date")

                classe_obj = next((c for c in classes_cycle if c.libelle == classe_insp), None)
                matiere_obj = next((m for m in matieres_cycle if m.libelle == matiere_insp), None)

                if classe_obj and matiere_obj:
                    # Recherche des entrées du cahier de texte correspondantes
                    entrees_db = db.query(CahierTexte).filter(
                        CahierTexte.school_id == target_school_id,
                        CahierTexte.classe_id == classe_obj.id,
                        CahierTexte.matiere_id == matiere_obj.id
                    ).all()

                    # Filtrage exact sur la date sélectionnée
                    entrees_jour = [
                        e for e in entrees_db 
                        if e.date and e.date.date() == date_insp
                    ]

                    st.markdown("---")
                    st.markdown(f"#### 📖 Enregistrement pour **{classe_insp}** en **{matiere_insp}** le **{date_insp.strftime('%d/%m/%Y')}**")

                    if not entrees_jour:
                        st.info(f"⚠️ Aucun cours n'a été enregistré pour cette classe et cette matière à la date du **{date_insp.strftime('%d/%m/%Y')}**.")
                    else:
                        for idx, ent in enumerate(entrees_jour):
                            with st.container():
                                st.markdown(f"**Séance #{idx + 1}** | Enseignant : `{ent.enseignant_username or 'Administration'}` | Durée : `{getattr(ent, 'duree', 1.0)}h`")
                                st.info(ent.contenu_realise or "Aucun contenu détaillé.")
                                if ent.difficultees:
                                    st.warning(f"**Difficultés / Remarques enseignant :** {ent.difficultees}")

                        # --- FORMULAIRE D'OBSERVATION DE L'INSPECTEUR ---
                        st.markdown("---")
                        with st.form("form_obs_inspecteur_cahier"):
                            st.markdown("#### ✍️ Formuler une Observation / Visa de l'Inspecteur")
                            st.markdown("Cette observation sera enregistrée et transmise à l'administration dans le journal de supervision du cahier de texte.")

                            texte_observation = st.text_area(
                                "Observations pédagogiques et instructions *",
                                placeholder="Ex: Cours conforme aux attentes pédagogiques, veiller à l'illustration graphique..."
                            )

                            submitted_obs = st.form_submit_button("Envoyer l'observation à l'administration", type="primary")
                            if submitted_obs:
                                if not texte_observation.strip():
                                    st.error("⚠️ Veuillez rédiger votre observation.")
                                else:
                                    action_log = f"Observation Inspection [{classe_insp} - {matiere_insp} du {date_insp.strftime('%d/%m/%Y')}] par {username} : {texte_observation.strip()}"
                                    
                                    nouveau_log = ActivityLog(
                                        school_id=target_school_id,
                                        timestamp=datetime.utcnow(),
                                        username=username,
                                        action=action_log,
                                        module="Supervision cahier",
                                        statut="Observation Validée"
                                    )
                                    db.add(nouveau_log)
                                    db.commit()

                                    st.success("✅ Observation enregistrée et transmise avec succès à l'administration !")
                                    st.rerun()

        with tab_insp2:
            st.markdown(f"### Tableau de Bord Global des Établissements ({cycle_en_cours})")
            ecoles = db.query(School).all()

            if not ecoles:
                st.info("Aucun établissement enregistré dans la plateforme multi-écoles.")
            else:
                data_global = []
                for ecole in ecoles:
                    nb_classes = db.query(Classe).filter(Classe.school_id == ecole.id, Classe.cycle == cycle_en_cours).count()
                    classes_ids = [c.id for c in db.query(Classe).filter(Classe.school_id == ecole.id, Classe.cycle == cycle_en_cours).all()]
                    nb_eleves = db.query(Eleve).filter(Eleve.school_id == ecole.id, Eleve.classe_id.in_(classes_ids)).count() if classes_ids else 0

                    data_global.append({
                        "Établissement": getattr(ecole, 'nom', 'École'),
                        "Cycle Actif": cycle_en_cours,
                        "Nombre de Classes": nb_classes,
                        "Effectif Total Élèves": nb_eleves,
                        "Statut Conformité": "Conforme"
                    })

                df_global = pd.DataFrame(data_global)
                st.dataframe(df_global, use_container_width=True)

                nouveau_log = ActivityLog(
                    school_id=target_school_id,
                    timestamp=datetime.utcnow(),
                    username=username,
                    action=f"Consultation du tableau de bord global d'inspection ({cycle_en_cours})",
                    module="Espace Inspection",
                    statut="Succès"
                )
                db.add(nouveau_log)
                db.commit()

    finally:
        db.close()

# Définition explicite des alias pour garantir la compatibilité avec le routeur app.py
def afficher_espace_inspection_academique():
    afficher_espace_inspection()

afficher_espace_inspection = afficher_espace_inspection
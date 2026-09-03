import streamlit as st
import pandas as pd
from datetime import datetime
from database.db_config import SessionLocal
from database.models import Classe, School, ActivityLog

def afficher_emploi_temps():
    st.subheader("📅 Gestion des Emplois du Temps")
    st.markdown("Planification hebdomadaire des cours par classe et cycle selon la grille horaire officielle (08h00 - 14h30 avec récréation 11h00 - 11h30).")
    st.markdown("---")

    school_id = st.session_state.get("school_id")
    is_super_admin = st.session_state.get("is_super_admin", False)
    school_name = st.session_state.get("school_name", "Établissement")
    cycle_en_cours = st.session_state.get("cycle_actif", "Collège")

    if not school_id and not is_super_admin:
        st.warning("⚠️ Veuillez vous connecter pour accéder à cette section.")
        return

    db = SessionLocal()
    try:
        tab1, tab2 = st.tabs(["📋 Consulter l'Emploi du Temps", "➕ Ajouter un Créneau"])

        # Isolation multi-écoles et multi-cycles pour les classes
        classes_query = db.query(Classe).filter(Classe.cycle == cycle_en_cours)
        if not is_super_admin and school_id:
            classes_query = classes_query.filter(Classe.school_id == school_id)
        classes_cycle = classes_query.all()

        # Initialisation du stockage en session state pour les emplois du temps dynamiques
        if "emplois_du_temps_data" not in st.session_state:
            st.session_state["emplois_du_temps_data"] = {}

        # Grille horaire officielle (08h00 - 14h30, avec récréation de 11h00 à 11h30)
        creneaux_horaires = [
            "08h00 - 09h00",
            "09h00 - 10h00",
            "10h00 - 11h00",
            "11h30 - 12h30",
            "12h30 - 13h30",
            "13h30 - 14h30"
        ]

        with tab1:
            st.markdown(f"### Emplois du Temps — **{school_name} ({cycle_en_cours})**")

            if not classes_cycle:
                st.info(f"Aucune classe enregistrée pour le cycle **{cycle_en_cours}** dans cet établissement.")
            else:
                noms_classes = [c.libelle for c in classes_cycle]
                classe_choisie = st.selectbox("Sélectionner la classe à consulter", noms_classes, key="consult_edt_classe")
                
                classe_obj = next((c for c in classes_cycle if c.libelle == classe_choisie), None)
                if classe_obj:
                    st.info(f"Emploi du temps pour la classe : **{classe_obj.libelle}** (Pause récréation : 11h00 - 11h30)")
                    
                    jours = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi"]
                    
                    # Récupération des données stockées pour cette école, cycle et classe
                    key_edt = f"{school_id}_{cycle_en_cours}_{classe_choisie}"
                    edt_dict = st.session_state["emplois_du_temps_data"].get(key_edt, {})

                    data_grille = []
                    for jour in jours:
                        ligne = {"Jour": jour}
                        for horaire in creneaux_horaires:
                            ligne[horaire] = edt_dict.get((jour, horaire), "—")
                        data_grille.append(ligne)

                    df_edt = pd.DataFrame(data_grille)
                    st.dataframe(df_edt, use_container_width=True)

        with tab2:
            st.markdown(f"### Planification d'un Créneau — **{school_name} ({cycle_en_cours})**")

            if not classes_cycle:
                st.warning(f"⚠️ Veuillez d'abord créer des classes pour le cycle **{cycle_en_cours}** dans le menu 'Classes & Tarifs'.")
            else:
                noms_classes = [c.libelle for c in classes_cycle]
                with st.form("form_add_creneau"):
                    col1, col2 = st.columns(2)
                    with col1:
                        classe_selectionnee = st.selectbox("Classe", noms_classes, key="form_edt_classe")
                        jour = st.selectbox("Jour de la semaine", ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi"])
                    with col2:
                        horaire = st.selectbox("Plage horaire", creneaux_horaires)
                        matiere = st.text_input("Matière / Cours (ou nom du vacataire)")

                    submitted = st.form_submit_button("Ajouter le créneau")
                    if submitted:
                        if not matiere:
                            st.error("⚠️ Veuillez indiquer la matière ou le cours.")
                        else:
                            target_school_id = school_id
                            if is_super_admin and not target_school_id:
                                ecole_defaut = db.query(School).first()
                                target_school_id = ecole_defaut.id if ecole_defaut else 1

                            key_edt = f"{target_school_id}_{cycle_en_cours}_{classe_selectionnee}"
                            if key_edt not in st.session_state["emplois_du_temps_data"]:
                                st.session_state["emplois_du_temps_data"][key_edt] = {}
                            
                            st.session_state["emplois_du_temps_data"][key_edt][(jour, horaire)] = matiere.strip().upper()

                            # Traçabilité dans le journal d'activité (avec l'heure locale exacte)
                            nouveau_log = ActivityLog(
                                school_id=target_school_id,
                                timestamp=datetime.now(),
                                username=st.session_state.get("username", "admin"),
                                action=f"Planification créneau EDT : {matiere} ({classe_selectionnee}, {jour} {horaire})",
                                module="Emploi du temps",
                                statut="Succès"
                            )
                            db.add(nouveau_log)
                            db.commit()

                            st.success(f"✅ Créneau de {matiere} ajouté avec succès pour {classe_selectionnee} ({jour}, {horaire}) !")
                            st.rerun()

    finally:
        db.close()

# Alias de compatibilité au cas où l'ancienne nomenclature est appelée
afficher_emploi_du_temps = afficher_emploi_temps
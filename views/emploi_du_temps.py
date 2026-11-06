from datetime import datetime
import io
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from database.db_config import SessionLocal
from database.models import ActivityLog, Classe, EmploiDuTemps, Matiere, Enseignant, School
import reportlab
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet


def afficher_emploi_temps():
    st.subheader("📅 Gestion des Emplois du Temps")
    st.markdown(
        "Planification hebdomadaire des cours par classe et cycle selon la "
        "grille horaire officielle (08h00 - 14h30 avec récréation 11h00 - 11h30)."
    )
    st.markdown("---")

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
        ecole_courante = None
        if school_id:
            ecole_courante = db.query(School).filter(School.id == school_id).first()
            if ecole_courante:
                school_name = ecole_courante.nom

        tab1, tab_global, tab2 = st.tabs([
            "📋 Consulter par Classe", 
            "📊 Vue Globale Établissement", 
            "➕ Ajouter un Créneau"
        ])

        classes_query = db.query(Classe).filter(Classe.cycle == cycle_en_cours)
        matieres_query = db.query(Matiere)
        enseignants_query = db.query(Enseignant)

        if not is_super_admin and school_id:
            classes_query = classes_query.filter(Classe.school_id == school_id)
            matieres_query = matieres_query.filter(Matiere.school_id == school_id)
            enseignants_query = enseignants_query.filter(Enseignant.school_id == school_id)
            
        classes_cycle = classes_query.all()
        matieres_disponibles = matieres_query.all()
        enseignants_disponibles = enseignants_query.all()

        heures_libelles = [
            ("1ère Heure", "08h00 - 09h00"),
            ("2ème Heure", "09h00 - 10h00"),
            ("3ème Heure", "10h00 - 11h00"),
            ("Récréation", "11h00 - 11h30"),
            ("4ème Heure", "11h30 - 12h30"),
            ("5ème Heure", "12h30 - 13h30"),
            ("6ème Heure", "13h30 - 14h30"),
        ]
        
        creneaux_horaires = [
            "08h00 - 09h00",
            "09h00 - 10h00",
            "10h00 - 11h00",
            "11h00 - 11h30",
            "11h30 - 12h30",
            "12h30 - 13h30",
            "13h30 - 14h30",
        ]
        
        creneaux_cours_uniquement = [
            "08h00 - 09h00",
            "09h00 - 10h00",
            "10h00 - 11h00",
            "11h30 - 12h30",
            "12h30 - 13h30",
            "13h30 - 14h30",
        ]

        jours = [
            "Lundi",
            "Mardi",
            "Mercredi",
            "Jeudi",
            "Vendredi",
            "Samedi",
        ]

        # ==========================================
        # ONGLET 1 : CONSULTATION PAR CLASSE
        # ==========================================
        with tab1:
            st.markdown(
                f"### Emplois du Temps — **{school_name} ({cycle_en_cours})** | Année Scolaire : **{annee_en_cours}**"
            )

            if not classes_cycle:
                st.info(
                    f"Aucune classe enregistrée pour le cycle **{cycle_en_cours}** "
                    "dans cet établissement."
                )
            else:
                noms_classes = [c.libelle for c in classes_cycle]
                classe_choisie = st.selectbox(
                    "Sélectionner la classe à consulter",
                    noms_classes,
                    key="consult_edt_classe",
                )

                classe_obj = next(
                    (c for c in classes_cycle if c.libelle == classe_choisie),
                    None,
                )
                if classe_obj:
                    query_edt = db.query(EmploiDuTemps).filter(
                        EmploiDuTemps.school_id == school_id,
                        EmploiDuTemps.classe == classe_choisie
                    ).all()

                    edt_dict = {}
                    for item in query_edt:
                        edt_dict[(item.jour, item.heure)] = {
                            "matiere": item.matiere,
                            "prof": item.enseignant,
                            "contact": getattr(item, "contact", "N/D") or "N/D"
                        }

                    data_grille = []
                    for jour in jours:
                        ligne = {"Jour": jour}
                        for horaire in creneaux_horaires:
                            if horaire == "11h00 - 11h30":
                                ligne[horaire] = "☕ Pause"
                            else:
                                val_creneau = edt_dict.get((jour, horaire), None)
                                if val_creneau:
                                    ligne[horaire] = (
                                        f"{val_creneau['matiere']}\nProf: {val_creneau['prof']}\n{val_creneau['contact']}"
                                    )
                                else:
                                    ligne[horaire] = ""
                        data_grille.append(ligne)

                    df_edt = pd.DataFrame(data_grille)

                    col_exp1, col_exp2, col_exp3, col_col_vide = st.columns(
                        [1.3, 1.3, 1.3, 3.5]
                    )

                    with col_exp1:
                        output_excel = io.BytesIO()
                        with pd.ExcelWriter(output_excel, engine="openpyxl") as writer:
                            df_edt.to_excel(
                                writer,
                                index=False,
                                sheet_name=f"EDT_{classe_choisie}",
                            )
                        excel_data = output_excel.getvalue()
                        st.download_button(
                            label="📥 Excel",
                            data=excel_data,
                            file_name=f"Emploi_du_Temps_{classe_choisie}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        )

                    with col_exp2:
                        pdf_buffer = io.BytesIO()
                        doc = SimpleDocTemplate(
                            pdf_buffer,
                            pagesize=landscape(A4),
                            rightMargin=20,
                            leftMargin=20,
                            topMargin=25,
                            bottomMargin=40,
                        )

                        elements = []
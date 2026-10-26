from datetime import datetime, date, timedelta
import io
import sqlalchemy as sa
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from database.db_config import SessionLocal, engine
from database.models import Classe, Matiere, Evaluation, ActivityLog, School

# Importation sécurisée de ReportLab
PDF_AVAILABLE = True
try:
    import reportlab
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
except ImportError:
    PDF_AVAILABLE = False

JOURS_FR = {
    0: "Lundi",
    1: "Mardi",
    2: "Mercredi",
    3: "Jeudi",
    4: "Vendredi",
    5: "Samedi",
    6: "Dimanche"
}

def afficher_planification_evaluations():
    st.subheader("📋 Planification Avancée des Évaluations (SIA)")
    st.markdown("Calendrier officiel des contrôles, compositions et examens blancs avec grille matricielle globale pour toutes les classes.")
    st.markdown("---")

    # --- MIGRATION AUTOMATIQUE DE LA COLONNE SEMESTRE ---
    try:
        with engine.connect() as conn:
            conn.execute(sa.text("ALTER TABLE evaluations ADD COLUMN IF NOT EXISTS semestre VARCHAR(50) DEFAULT 'Semestre 1';"))
            conn.commit()
    except Exception:
        pass

    school_id = st.session_state.get("school_id")
    is_super_admin = st.session_state.get("is_super_admin", False)
    school_name = st.session_state.get("school_name", "Établissement")
    cycle_en_cours = st.session_state.get("cycle_actif", "Collège")
    username = st.session_state.get("username", "admin")
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
        classes_dict_map = {c.id: c.libelle for c in classes_cycle}
        matieres_dict_map = {m.id: (m.libelle if hasattr(m, 'libelle') else getattr(m, 'nom', 'N/A')) for m in matieres_disponibles}

        tab1, tab2 = st.tabs(["📅 Calendrier & Suivi des Évaluations", "⚡ Grille Globale (Toutes les Classes)"])

        with tab1:
            st.markdown(f"### Calendrier Officiel ({annee_en_cours}) — **{school_name} ({cycle_en_cours})**")
            
            col_filt1, col_filt2 = st.columns(2)
            with col_filt1:
                classe_filtre = st.selectbox("Filtrer par classe", ["Toutes les classes"] + noms_classes, key="filtre_eval_classe")
            with col_filt2:
                semestre_filtre = st.selectbox("Filtrer par semestre", ["Tous les semestres", "Semestre 1", "Semestre 2"], key="filtre_eval_semestre")
            
            eval_query = db.query(Evaluation).join(Classe, Evaluation.classe_id == Classe.id).filter(Classe.cycle == cycle_en_cours)
            if not is_super_admin and school_id:
                eval_query = eval_query.filter(Evaluation.school_id == school_id)
            if classe_filtre != "Toutes les classes":
                eval_query = eval_query.filter(Classe.libelle == classe_filtre)
            if semestre_filtre != "Tous les semestres" and hasattr(Evaluation, 'semestre'):
                eval_query = eval_query.filter(Evaluation.semestre == semestre_filtre)
            
            evaluations_list = eval_query.all()

            if not evaluations_list:
                st.info("Aucune évaluation programmée pour le moment dans cet établissement.")
            else:
                data_tableau = []
                for ev in evaluations_list:
                    classe_lib = classes_dict_map.get(ev.classe_id, "N/A")
                    mat_lib = matieres_dict_map.get(ev.matiere_id, "N/A") if ev.matiere_id else "N/A"
                    data_tableau.append({
                        "ID": ev.id,
                        "Semestre": getattr(ev, 'semestre', 'Semestre 1'),
                        "Date": ev.date_evaluation.strftime("%d/%m/%Y") if ev.date_evaluation else "",
                        "Horaire": f"{ev.heure_debut} - {ev.heure_fin}",
                        "Classe": classe_lib,
                        "Matière": mat_lib,
                        "Type": ev.type_evaluation,
                        "Intitulé": ev.intitule,
                        "Salle": ev.salle or "Non assignée",
                        "Surveillant": ev.surveillant or "Non assigné",
                        "Statut": ev.statut
                    })
            
                df_evals = pd.DataFrame(data_tableau)

                col_exp1, col_exp2, col_exp3, _ = st.columns([1.3, 1.3, 1.3, 3])

                with col_exp1:
                    output_excel = io.BytesIO()
                    with pd.ExcelWriter(output_excel, engine="openpyxl") as writer:
                        df_evals.to_excel(writer, index=False, sheet_name=f"Evaluations_{annee_en_cours}")
                    excel_data = output_excel.getvalue()
                    st.download_button(
                        label="📥 Excel",
                        data=excel_data,
                        file_name=f"Calendrier_Evaluations_{annee_en_cours}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="btn_excel_tab1"
                    )

                with col_exp2:
                    if PDF_AVAILABLE:
                        pdf_buffer = io.BytesIO()
                        doc = SimpleDocTemplate(pdf_buffer, pagesize=landscape(A4), rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=50)
                        elements = []
                        styles = getSampleStyleSheet()
                        title_style = ParagraphStyle("TitleStyle", parent=styles["Heading1"], fontSize=14, textColor=colors.HexColor("#1e3a8a"), alignment=1, spaceAfter=15)
                        elements.append(Paragraph(f"CALENDRIER OFFICIEL DES ÉVALUATIONS ({annee_en_cours}) — {school_name} ({cycle_en_cours})", title_style))
                        elements.append(Spacer(1, 10))

                        df_pdf = df_evals.drop(columns=["ID"]) if "ID" in df_evals.columns else df_evals
                        table_data = [list(df_pdf.columns)]
                        for _, row in df_pdf.iterrows():
                            table_data.append([str(val) for val in row])

                        col_widths = [780 / len(df_pdf.columns)] * len(df_pdf.columns)
                        t = Table(table_data, colWidths=col_widths)
                        t.setStyle(TableStyle([
                            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1e3a8a")),
                            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                            ('FONTSIZE', (0,0), (-1,0), 8),
                            ('BOTTOMPADDING', (0,0), (-1,0), 8),
                            ('BACKGROUND', (0,1), (-1,-1), colors.HexColor("#f8fafc")),
                            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
                            ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
                            ('FONTSIZE', (0,1), (-1,-1), 8),
                            ('BOTTOMPADDING', (0,1), (-1,-1), 5),
                            ('TOPPADDING', (0,1), (-1,-1), 5),
                        ]))
                        elements.append(t)
                        doc.build(elements)
                        pdf_data = pdf_buffer.getvalue()

                        st.download_button(label="📥 PDF", data=pdf_data, file_name=f"Calendrier_Evaluations_{annee_en_cours}.pdf", mime="application/pdf", key="btn_pdf_tab1")
                    else:
                        st.info("Export PDF indisponible (installez reportlab)")

                with col_exp3:
                    components.html('<button onclick="parent.window.print()" style="background-color: #2563eb; color: white; border: none; padding: 0.45rem 1rem; font-size: 0.85rem; font-weight: 500; border-radius: 6px; cursor: pointer; box-shadow: 0 2px 4px rgba(0,0,0,0.2); font-family: sans-serif;">🖨️ Imprimer</button>', height=40)

                st.markdown("<br>", unsafe_allow_html=True)
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
            st.markdown(f"### ⚡ Grille Matricielle Globale (Toutes les Classes) — **{school_name} ({cycle_en_cours})**")
            st.markdown("Planifiez les évaluations pour l'ensemble des classes de l'établissement dans un tableau unifié (Lundi au Dimanche).")

            col_g1, col_g2 = st.columns(2)
            with col_g1:
                semestre_eval = st.selectbox("Sélectionner le semestre", ["Semestre 1", "Semestre 2"], key="grille_semestre_matrix_global")
            with col_g2:
                type_eval = st.selectbox("Type d'évaluation", ["Interro 1", "Interro 2", "Devoir 1", "Devoir 2", "Compo"], key="grille_type_matrix_global")

            date_debut_semaine = st.date_input("Date de début de la session d'évaluation (Lundi de référence)", value=date.today(), key="grille_date_debut_global")
            
            # Génération des 7 jours (Lundi à Dimanche)
            jours_colonnes = []
            dates_jours = {}
            for i in range(7):
                d_courante = date_debut_semaine + timedelta(days=i)
                nom_jour_fr = JOURS_FR[d_courante.weekday()]
                lib_jour = f"{nom_jour_fr} {d_courante.strftime('%d/%m')}"
                jours_colonnes.append(lib_jour)
                dates_jours[lib_jour] = d_courante

            # Construction des lignes combinant Classe et Créneaux par défaut
            creneaux_defaut = ["08h00 - 10h00", "10h30 - 12h30", "15h00 - 17h00"]
            matrice_data = []

            target_school_id = school_id if school_id else (ecole_courante.id if ecole_courante else 1)

            for classe_obj in classes_cycle:
                # Matières spécifiques à cette classe
                m_list = db.query(Matiere).filter(Matiere.classe_id == classe_obj.id).all()
                noms_mats_classe = ["---"] + sorted(list(set([(m.libelle if hasattr(m, 'libelle') and m.libelle else getattr(m, 'nom', '')).strip().title() for m in m_list])))

                for heure in creneaux_defaut:
                    h_deb = heure.split(" - ")[0]
                    ligne = {
                        "Classe": classe_obj.libelle,
                        "Créneau Horaire": heure
                    }
                    for j in jours_colonnes:
                        d_eval_cib = dates_jours[j]
                        
                        existant = db.query(Evaluation).filter(
                            Evaluation.school_id == target_school_id,
                            Evaluation.classe_id == classe_obj.id,
                            Evaluation.semestre == semestre_eval,
                            Evaluation.type_evaluation == type_eval,
                            Evaluation.date_evaluation == d_eval_cib,
                            Evaluation.heure_debut == h_deb
                        ).first()
                        
                        matiere_affectee = "---"
                        if existant and existant.matiere_id:
                            m_trouvee = db.query(Matiere).filter(Matiere.id == existant.matiere_id).first()
                            if m_trouvee:
                                matiere_affectee = (m_trouvee.libelle if hasattr(m_trouvee, 'libelle') and m_trouvee.libelle else getattr(m_trouvee, 'nom', '')).strip().title()
                        
                        ligne[j] = matiere_affectee if matiere_affectee in noms_mats_classe else "---"
                    matrice_data.append(ligne)

            df_matrice_grid = pd.DataFrame(matrice_data)

            # Configuration des colonnes de l'éditeur interactif
            column_config_grid = {
                "Classe": st.column_config.TextColumn("Classe", disabled=True),
                "Créneau Horaire": st.column_config.TextColumn("Créneau Horaire", required=True)
            }
            # Pour chaque jour, on met une selectbox globale avec toutes les matières du cycle ou de l'école
            toutes_matieres_cycle = ["---"] + sorted(list(set([(m.libelle if hasattr(m, 'libelle') and m.libelle else getattr(m, 'nom', '')).strip().title() for m in matieres_disponibles])))
            for j in jours_colonnes:
                column_config_grid[j] = st.column_config.SelectboxColumn(
                    j,
                    options=toutes_matieres_cycle,
                    required=True
                )

            st.markdown("#### 🗓️ Emploi du Temps Global des Évaluations (Toutes les Classes)")
            edited_grid_df = st.data_editor(
                df_matrice_grid,
                column_config=column_config_grid,
                num_rows="dynamic",
                hide_index=True,
                use_container_width=True,
                key="editor_global_classes_heures"
            )

            if st.button("💾 Enregistrer la grille globale pour toutes les classes", type="primary", key="btn_save_global_grid"):
                enregistrements_compteur = 0

                for _, row in edited_grid_df.iterrows():
                    nom_classe_ligne = str(row["Classe"]).strip()
                    classe_obj_ligne = db.query(Classe).filter(Classe.libelle == nom_classe_ligne, Classe.school_id == target_school_id).first()
                    
                    if not classe_obj_ligne:
                        continue

                    heure_creneau = str(row["Créneau Horaire"]).strip()
                    if " - " in heure_creneau:
                        h_deb, h_fin = heure_creneau.split(" - ", 1)
                    else:
                        h_deb, h_fin = heure_creneau, "10h00"

                    for j in jours_colonnes:
                        matiere_choisie_cellule = row[j]
                        d_eval_cellule = dates_jours[j]

                        if matiere_choisie_cellule and matiere_choisie_cellule != "---":
                            mat_obj_cell = db.query(Matiere).filter(
                                ((Matiere.libelle == matiere_choisie_cellule) | (Matiere.nom == matiere_choisie_cellule)),
                                Matiere.classe_id == classe_obj_ligne.id,
                                Matiere.school_id == target_school_id
                            ).first()

                            if mat_obj_cell:
                                eval_existante = db.query(Evaluation).filter(
                                    Evaluation.school_id == target_school_id,
                                    Evaluation.classe_id == classe_obj_ligne.id,
                                    Evaluation.semestre == semestre_eval,
                                    Evaluation.type_evaluation == type_eval,
                                    Evaluation.date_evaluation == d_eval_cellule,
                                    Evaluation.heure_debut == h_deb
                                ).first()

                                if eval_existante:
                                    eval_existante.matiere_id = mat_obj_cell.id
                                    eval_existante.heure_fin = h_fin
                                    eval_existante.intitule = f"{type_eval} de {matiere_choisie_cellule}"
                                else:
                                    nouvelle_eval = Evaluation(
                                        school_id=target_school_id,
                                        cycle=cycle_en_cours,
                                        classe_id=classe_obj_ligne.id,
                                        matiere_id=mat_obj_cell.id,
                                        semestre=semestre_eval,
                                        type_evaluation=type_eval,
                                        intitule=f"{type_eval} de {matiere_choisie_cellule}",
                                        date_evaluation=d_eval_cellule,
                                        heure_debut=h_deb,
                                        heure_fin=h_fin,
                                        salle="Salle Principale",
                                        surveillant="",
                                        statut="Brouillon",
                                        cree_par=username
                                    )
                                    db.add(nouvelle_eval)
                                enregistrements_compteur += 1

                db.commit()
                st.success(f"✅ Grille globale enregistrée avec succès ! {enregistrements_compteur} affectations mises à jour pour l'ensemble des classes.")
                st.rerun()

    finally:
        db.close()

# Alias de compatibilité
afficher_planification_des_evaluations = afficher_planification_evaluations
from datetime import datetime, date, time, timedelta
import io
import sqlalchemy as sa
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from database.db_config import SessionLocal, engine
from database.models import Classe, Matiere, Evaluation, ActivityLog, School
import reportlab
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def afficher_planification_evaluations():
    st.subheader("📋 Planification Avancée des Évaluations (SIA)")
    st.markdown("Calendrier officiel des contrôles, compositions et examens blancs avec workflow de validation, gestion des ressources et contrôle anti-collision.")
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

        tab1, tab2 = st.tabs(["📅 Calendrier & Suivi des Évaluations", "⚡ Saisie Rapide en Grille"])

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

                # --- BOUTONS D'EXPORTATION (EXCEL, PDF A4 PAYSAGE & IMPRESSION) ---
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
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

                with col_exp2:
                    pdf_buffer = io.BytesIO()
                    doc = SimpleDocTemplate(
                        pdf_buffer,
                        pagesize=landscape(A4),
                        rightMargin=30,
                        leftMargin=30,
                        topMargin=30,
                        bottomMargin=50
                    )

                    elements = []
                    styles = getSampleStyleSheet()

                    title_style = ParagraphStyle(
                        "TitleStyle",
                        parent=styles["Heading1"],
                        fontSize=14,
                        textColor=colors.HexColor("#1e3a8a"),
                        alignment=1,
                        spaceAfter=15
                    )

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

                    def add_footer(canvas, doc_obj):
                        canvas.saveState()
                        footer_y = 22
                        s_nom = ecole_courante.nom if ecole_courante else school_name
                        s_adr = ecole_courante.adresse if ecole_courante and ecole_courante.adresse else "Niamey - Niger"
                        s_cont = ecole_courante.contacts if ecole_courante and ecole_courante.contacts else "N/D"
                        s_dev = ecole_courante.devise if ecole_courante and ecole_courante.devise else "Excellence - Persévérance - Réussite"

                        footer_text = f"<b>{s_nom}</b> | Adresse : {s_adr} | Contacts : {s_cont} | Devise : <i>{s_dev}</i>"
                        footer_style = ParagraphStyle(
                            "FooterStyle",
                            parent=styles["Normal"],
                            fontSize=8,
                            textColor=colors.HexColor("#475569"),
                            alignment=1
                        )
                        p = Paragraph(footer_text, footer_style)
                        p.wrap(doc_obj.pagesize[0] - 60, footer_y)
                        p.drawOn(canvas, 30, footer_y)
                        canvas.restoreState()

                    doc.build(elements, onFirstPage=add_footer)
                    pdf_data = pdf_buffer.getvalue()

                    st.download_button(
                        label="📥 PDF",
                        data=pdf_data,
                        file_name=f"Calendrier_Evaluations_{annee_en_cours}.pdf",
                        mime="application/pdf"
                    )

                with col_exp3:
                    components.html(
                        """
                        <button onclick="parent.window.print()" style="
                            background-color: #2563eb;
                            color: white;
                            border: none;
                            padding: 0.45rem 1rem;
                            font-size: 0.85rem;
                            font-weight: 500;
                            border-radius: 6px;
                            cursor: pointer;
                            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
                            font-family: sans-serif;
                        ">🖨️ Imprimer</button>
                        """,
                        height=40,
                    )

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
            st.markdown(f"### ⚡ Saisie Rapide en Grille ({annee_en_cours}) — **{school_name} ({cycle_en_cours})**")
            st.markdown("Renseignez directement les informations d'évaluation pour plusieurs matières simultanément sous forme de tableau interactif.")

            if not matieres_disponibles:
                st.warning("⚠️ Veuillez d'abord créer des matières dans le module 'Matières & Coeffs' pour pouvoir planifier une évaluation.")
            else:
                col_g1, col_g2, col_g3 = st.columns(3)
                with col_g1:
                    classe_choisie = st.selectbox("Classe concernée (Grille)", noms_classes, key="grille_classe")
                with col_g2:
                    semestre_eval = st.selectbox("Sélectionner le semestre (Grille)", ["Semestre 1", "Semestre 2"], key="grille_semestre")
                with col_g3:
                    type_eval = st.selectbox("Type d'évaluation (Global)", ["Interro 1", "Interro 2", "Devoir 1", "Devoir 2", "Compo"], key="grille_type")

                lignes_grille = []
                for m in matieres_disponibles:
                    mat_lib = m.libelle if hasattr(m, 'libelle') else getattr(m, 'nom', 'Matière')
                    lignes_grille.append({
                        "Matière": mat_lib,
                        "Intitulé": f"{type_eval} de {mat_lib}",
                        "Date": date.today(),
                        "Heure Début": "08h00",
                        "Heure Fin": "10h00",
                        "Salle": "Salle Principale",
                        "Surveillant": ""
                    })

                df_saisie = pd.DataFrame(lignes_grille)

                st.markdown("#### ✏️ Tableau d'édition rapide (Modifiable)")
                df_modifie = st.data_editor(
                    df_saisie,
                    num_rows="dynamic",
                    use_container_width=True,
                    key="table_saisie_evals"
                )

                if st.button("💾 Enregistrer toutes les évaluations de la grille", type="primary"):
                    target_school_id = school_id
                    if is_super_admin and not target_school_id:
                        ecole_defaut = db.query(School).first()
                        target_school_id = ecole_defaut.id if ecole_defaut else 1

                    classe_obj = db.query(Classe).filter(Classe.libelle == classe_choisie, Classe.school_id == target_school_id).first()
                    
                    if not classe_obj:
                        st.error("❌ Erreur : Classe introuvable en base de données.")
                    else:
                        success_count = 0
                        for _, row in df_modifie.iterrows():
                            mat_nom = row["Matière"]
                            matiere_obj = db.query(Matiere).filter((Matiere.libelle == mat_nom) | (Matiere.nom == mat_nom), Matiere.school_id == target_school_id).first()
                            
                            titre_eval = str(row["Intitulé"]).strip()
                            date_ev = row["Date"]
                            h_debut = str(row["Heure Début"]).strip()
                            h_fin = str(row["Heure Fin"]).strip()
                            salle_val = str(row["Salle"]).strip()
                            surv_val = str(row["Surveillant"]).strip()

                            if not titre_eval or not mat_nom:
                                continue

                            conflit = db.query(Evaluation).filter(
                                Evaluation.school_id == target_school_id,
                                Evaluation.classe_id == classe_obj.id,
                                Evaluation.date_evaluation == date_ev,
                                Evaluation.heure_debut == h_debut
                            ).first()

                            if not conflit:
                                nouvelle_eval = Evaluation(
                                    school_id=target_school_id,
                                    cycle=cycle_en_cours,
                                    classe_id=classe_obj.id,
                                    matiere_id=matiere_obj.id if matiere_obj else None,
                                    semestre=semestre_eval,
                                    type_evaluation=type_eval,
                                    intitule=titre_eval,
                                    date_evaluation=date_ev,
                                    heure_debut=h_debut,
                                    heure_fin=h_fin,
                                    salle=salle_val,
                                    surveillant=surv_val,
                                    statut="Brouillon",
                                    cree_par=username
                                )
                                db.add(nouvelle_eval)
                                success_count += 1

                        if success_count > 0:
                            nouveau_log = ActivityLog(
                                school_id=target_school_id,
                                timestamp=datetime.now(),
                                username=username,
                                action=f"Planification en masse ({semestre_eval}) : {success_count} évaluations pour {classe_choisie}",
                                module="Planification des Évaluations",
                                statut="Succès"
                            )
                            db.add(nouveau_log)
                            db.commit()
                            st.success(f"🎉 {success_count} évaluations programmées et enregistrées avec succès en mode grille pour la classe de **{classe_choisie}** !")
                            st.rerun()
                        else:
                            st.warning("⚠️ Aucune nouvelle évaluation valide n'a pu être enregistrée (vérifiez les conflits d'horaires ou les champs vides).")

    finally:
        db.close()

# Alias de compatibilité
afficher_planification_des_evaluations = afficher_planification_evaluations
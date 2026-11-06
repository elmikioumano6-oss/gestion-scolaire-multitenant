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

        tab1, tab2 = st.tabs(["📅 Calendrier & Suivi des Évaluations", "⚡ Grille Matricielle (Par Classes & Sessions)"])

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

                col_exp1, col_exp2, _, _ = st.columns([1.3, 1.3, 3, 3])

                with col_exp1:
                    output_excel = io.BytesIO()
                    with pd.ExcelWriter(output_excel, engine="openpyxl") as writer:
                        df_export = df_evals.drop(columns=["ID"]) if "ID" in df_evals.columns else df_evals
                        df_export.to_excel(writer, index=False, sheet_name=f"Evaluations_{annee_en_cours}")
                        
                        # --- AJUSTEMENT AUTOMATIQUE DES LARGEURS DE COLONNES ---
                        worksheet = writer.sheets[f"Evaluations_{annee_en_cours}"]
                        for col in worksheet.columns:
                            max_len = max(len(str(cell.value or '')) for cell in col)
                            col_letter = col[0].column_letter
                            worksheet.column_dimensions[col_letter].width = max(max_len + 4, 12)

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
                            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                            ('FONTSIZE', (0,0), (-1,0), 9),
                            ('BOTTOMPADDING', (0,0), (-1,0), 6),
                            ('BACKGROUND', (0,1), (-1,-1), colors.HexColor("#f8fafc")),
                            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
                            ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
                            ('FONTSIZE', (0,1), (-1,-1), 8)
                        ]))
                        elements.append(t)
                        doc.build(elements)
                        pdf_data = pdf_buffer.getvalue()
                        st.download_button(
                            label="📥 PDF",
                            data=pdf_data,
                            file_name=f"Calendrier_Evaluations_{annee_en_cours}.pdf",
                            mime="application/pdf",
                            key="btn_pdf_tab1"
                        )
                
                st.dataframe(df_evals.drop(columns=["ID"]) if "ID" in df_evals.columns else df_evals, use_container_width=True)

        with tab2:
            st.markdown(f"### ⚡ Grille Matricielle des Évaluations — **{school_name} ({cycle_en_cours})**")
            st.markdown("Vue croisée par date/créneau horaire (lignes) et par classe (colonnes), similaire au modèle officiel Word.")

            eval_query_all = db.query(Evaluation).join(Classe, Evaluation.classe_id == Classe.id).filter(Classe.cycle == cycle_en_cours)
            if not is_super_admin and school_id:
                eval_query_all = eval_query_all.filter(Evaluation.school_id == school_id)
            evals_matrice = eval_query_all.all()

            if not evals_matrice:
                st.info("Aucune évaluation enregistrée pour alimenter la grille matricielle.")
            else:
                matrice_dict = {}
                classes_actives_set = sorted(list(set(classes_dict_map.values())))

                for ev in evals_matrice:
                    date_str = ev.date_evaluation.strftime("%d/%m/%Y") if ev.date_evaluation else "Date N/C"
                    horaire_str = f"{ev.heure_debut} - {ev.heure_fin}"
                    session_key = (date_str, horaire_str)
                    
                    classe_lib = classes_dict_map.get(ev.classe_id, "Inconnue")
                    mat_lib = matieres_dict_map.get(ev.matiere_id, "Matière N/C") if ev.matiere_id else "Matière N/C"
                    
                    if session_key not in matrice_dict:
                        matrice_dict[session_key] = {c: [] for c in classes_actives_set}
                    
                    if classe_lib in matrice_dict[session_key]:
                        matrice_dict[session_key][classe_lib].append(mat_lib)

                lignes_grille = []
                for (date_val, horaire_val), classes_map in sorted(matrice_dict.items()):
                    row_data = {"Date & Session": f"{date_val} ({horaire_val})"}
                    for c_nom in classes_actives_set:
                        matieres_du_creneau = classes_map.get(c_nom, [])
                        row_data[c_nom] = " - " + " / ".join(matieres_du_creneau) if matieres_du_creneau else ""
                    lignes_grille.append(row_data)

                df_grille = pd.DataFrame(lignes_grille)
                st.dataframe(df_grille, use_container_width=True)

    finally:
        db.close()

afficher_planification_evaluations = afficher_planification_evaluations
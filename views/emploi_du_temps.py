from datetime import datetime
import io
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from database.db_config import SessionLocal
from database.models import ActivityLog, Classe, EmploiDuTemps, School
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
        if not is_super_admin and school_id:
            classes_query = classes_query.filter(Classe.school_id == school_id)
        classes_cycle = classes_query.all()

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
                    # Chargement persistant depuis la table SQLAlchemy EmploiDuTemps
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
                        styles = getSampleStyleSheet()

                        title_style = ParagraphStyle(
                            "TitleStyle",
                            parent=styles["Heading1"],
                            fontSize=13,
                            textColor=colors.HexColor("#1e3a8a"),
                            alignment=1,
                            spaceAfter=10,
                        )

                        elements.append(
                            Paragraph(
                                f"EMPLOI DU TEMPS OFFICIEL ({annee_en_cours}) — CLASSE : {classe_choisie} ({school_name})",
                                title_style,
                            )
                        )
                        elements.append(Spacer(1, 5))

                        cell_style = ParagraphStyle(
                            "CellPDF",
                            parent=styles["Normal"],
                            fontSize=7,
                            leading=9,
                            alignment=1,
                            textColor=colors.HexColor("#1e293b"),
                        )

                        header_cell_style = ParagraphStyle(
                            "HeaderCellPDF",
                            parent=styles["Normal"],
                            fontSize=7.5,
                            leading=10,
                            alignment=1,
                            textColor=colors.white,
                            fontName="Helvetica-Bold",
                        )

                        table_data_pdf = []
                        header_row = [Paragraph(str(col), header_cell_style) for col in df_edt.columns]
                        table_data_pdf.append(header_row)

                        for _, row in df_edt.iterrows():
                            row_cells = []
                            for val in row:
                                text_val = str(val) if val else ""
                                text_formatted = text_val.replace("\n", "<br/>")
                                row_cells.append(Paragraph(text_formatted, cell_style))
                            table_data_pdf.append(row_cells)

                        col_widths = [65] + [ (780 - 65) / len(creneaux_horaires) ] * len(creneaux_horaires)
                        row_heights = [35] + [45] * len(jours)

                        t_pdf = Table(table_data_pdf, colWidths=col_widths, rowHeights=row_heights)
                        t_pdf.setStyle(
                            TableStyle([
                                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a8a")),
                                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f8fafc")),
                                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                                ("TOPPADDING", (0, 0), (-1, -1), 4),
                            ])
                        )
                        elements.append(t_pdf)

                        def add_footer(canvas, doc_obj):
                            canvas.saveState()
                            footer_y = 15
                            s_nom = ecole_courante.nom if ecole_courante else school_name
                            s_adr = ecole_courante.adresse if ecole_courante and ecole_courante.adresse else "Niamey - Niger"
                            s_cont = ecole_courante.contacts if ecole_courante and ecole_courante.contacts else "N/D"
                            s_dev = ecole_courante.devise if ecole_courante and ecole_courante.devise else "Excellence - Persévérance - Réussite"

                            footer_text = f"<b>{s_nom}</b> | Adresse : {s_adr} | Contacts : {s_cont} | Devise : <i>{s_dev}</i>"
                            footer_style = ParagraphStyle(
                                "FooterStyle",
                                parent=styles["Normal"],
                                fontSize=7.5,
                                textColor=colors.HexColor("#475569"),
                                alignment=1,
                            )
                            p = Paragraph(footer_text, footer_style)
                            p.wrap(doc_obj.pagesize[0] - 40, footer_y)
                            p.drawOn(canvas, 20, footer_y)
                            canvas.restoreState()

                        doc.build(elements, onFirstPage=add_footer)
                        pdf_data = pdf_buffer.getvalue()

                        st.download_button(
                            label="📥 PDF",
                            data=pdf_data,
                            file_name=f"Emploi_du_Temps_{classe_choisie}.pdf",
                            mime="application/pdf",
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

                    lignes_tbody = ""
                    for jour in jours:
                        lignes_tbody += f"<tr><td>{jour}</td>"
                        skip_slots = 0
                        for i, horaire in enumerate(creneaux_horaires):
                            if skip_slots > 0:
                                skip_slots -= 1
                                continue

                            if horaire == "11h00 - 11h30":
                                lignes_tbody += '<td class="pause-col">☕ Pause</td>'
                                continue

                            val_creneau = edt_dict.get((jour, horaire), None)
                            if val_creneau:
                                span = 1
                                for next_h in creneaux_horaires[i+1:]:
                                    if next_h == "11h00 - 11h30":
                                        break
                                    next_val = edt_dict.get((jour, next_h), None)
                                    if next_val == val_creneau:
                                        span += 1
                                    else:
                                        break
                                
                                skip_slots = span - 1
                                colspan_attr = f' colspan="{span}"' if span > 1 else ''

                                lignes_tbody += f"""
                                <td{colspan_attr}>
                                    <div style="color: #34d399; font-weight: 700; font-size: 0.85rem; margin-bottom: 3px;">{val_creneau['matiere']}</div>
                                    <div style="font-size: 0.75rem; color: #94a3b8; margin-bottom: 2px;">👨‍🏫 {val_creneau['prof']}</div>
                                    <div style="font-size: 0.7rem; color: #60a5fa;">📞 {val_creneau['contact']}</div>
                                </td>
                                """
                            else:
                                lignes_tbody += "<td></td>"
                        lignes_tbody += "</tr>"

                    html_table = f"""
                    <!DOCTYPE html>
                    <html>
                    <head>
                    <meta charset="utf-8">
                    <style>
                        body {{
                            background-color: #0e1117;
                            color: #f3f4f6;
                            font-family: sans-serif;
                            margin: 0;
                            padding: 0;
                        }}
                        .edt-container {{
                            background-color: #0e1117;
                            padding: 0.5rem;
                            border-radius: 12px;
                            border: 1px solid rgba(255, 255, 255, 0.1);
                        }}
                        .edt-header {{
                            display: flex;
                            justify-content: space-between;
                            align-items: center;
                            margin-bottom: 1.2rem;
                            border-bottom: 2px solid #1f2937;
                            padding-bottom: 0.8rem;
                        }}
                        .edt-title {{
                            font-size: 1.1rem;
                            font-weight: 600;
                            color: #f3f4f6;
                        }}
                        .edt-badge-repot {{
                            background: #3b82f6;
                            color: white;
                            padding: 0.4rem 0.8rem;
                            border-radius: 20px;
                            font-size: 0.8rem;
                            font-weight: 500;
                        }}
                        .styled-table {{
                            width: 100%;
                            border-collapse: collapse;
                            border-radius: 8px;
                            overflow: hidden;
                            border: 1px solid #2d3748;
                        }}
                        .styled-table th {{
                            background-color: #1a202c;
                            color: #e2e8f0;
                            text-align: center;
                            padding: 12px 8px;
                            font-size: 0.85rem;
                            border-bottom: 2px solid #4a5568;
                        }}
                        .styled-table td {{
                            background-color: #111827;
                            color: #cbd5e0;
                            text-align: center;
                            padding: 12px 8px;
                            font-size: 0.8rem;
                            border-bottom: 1px solid #1f2937;
                            border-right: 1px solid #1f2937;
                            vertical-align: middle;
                            height: 65px;
                            word-break: break-word;
                        }}
                        .styled-table td:first-child {{
                            font-weight: 600;
                            color: #60a5fa;
                            background-color: #161e2e;
                            width: 90px;
                        }}
                        .pause-col {{
                            background-color: #18212f !important;
                            color: #9ca3af !important;
                            font-style: italic;
                        }}
                    </style>
                    </head>
                    <body>
                    <div class="edt-container">
                        <div class="edt-header">
                            <div class="edt-title">📌 Emploi du temps officiel ({annee_en_cours}) : <span style="color: #60a5fa;">{classe_choisie}</span></div>
                            <div class="edt-badge-repot">☕ Pause récréative : 11h00 - 11h30</div>
                        </div>
                        <table class="styled-table">
                            <thead>
                                <tr>
                                    <th>Jour</th>
                                    <th>08h00 - 09h00</th>
                                    <th>09h00 - 10h00</th>
                                    <th>10h00 - 11h00</th>
                                    <th class="pause-col">11h00 - 11h30<br><span style="font-size:0.65rem;">(Récréation)</span></th>
                                    <th>11h30 - 12h30</th>
                                    <th>12h30 - 13h30</th>
                                    <th>13h30 - 14h30</th>
                                </tr>
                            </thead>
                            <tbody>
                                {lignes_tbody}
                            </tbody>
                        </table>
                    </div>
                    </body>
                    </html>
                    """
                    components.html(html_table, height=520, scrolling=True)

        # ==========================================
        # ONGLET 2 : VUE GLOBALE DE L'ÉTABLISSEMENT
        # ==========================================
        with tab_global:
            st.markdown(f"### 📊 Tableau de Service Global — **{school_name} ({cycle_en_cours})**")
            st.info("Disposition officielle : Classes et Heures en lignes, Jours de la semaine en colonnes.")

            if not classes_cycle:
                st.warning("Aucune classe disponible pour ce cycle.")
            else:
                lignes_globales = []
                for classe_obj in classes_cycle:
                    c_nom = classe_obj.libelle
                    query_edt_g = db.query(EmploiDuTemps).filter(
                        EmploiDuTemps.school_id == school_id,
                        EmploiDuTemps.classe == c_nom
                    ).all()
                    edt_dict_g = {(item.jour, item.heure): {"matiere": item.matiere, "prof": item.enseignant} for item in query_edt_g}

                    for nom_h, plage_h in heures_libelles:
                        ligne_dict = {
                            "Classe": c_nom,
                            "Heure": nom_h,
                            "Plage": plage_h
                        }
                        for jour in jours:
                            if nom_h == "Récréation" or plage_h == "11h00 - 11h30":
                                ligne_dict[jour] = "☕ Pause"
                            else:
                                val = edt_dict_g.get((jour, plage_h), None)
                                if val:
                                    ligne_dict[jour] = f"{val['matiere']} ({val['prof']})"
                                else:
                                    ligne_dict[jour] = "-"
                        lignes_globales.append(ligne_dict)

                if lignes_globales:
                    df_global_service = pd.DataFrame(lignes_globales)

                    col_g_exp1, col_g_exp2, col_g_exp3, col_g_vide = st.columns([1.3, 1.3, 1.3, 3.5])

                    with col_g_exp1:
                        output_excel_g = io.BytesIO()
                        with pd.ExcelWriter(output_excel_g, engine="openpyxl") as writer:
                            df_global_service.to_excel(
                                writer,
                                index=False,
                                sheet_name="Tableau_Service_Global",
                            )
                        excel_data_g = output_excel_g.getvalue()
                        st.download_button(
                            label="📥 Excel",
                            data=excel_data_g,
                            file_name=f"Tableau_Service_Global_{cycle_en_cours}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key="download_excel_global"
                        )

                    with col_g_exp2:
                        pdf_buffer_g = io.BytesIO()
                        doc_g = SimpleDocTemplate(
                            pdf_buffer_g,
                            pagesize=landscape(A4),
                            rightMargin=20,
                            leftMargin=20,
                            topMargin=30,
                            bottomMargin=40,
                        )
                        elements_g = []
                        styles_g = getSampleStyleSheet()

                        title_style_g = ParagraphStyle(
                            "TitleStyleGlobal",
                            parent=styles_g["Heading1"],
                            fontSize=13,
                            textColor=colors.HexColor("#1e3a8a"),
                            alignment=1,
                            spaceAfter=12,
                        )

                        elements_g.append(
                            Paragraph(
                                f"TABLEAU DE SERVICE GLOBAL — {school_name} ({cycle_en_cours}) | ANNÉE SCOLAIRE : {annee_en_cours}",
                                title_style_g,
                            )
                        )
                        elements_g.append(Spacer(1, 8))

                        table_data_g = [list(df_global_service.columns)]
                        for _, row in df_global_service.iterrows():
                            table_data_g.append([str(val) for val in row])

                        t_g_style = TableStyle([
                            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a8a")),
                            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                            ("FONTSIZE", (0, 0), (-1, 0), 8),
                            ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
                            ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f8fafc")),
                            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                            ("FONTSIZE", (0, 1), (-1, -1), 7),
                            ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
                            ("TOPPADDING", (0, 1), (-1, -1), 4),
                        ])

                        t_g = Table(table_data_g)
                        t_g.setStyle(t_g_style)
                        elements_g.append(t_g)
                        doc_g.build(elements_g)
                        pdf_data_g = pdf_buffer_g.getvalue()

                        st.download_button(
                            label="📥 PDF",
                            data=pdf_data_g,
                            file_name=f"Tableau_Service_Global_{cycle_en_cours}.pdf",
                            mime="application/pdf",
                            key="download_pdf_global"
                        )

                    with col_g_exp3:
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
                    st.dataframe(df_global_service, use_container_width=True)

        # ==========================================
        # ONGLET 3 : AJOUTER UN CRÉNEAU (Persistant en DB)
        # ==========================================
        with tab2:
            st.markdown(
                f"### Planification d'un Créneau — **{school_name} ({cycle_en_cours})**"
            )

            if not classes_cycle:
                st.warning(
                    f"⚠️ Veuillez d'abord créer des classes pour le cycle "
                    f" **{cycle_en_cours}** dans le menu 'Classes & Tarifs'."
                )
            else:
                noms_classes = [c.libelle for c in classes_cycle]
                with st.form("form_add_creneau"):
                    col1, col2 = st.columns(2)
                    with col1:
                        classe_selectionnee = st.selectbox(
                            "Classe", noms_classes, key="form_edt_classe"
                        )
                        jour = st.selectbox(
                            "Jour de la semaine",
                            jours,
                        )
                        horaire_debut = st.selectbox(
                            "Heure de début", creneaux_cours_uniquement
                        )
                        duree_cours = st.selectbox(
                            "Durée du cours", ["1 heure", "2 heures", "3 heures"]
                        )
                    with col2:
                        matiere = st.text_input("Matière / Intitulé du cours")
                        prof_nom = st.text_input("Nom de l'enseignant")
                        prof_contact = st.text_input(
                            "Contact / Téléphone de l'enseignant"
                        )

                    submitted = st.form_submit_button("Ajouter le créneau")
                    if submitted:
                        if not matiere or not prof_nom:
                            st.error(
                                "⚠️ Veuillez indiquer la matière et le nom de l'enseignant."
                            )
                        else:
                            target_school_id = school_id
                            if is_super_admin and not target_school_id:
                                ecole_defaut = db.query(School).first()
                                target_school_id = (
                                    ecole_defaut.id if ecole_defaut else 1
                                )

                            nb_heures = 1
                            if duree_cours == "2 heures":
                                nb_heures = 2
                            elif duree_cours == "3 heures":
                                nb_heures = 3

                            try:
                                start_idx = creneaux_cours_uniquement.index(horaire_debut)
                            except ValueError:
                                start_idx = 0

                            classe_db_obj = db.query(Classe).filter(
                                Classe.school_id == target_school_id,
                                Classe.libelle == classe_selectionnee
                            ).first()
                            classe_id_val = classe_db_obj.id if classe_db_obj else None

                            assigned_count = 0
                            current_idx = start_idx
                            while assigned_count < nb_heures and current_idx < len(creneaux_cours_uniquement):
                                target_slot = creneaux_cours_uniquement[current_idx]
                                
                                existing_creneau = db.query(EmploiDuTemps).filter(
                                    EmploiDuTemps.school_id == target_school_id,
                                    EmploiDuTemps.classe == classe_selectionnee,
                                    EmploiDuTemps.jour == jour,
                                    EmploiDuTemps.heure == target_slot
                                ).first()

                                if existing_creneau:
                                    existing_creneau.matiere = matiere.strip().upper()
                                    existing_creneau.enseignant = prof_nom.strip()
                                    existing_creneau.classe_id = classe_id_val
                                    if hasattr(existing_creneau, "contact"):
                                        existing_creneau.contact = prof_contact.strip() if prof_contact else "N/D"
                                else:
                                    nouveau_creneau = EmploiDuTemps(
                                        school_id=target_school_id,
                                        classe_id=classe_id_val,
                                        classe=classe_selectionnee,
                                        jour=jour,
                                        heure=target_slot,
                                        matiere=matiere.strip().upper(),
                                        enseignant=prof_nom.strip()
                                    )
                                    if hasattr(nouveau_creneau, "contact"):
                                        nouveau_creneau.contact = prof_contact.strip() if prof_contact else "N/D"
                                    db.add(nouveau_creneau)

                                assigned_count += 1
                                current_idx += 1

                            nouveau_log = ActivityLog(
                                school_id=target_school_id,
                                timestamp=datetime.now(),
                                username=st.session_state.get("username", "admin"),
                                action=(
                                    f"Planification créneau EDT ({duree_cours}) : {matiere} avec {prof_nom}"
                                    f" ({classe_selectionnee}, {jour} à partir de {horaire_debut})"
                                ),
                                module="Emploi du temps",
                                statut="Succès",
                            )
                            db.add(nouveau_log)
                            db.commit()

                            st.success(
                                f"✅ Créneau de {matiere} ({prof_nom}) d'une durée de {duree_cours} "
                                f"enregistré et persisté en base de données pour {classe_selectionnee} ({jour}, dès {horaire_debut}) !"
                            )
                            st.rerun()

    finally:
        db.close()


# Alias de compatibilité
afficher_emploi_du_temps = afficher_emploi_temps
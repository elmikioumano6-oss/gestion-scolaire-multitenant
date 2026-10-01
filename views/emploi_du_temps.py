from datetime import datetime
import io
from database.db_config import SessionLocal
from database.models import ActivityLog, Classe, School
import pandas as pd
import reportlab
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
import streamlit as st
import streamlit.components.v1 as components


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
            ecole_courante = (
                db.query(School).filter(School.id == school_id).first()
            )
            if ecole_courante:
                school_name = ecole_courante.nom

        tab1, tab_global, tab2 = st.tabs([
            "📋 Consulter par Classe", 
            "📊 Vue Globale Établissement", 
            "➕ Ajouter un Créneau"
        ])

        classes_query = db.query(Classe).filter(Classe.cycle == cycle_en_cours)
        if not is_super_admin and school_id:
            classes_query = classes_query.filter(
                Classe.school_id == school_id
            )
        classes_cycle = classes_query.all()

        if "emplois_du_temps_data" not in st.session_state:
            st.session_state["emplois_du_temps_data"] = {}

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
                    key_edt = f"{school_id}_{cycle_en_cours}_{classe_choisie}"
                    edt_dict = st.session_state["emplois_du_temps_data"].get(
                        key_edt, {}
                    )

                    data_grille = []
                    for jour in jours:
                        ligne = {"Jour": jour}
                        for horaire in creneaux_horaires:
                            if horaire == "11h00 - 11h30":
                                ligne[horaire] = "☕ Pause"
                            else:
                                val_creneau = edt_dict.get(
                                    (jour, horaire), None
                                )
                                if val_creneau:
                                    ligne[horaire] = (
                                        f"{val_creneau['matiere']} (Prof: {val_creneau['prof']} - {val_creneau['contact']})"
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
                        with pd.ExcelWriter(
                            output_excel, engine="openpyxl"
                        ) as writer:
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
                            mime=(
                                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            ),
                        )

                    with col_exp2:
                        pdf_buffer = io.BytesIO()
                        doc = SimpleDocTemplate(
                            pdf_buffer,
                            pagesize=landscape(A4),
                            rightMargin=30,
                            leftMargin=30,
                            topMargin=30,
                            bottomMargin=50,
                        )

                        elements = []
                        styles = getSampleStyleSheet()

                        title_style = ParagraphStyle(
                            "TitleStyle",
                            parent=styles["Heading1"],
                            fontSize=15,
                            textColor=colors.HexColor("#1e3a8a"),
                            alignment=1,
                            spaceAfter=15,
                        )

                        elements.append(
                            Paragraph(
                                f"EMPLOI DU TEMPS OFFICIEL ({annee_en_cours}) — CLASSE : {classe_choisie} ({school_name})",
                                title_style,
                            )
                        )
                        elements.append(Spacer(1, 10))

                        table_data = [list(df_edt.columns)]
                        for _, row in df_edt.iterrows():
                            table_data.append([str(val) for val in row])

                        col_widths = [70] + [
                            (780 - 70) / len(creneaux_horaires)
                        ] * len(creneaux_horaires)
                        t = Table(table_data, colWidths=col_widths)
                        t.setStyle(
                            TableStyle([
                                (
                                    "BACKGROUND",
                                    (0, 0),
                                    (-1, 0),
                                    colors.HexColor("#1e3a8a"),
                                ),
                                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                                ("FONTSIZE", (0, 0), (-1, 0), 9),
                                ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                                (
                                    "BACKGROUND",
                                    (0, 1),
                                    (-1, -1),
                                    colors.HexColor("#f8fafc"),
                                ),
                                (
                                    "GRID",
                                    (0, 0),
                                    (-1, -1),
                                    0.5,
                                    colors.HexColor("#cbd5e1"),
                                ),
                                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                                ("FONTSIZE", (0, 1), (-1, -1), 8),
                                ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
                                ("TOPPADDING", (0, 1), (-1, -1), 5),
                            ])
                        )
                        elements.append(t)

                        def add_footer(canvas, doc_obj):
                            canvas.saveState()
                            footer_y = 22
                            s_nom = (
                                ecole_courante.nom
                                if ecole_courante
                                else school_name
                            )
                            s_adr = (
                                ecole_courante.adresse
                                if ecole_courante
                                and ecole_courante.adresse
                                else "Niamey - Niger"
                            )
                            s_cont = (
                                ecole_courante.contacts
                                if ecole_courante
                                and ecole_courante.contacts
                                else "N/D"
                            )
                            s_dev = (
                                ecole_courante.devise
                                if ecole_courante
                                and ecole_courante.devise
                                else "Excellence - Persévérance - Réussite"
                            )

                            footer_text = f"<b>{s_nom}</b> | Adresse : {s_adr} | Contacts : {s_cont} | Devise : <i>{s_dev}</i>"
                            footer_style = ParagraphStyle(
                                "FooterStyle",
                                parent=styles["Normal"],
                                fontSize=8,
                                textColor=colors.HexColor("#475569"),
                                alignment=1,
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

                    st.markdown(
                        """
                        <style>
                            .edt-container {
                                background-color: #0e1117;
                                padding: 1.5rem;
                                border-radius: 12px;
                                border: 1px solid rgba(255, 255, 255, 0.1);
                                box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
                                font-family: 'Inter', sans-serif;
                            }
                            .edt-header {
                                display: flex;
                                justify-content: space-between;
                                align-items: center;
                                margin-bottom: 1.2rem;
                                border-bottom: 2px solid #1f2937;
                                padding-bottom: 0.8rem;
                            }
                            .edt-title {
                                font-size: 1.15rem;
                                font-weight: 600;
                                color: #f3f4f6;
                            }
                            .edt-badge-repot {
                                background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
                                color: white;
                                padding: 0.4rem 0.8rem;
                                border-radius: 20px;
                                font-size: 0.85rem;
                                font-weight: 500;
                                box-shadow: 0 2px 6px rgba(59, 130, 246, 0.3);
                            }
                            .styled-table {
                                width: 100%;
                                border-collapse: separate;
                                border-spacing: 0;
                                border-radius: 8px;
                                overflow: hidden;
                                border: 1px solid #2d3748;
                            }
                            .styled-table th {
                                background-color: #1a202c;
                                color: #e2e8f0;
                                text-align: center;
                                padding: 12px 8px;
                                font-size: 0.85rem;
                                font-weight: 600;
                                letter-spacing: 0.05em;
                                border-bottom: 2px solid #4a5568;
                            }
                            .styled-table td {
                                background-color: #111827;
                                color: #cbd5e0;
                                text-align: center;
                                padding: 12px 8px;
                                font-size: 0.8rem;
                                border-bottom: 1px solid #1f2937;
                                border-right: 1px solid #1f2937;
                                vertical-align: middle;
                                height: 45px;
                            }
                            .styled-table td:first-child {
                                font-weight: 600;
                                color: #60a5fa;
                                background-color: #161e2e;
                            }
                            .pause-col {
                                background-color: #18212f !important;
                                color: #9ca3af !important;
                                font-style: italic;
                                font-size: 0.8rem;
                            }
                        </style>
                        """,
                        unsafe_allow_html=True,
                    )

                    html_table = f"""
                    <div class="edt-container">
                        <div class="edt-header">
                            <div class="edt-title">📌 Emploi du temps officiel ({annee_en_cours}) : <span style="color: #60a5fa;">{classe_obj.libelle}</span></div>
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
                    """

                    for jour in jours:
                        html_table += f"<tr><td>{jour}</td>"
                        for horaire in creneaux_horaires:
                            if horaire == "11h00 - 11h30":
                                html_table += (
                                    '<td class="pause-col">☕ Pause</td>'
                                )
                            else:
                                val_creneau = edt_dict.get(
                                    (jour, horaire), None
                                )
                                if val_creneau:
                                    html_table += f"""
                                    <td>
                                        <strong style="color: #34d399;">{val_creneau['matiere']}</strong><br>
                                        <span style="font-size: 0.75rem; color: #94a3b8;">👨‍🏫 {val_creneau['prof']}</span><br>
                                        <span style="font-size: 0.7rem; color: #60a5fa;">📞 {val_creneau['contact']}</span>
                                    </td>
                                    """
                                else:
                                    html_table += "<td></td>"
                        html_table += "</tr>"

                    html_table += """
                            </tbody>
                        </table>
                    </div>
                    """
                    st.markdown(html_table, unsafe_allow_html=True)

        # ==========================================
        # ONGLET 2 : VUE GLOBALE DE L'ÉTABLISSEMENT (Avec boutons d'exportation)
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
                    key_edt = f"{school_id}_{cycle_en_cours}_{c_nom}"
                    edt_dict = st.session_state["emplois_du_temps_data"].get(key_edt, {})

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
                                val = edt_dict.get((jour, plage_h), None)
                                if val:
                                    ligne_dict[jour] = f"{val['matiere']} ({val['prof']})"
                                else:
                                    ligne_dict[jour] = "-"
                        lignes_globales.append(ligne_dict)

                if lignes_globales:
                    df_global_service = pd.DataFrame(lignes_globales)

                    # --- BOUTONS D'EXPORTATION POUR LA VUE GLOBALE ---
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
                                f"TABLEAU DE SERVICE GLOBAL — {school_name} ({cycle_en_cours}) | ANNEESCOLAIRE : {annee_en_cours}",
                                title_style_g,
                            )
                        )
                        elements_g.append(Spacer(1, 8))

                        table_data_g = [list(df_global_service.columns)]
                        for _, row in df_global_service.iterrows():
                            table_data_g.append([str(val) for val in row])

                        t_g = Table(table_data_g)
                        t_g.setStyle(
                            TableStyle([
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
                        )
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
        # ONGLET 3 : AJOUTER UN CRÉNEAU
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
                        creneaux_cours = [
                            c for c in creneaux_horaires if c != "11h00 - 11h30"
                        ]
                        horaire = st.selectbox(
                            "Plage horaire", creneaux_cours
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

                            key_edt = f"{target_school_id}_{cycle_en_cours}_{classe_selectionnee}"
                            if (
                                key_edt
                                not in st.session_state[
                                    "emplois_du_temps_data"
                                ]
                            ):
                                st.session_state["emplois_du_temps_data"][
                                    key_edt
                                ] = {}

                            st.session_state["emplois_du_temps_data"][key_edt][
                                (jour, horaire)
                            ] = {
                                "matiere": matiere.strip().upper(),
                                "prof": prof_nom.strip(),
                                "contact": (
                                    prof_contact.strip()
                                    if prof_contact
                                    else "N/D"
                                ),
                            }

                            nouveau_log = ActivityLog(
                                school_id=target_school_id,
                                timestamp=datetime.now(),
                                username=st.session_state.get(
                                    "username", "admin"
                                ),
                                action=(
                                    f"Planification créneau EDT : {matiere} avec {prof_nom}"
                                    f" ({classe_selectionnee}, {jour} {horaire})"
                                ),
                                module="Emploi du temps",
                                statut="Succès",
                            )
                            db.add(nouveau_log)
                            db.commit()

                            st.success(
                                f"✅ Créneau de {matiere} ({prof_nom}) ajouté avec succès pour"
                                f" {classe_selectionnee} ({jour}, {horaire}) !"
                            )
                            st.rerun()

    finally:
        db.close()


# Alias de compatibilité
afficher_emploi_du_temps = afficher_emploi_temps
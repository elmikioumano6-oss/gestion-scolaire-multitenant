from datetime import datetime
import io
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from database.db_config import SessionLocal
from database.models import ActivityLog, AnneeScolaire, Classe, Eleve, Presence, School
import reportlab
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle


def afficher_presence():
    # --- STYLE CSS DESIGN ERP HAUT DE GAMME ---
    st.markdown(
        """
    <style>
        @media print {
            body {
                background-color: white !important;
                color: black !important;
            }
            .stButton, .stSelectbox, sidebar, header, footer, [data-testid="stSidebar"] {
                display: none !important;
            }
            .printable-area {
                width: 100% !important;
                padding: 10px !important;
                margin: 0 !important;
            }
            .print-footer {
                position: fixed;
                bottom: 0;
                left: 0;
                right: 0;
                text-align: center;
                font-size: 8pt;
                border-top: 1px solid #ccc;
                padding-top: 8px;
                color: #333;
                background-color: white;
            }
        }
    </style>
    """,
        unsafe_allow_html=True,
    )

    st.subheader("Gestion de l'Assiduité & Registre des Présences")
    st.markdown(
        "Suivi des présences en temps réel, contrôle de la discipline, tableau "
        "de bord de régularisation pour la Censure et bilans mensuels."
    )
    st.markdown("---")

    school_id = st.session_state.get("school_id")
    is_super_admin = st.session_state.get("is_super_admin", False)
    
    query_params = st.query_params if hasattr(st, "query_params") else {}
    role_url = str(query_params.get("role", "")).lower()
    role_session = str(st.session_state.get("role", "")).lower()
    role_utilisateur = role_url if role_url else role_session

    username = st.session_state.get("username", "admin")
    cycle_en_cours = st.session_state.get("cycle_actif", "Collège")

    if not school_id and not is_super_admin:
        st.warning("Veuillez vous connecter pour accéder à cette section.")
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
            school_devise = ecole_courante.devise if ecole_courante else "Excellence - Persévérance - Réussite"
            school_adresse = ecole_courante.adresse if ecole_courante and ecole_courante.adresse else "Niamey - Niger"
            school_contacts = ecole_courante.contacts if ecole_courante and ecole_courante.contacts else "N/D"
        else:
            school_name = st.session_state.get("school_name", "Établissement")
            school_devise = "Excellence - Persévérance - Réussite"
            school_adresse = "Niamey - Niger"
            school_contacts = "N/D"

        annee_active = (
            db.query(AnneeScolaire)
            .filter(
                AnneeScolaire.school_id == target_school_id,
                AnneeScolaire.active == True,
            )
            .first()
        )
        libelle_annee = annee_active.libelle if annee_active else str(datetime.now().year)

        classes_query = db.query(Classe).filter(Classe.cycle == cycle_en_cours)
        if not is_super_admin and school_id:
            classes_query = classes_query.filter(Classe.school_id == school_id)
        else:
            classes_query = classes_query.filter(Classe.school_id == target_school_id)
        classes_cycle = classes_query.all()

        if not classes_cycle:
            st.warning(f"Aucune classe configurée pour le cycle {cycle_en_cours}.")
            return

        noms_classes = [
            (c.libelle if hasattr(c, "libelle") and c.libelle else getattr(c, "nom", ""))
            for c in classes_cycle
        ]

        # --- CREATION DES ONGLETS PRINCIPAUX ---
        tab_appel, tab_bilan = st.tabs([
            "Appel et Saisie Journalière",
            "Bilan Mensuel & Suivi Élève"
        ])

        with tab_appel:
            st.markdown('<div class="printable-area">', unsafe_allow_html=True)
            st.markdown(f"### Suivi d'Assiduité ({libelle_annee}) — **{school_name} ({cycle_en_cours})**")

            col_sel1, col_sel2 = st.columns(2)
            with col_sel1:
                classe_choisie = st.selectbox("Sélectionner la classe", noms_classes, key="presence_classe_select")
            with col_sel2:
                date_appel = st.date_input("Date concernée", value=datetime.now().date(), key="presence_date_select")

            classe_obj = next(
                (c for c in classes_cycle if (c.libelle if hasattr(c, "libelle") else getattr(c, "nom", "")) == classe_choisie),
                None,
            )
            if not classe_obj:
                st.markdown("</div>", unsafe_allow_html=True)
                return

            eleves_query = db.query(Eleve).filter(
                Eleve.classe_id == classe_obj.id, Eleve.school_id == target_school_id
            )
            eleves = eleves_query.order_by(Eleve.nom).all()

            if not eleves:
                st.info(f"Aucun élève inscrit dans la classe {classe_choisie}.")
                st.markdown("</div>", unsafe_allow_html=True)
                return

            is_censeur_or_admin = (
                role_utilisateur in ["censeur", "directeur", "super_admin", "surveillant", "admin", "fondateur", "proviseur"]
                or is_super_admin
                or "directeur" in role_utilisateur
                or "admin" in role_utilisateur
            )

            liste_statuts_assiduite = [
                "Présent",
                "Absent non justifié",
                "Absent justifié",
                "Retard < 15 min",
                "Retard > 15 min",
                "Puni",
                "Exclu",
                "Dispensé",
            ]

            liste_motifs = [
                "Aucun",
                "Maladie / Certificat médical",
                "Permission familiale",
                "Problème de transport",
                "Retard indépendant de la volonté",
                "Rendez-vous médical",
                "Sanction disciplinaire",
                "Autre motif valable",
            ]

            existantes = (
                db.query(Presence)
                .join(Eleve)
                .filter(
                    Presence.school_id == target_school_id,
                    Presence.date == date_appel,
                    Eleve.classe_id == classe_obj.id,
                )
                .all()
            )
            dict_existantes = {p.eleve_id: p for p in existantes}

            if is_censeur_or_admin:
                st.markdown(
                    f"""
                    <div style="background: linear-gradient(135deg, rgba(33, 150, 243, 0.12) 0%, rgba(33, 150, 243, 0.03) 100%); padding: 15px 20px; border-radius: 10px; border-left: 5px solid #2196F3; margin-bottom: 25px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
                        Espace Censeur / Direction — Tableau de contrôle et de régularisation pour la classe de <b>{classe_choisie}</b> au <b>{date_appel.strftime('%d/%m/%Y')}</b> (<span style="color: #4da6ff; font-weight: bold;">{len(eleves)} élèves</span> enregistrés).
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                if not existantes:
                    st.warning(
                        "Aucun appel n'a encore été transmis par le professeur pour cette date. "
                        "Vous pouvez procéder ci-dessous au contrôle ou à la régularisation administrative de l'ensemble de la classe."
                    )

                with st.form(key=f"form_censeur_{classe_choisie}_{date_appel}"):
                    saisie_censeur = []
                    
                    hc1, hc2, hc3, hc4 = st.columns([1.5, 3.2, 3.0, 3.3])
                    hc1.markdown("<p style='color: #94a3b8; font-weight: 600; font-size: 0.85rem; text-transform: uppercase;'>Matricule</p>", unsafe_allow_html=True)
                    hc2.markdown("<p style='color: #94a3b8; font-weight: 600; font-size: 0.85rem; text-transform: uppercase;'>Nom & Prénom</p>", unsafe_allow_html=True)
                    hc3.markdown("<p style='color: #94a3b8; font-weight: 600; font-size: 0.85rem; text-transform: uppercase;'>Statut administratif</p>", unsafe_allow_html=True)
                    hc4.markdown("<p style='color: #94a3b8; font-weight: 600; font-size: 0.85rem; text-transform: uppercase;'>Motif / Visa de la Censure</p>", unsafe_allow_html=True)
                    st.markdown("<hr style='margin: 5px 0 15px 0; border-color: rgba(255,255,255,0.1);'>", unsafe_allow_html=True)

                    for e in eleves:
                        p_ex = dict_existantes.get(e.id)
                        statut_val = p_ex.statut if p_ex and p_ex.statut in liste_statuts_assiduite else "Présent"
                        motif_val = p_ex.motif if p_ex and p_ex.motif in liste_motifs else "Aucun"

                        rc1, rc2, rc3, rc4 = st.columns([1.5, 3.2, 3.0, 3.3])
                        rc1.markdown(f"<div style='padding-top: 8px;'><span style='background-color: rgba(77, 166, 255, 0.1); color: #4da6ff; padding: 4px 8px; border-radius: 4px; font-weight: 600; font-size: 0.9rem;'>{e.matricule or 'N/A'}</span></div>", unsafe_allow_html=True)
                        rc2.markdown(f"<div style='padding-top: 8px; font-weight: 500; font-size: 0.95rem;'>{e.nom} {e.prenom}</div>", unsafe_allow_html=True)
                        
                        choix_statut = rc3.selectbox(
                            f"Statut_{e.id}",
                            options=liste_statuts_assiduite,
                            index=liste_statuts_assiduite.index(statut_val) if statut_val in liste_statuts_assiduite else 0,
                            label_visibility="collapsed",
                            key=f"statut_c_{e.id}"
                        )
                        choix_motif = rc4.selectbox(
                            f"Motif_{e.id}",
                            options=liste_motifs,
                            index=liste_motifs.index(motif_val) if motif_val in liste_motifs else 0,
                            label_visibility="collapsed",
                            key=f"motif_c_{e.id}"
                        )

                        saisie_censeur.append({
                            "eleve_id": e.id,
                            "Matricule": e.matricule or "N/A",
                            "Nom & Prénom": f"{e.nom} {e.prenom}",
                            "Statut administratif": choix_statut,
                            "Motif / Visa de la Censure": choix_motif,
                        })

                    st.markdown("<hr style='margin: 20px 0 15px 0; border-color: rgba(255,255,255,0.1);'>", unsafe_allow_html=True)
                    submitted_censure = st.form_submit_button("Enregistrer les modifications de la Censure", type="primary")

                    if submitted_censure:
                        local_db = SessionLocal()
                        try:
                            eleve_ids = [item["eleve_id"] for item in saisie_censeur]
                            local_db.query(Presence).filter(
                                Presence.school_id == target_school_id,
                                Presence.date == date_appel,
                                Presence.eleve_id.in_(eleve_ids),
                            ).delete(synchronize_session=False)

                            for item in saisie_censeur:
                                nouvelle_presence = Presence(
                                    school_id=target_school_id,
                                    eleve_id=item["eleve_id"],
                                    date=date_appel,
                                    statut=item["Statut administratif"],
                                    motif=item["Motif / Visa de la Censure"] if item["Motif / Visa de la Censure"] != "Aucun" else None,
                                )
                                local_db.add(nouvelle_presence)

                            nouveau_log = ActivityLog(
                                school_id=target_school_id,
                                timestamp=datetime.now(),
                                username=username,
                                action=f"Validation censure — Classe {classe_choisie} ({date_appel.strftime('%d/%m/%Y')}) par {username}",
                                module="Présence",
                                statut="Succès",
                            )
                            local_db.add(nouveau_log)
                            local_db.commit()
                            st.success(f"Registre officiel de la classe {classe_choisie} mis à jour et archivé avec succès !")
                            st.rerun()
                        except Exception as err:
                            local_db.rollback()
                            st.error(f"Erreur de base de données : {err}")
                        finally:
                            local_db.close()

                df_suivi = pd.DataFrame(saisie_censeur)
                st.markdown("<br>", unsafe_allow_html=True)
                col_exp2, col_exp3, col_exp4 = st.columns([1.2, 1.2, 2])

                with col_exp2:
                    pdf_buffer = io.BytesIO()
                    doc = SimpleDocTemplate(pdf_buffer, pagesize=landscape(A4), rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=50)
                    elements = []
                    styles = getSampleStyleSheet()
                    title_style = ParagraphStyle("TitleStyle", parent=styles["Heading1"], fontSize=14, textColor=colors.HexColor("#1e3a8a"), alignment=1, spaceAfter=15)
                    
                    elements.append(Paragraph(f"REGISTRE DE PRÉSENCE ({libelle_annee}) — CLASSE : {classe_choisie} ({school_name}) — Date : {date_appel.strftime('%d/%m/%Y')}", title_style))
                    elements.append(Spacer(1, 10))

                    df_pdf = df_suivi.drop(columns=["eleve_id"]) if "eleve_id" in df_suivi.columns else df_suivi
                    table_data = [list(df_pdf.columns)]
                    for _, row in df_pdf.iterrows():
                        table_data.append([str(val) for val in row])

                    col_widths = [780 / len(df_pdf.columns)] * len(df_pdf.columns)
                    t = Table(table_data, colWidths=col_widths)
                    t.setStyle(TableStyle([
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a8a")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 9),
                        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f8fafc")),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                        ("FONTSIZE", (0, 1), (-1, -1), 9),
                    ]))
                    elements.append(t)

                    def add_footer(canvas, doc_obj):
                        canvas.saveState()
                        footer_text = f"<b>{school_name}</b> | Adresse : {school_adresse} | Contacts : {school_contacts} | Devise : <i>{school_devise}</i>"
                        footer_style = ParagraphStyle("FooterStyle", parent=styles["Normal"], fontSize=8, textColor=colors.HexColor("#475569"), alignment=1)
                        p = Paragraph(footer_text, footer_style)
                        p.wrap(doc_obj.pagesize[0] - 60, 22)
                        p.drawOn(canvas, 30, 22)
                        canvas.restoreState()

                    doc.build(elements, onFirstPage=add_footer)
                    st.download_button("Télécharger PDF", data=pdf_buffer.getvalue(), file_name=f"Registre_Presence_{classe_choisie}.pdf", mime="application/pdf")

                with col_exp3:
                    components.html('<button onclick="parent.window.print()" style="background-color: #2563eb; color: white; border: none; padding: 0.5rem 1rem; font-size: 0.9rem; border-radius: 6px; cursor: pointer; font-family: sans-serif;">Imprimer</button>', height=45)

                with col_exp4:
                    csv_data = df_suivi.drop(columns=["eleve_id"]).to_csv(index=False).encode("utf-8")
                    st.download_button("Télécharger CSV", data=csv_data, file_name=f"appel_{classe_choisie}.csv", mime="text/csv")

            else:
                st.info(f"Espace Enseignant — Feuille d'appel active pour la classe de **{classe_choisie}** ({len(eleves)} élèves).")

                with st.form(key=f"form_ens_{classe_choisie}_{date_appel}"):
                    saisie_ens = []
                    hc1, hc2, hc3, hc4 = st.columns([1.5, 3.2, 3.0, 3.3])
                    hc1.markdown("<p style='color: #94a3b8; font-weight: 600; font-size: 0.85rem; text-transform: uppercase;'>Matricule</p>", unsafe_allow_html=True)
                    hc2.markdown("<p style='color: #94a3b8; font-weight: 600; font-size: 0.85rem; text-transform: uppercase;'>Nom & Prénom</p>", unsafe_allow_html=True)
                    hc3.markdown("<p style='color: #94a3b8; font-weight: 600; font-size: 0.85rem; text-transform: uppercase;'>Statut</p>", unsafe_allow_html=True)
                    hc4.markdown("<p style='color: #94a3b8; font-weight: 600; font-size: 0.85rem; text-transform: uppercase;'>Précisions / Motif</p>", unsafe_allow_html=True)
                    st.markdown("<hr style='margin: 5px 0 15px 0; border-color: rgba(255,255,255,0.1);'>", unsafe_allow_html=True)

                    for e in eleves:
                        p_ex = dict_existantes.get(e.id)
                        statut_val = p_ex.statut if p_ex and p_ex.statut in liste_statuts_assiduite else "Présent"
                        motif_val = p_ex.motif if p_ex and p_ex.motif in liste_motifs else "Aucun"

                        rc1, rc2, rc3, rc4 = st.columns([1.5, 3.2, 3.0, 3.3])
                        rc1.markdown(f"<div style='padding-top: 8px;'><span style='background-color: rgba(77, 166, 255, 0.1); color: #4da6ff; padding: 4px 8px; border-radius: 4px; font-weight: 600; font-size: 0.9rem;'>{e.matricule or 'N/A'}</span></div>", unsafe_allow_html=True)
                        rc2.markdown(f"<div style='padding-top: 8px; font-weight: 500; font-size: 0.95rem;'>{e.nom} {e.prenom}</div>", unsafe_allow_html=True)
                        
                        choix_statut = rc3.selectbox(
                            f"Statut_e_{e.id}",
                            options=liste_statuts_assiduite,
                            index=liste_statuts_assiduite.index(statut_val) if statut_val in liste_statuts_assiduite else 0,
                            label_visibility="collapsed",
                            key=f"statut_e_{e.id}"
                        )
                        choix_motif = rc4.selectbox(
                            f"Motif_e_{e.id}",
                            options=liste_motifs,
                            index=liste_motifs.index(motif_val) if motif_val in liste_motifs else 0,
                            label_visibility="collapsed",
                            key=f"motif_e_{e.id}"
                        )

                        saisie_ens.append({
                            "eleve_id": e.id,
                            "Statut": choix_statut,
                            "Motif": choix_motif,
                        })

                    st.markdown("<hr style='margin: 20px 0 15px 0; border-color: rgba(255,255,255,0.1);'>", unsafe_allow_html=True)
                    submitted_ens = st.form_submit_button("Transmettre l'appel à la Censure", type="primary")

                    if submitted_ens:
                        local_db = SessionLocal()
                        try:
                            eleve_ids = [item["eleve_id"] for item in saisie_ens]
                            local_db.query(Presence).filter(
                                Presence.school_id == target_school_id,
                                Presence.date == date_appel,
                                Presence.eleve_id.in_(eleve_ids),
                            ).delete(synchronize_session=False)

                            for item in saisie_ens:
                                nouvelle_presence = Presence(
                                    school_id=target_school_id,
                                    eleve_id=item["eleve_id"],
                                    date=date_appel,
                                    statut=item["Statut"],
                                    motif=item["Motif"] if item["Motif"] != "Aucun" else None,
                                )
                                local_db.add(nouvelle_presence)
                            local_db.commit()
                            st.success("Feuille d'appel transmise avec succès !")
                            st.rerun()
                        except Exception as err:
                            local_db.rollback()
                            st.error(f"Erreur de base de données : {err}")
                        finally:
                            local_db.close()

            st.markdown(
                f"""
                <div class="print-footer" style="margin-top: 40px; padding: 15px; border-top: 1px solid rgba(255,255,255,0.1); text-align: center; color: #94a3b8; font-size: 0.85rem;">
                    <b>{school_name}</b> | Adresse : {school_adresse} | Contacts : {school_contacts} | Devise : <i>{school_devise}</i>
                </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # --- ONGLET : BILAN MENSUEL & SUIVI ELEVE AVEC BOUTONS D'EXPORT ---
        with tab_bilan:
            st.markdown(f"### Bilan Mensuel & Suivi de l'Assiduité — **{school_name}**")
            st.markdown("Analysez les statistiques d'absence et de retard par mois et consultez l'historique individuel de chaque élève.")
            st.markdown("---")

            col_b1, col_b2 = st.columns(2)
            with col_b1:
                classe_bilan = st.selectbox("Sélectionner la classe pour le bilan", noms_classes, key="bilan_classe_select")
            with col_b2:
                mois_noms = {
                    1: "Janvier", 2: "Février", 3: "Mars", 4: "Avril", 
                    5: "Mai", 6: "Juin", 7: "Juillet", 8: "Août", 
                    9: "Septembre", 10: "Octobre", 11: "Novembre", 12: "Décembre"
                }
                mois_options = [(m, nom) for m, nom in mois_noms.items()]
                mois_choisi_num = st.selectbox(
                    "Sélectionner le mois", 
                    options=[m[0] for m in mois_options], 
                    format_func=lambda x: mois_noms[x], 
                    key="bilan_mois_select"
                )

            cls_obj_bilan = next(
                (c for c in classes_cycle if (c.libelle if hasattr(c, "libelle") else getattr(c, "nom", "")) == classe_bilan),
                None,
            )

            if cls_obj_bilan:
                eleves_bilan = db.query(Eleve).filter(
                    Eleve.classe_id == cls_obj_bilan.id, Eleve.school_id == target_school_id
                ).order_by(Eleve.nom).all()

                if not eleves_bilan:
                    st.info("Aucun élève trouvé dans cette classe.")
                else:
                    presences_mois = (
                        db.query(Presence)
                        .join(Eleve)
                        .filter(
                            Presence.school_id == target_school_id,
                            Eleve.classe_id == cls_obj_bilan.id
                        )
                        .all()
                    )

                    presences_mois_filtrees = [
                        p for p in presences_mois 
                        if (isinstance(p.date, datetime) and p.date.month == mois_choisi_num) or (hasattr(p.date, 'month') and p.date.month == mois_choisi_num)
                    ]

                    data_recap = []
                    for e in eleves_bilan:
                        p_eleves = [p for p in presences_mois_filtrees if p.eleve_id == e.id]
                        abs_NJ = sum(1 for p in p_eleves if "Absent non justifié" in str(p.statut))
                        abs_J = sum(1 for p in p_eleves if "Absent justifié" in str(p.statut))
                        retards = sum(1 for p in p_eleves if "Retard" in str(p.statut))
                        total_abs = abs_NJ + abs_J

                        data_recap.append({
                            "eleve_id": e.id,
                            "Matricule": e.matricule or "N/A",
                            "Élève": f"{e.nom} {e.prenom}",
                            "Absences Non Justifiées": abs_NJ,
                            "Absences Justifiées": abs_J,
                            "Total Absences": total_abs,
                            "Retards": retards
                        })

                    df_recap = pd.DataFrame(data_recap)
                    
                    st.markdown(f"#### Récapitulatif mensuel pour la classe : **{classe_bilan}** ({mois_noms[mois_choisi_num]})")
                    st.dataframe(df_recap.drop(columns=["eleve_id"]), use_container_width=True, hide_index=True)

                    # --- BOUTONS D'EXPORT DU BILAN MENSUEL ---
                    st.markdown("<br>", unsafe_allow_html=True)
                    col_ex_b1, col_ex_b2, col_ex_b3 = st.columns([1.2, 1.2, 2])

                    with col_ex_b1:
                        pdf_buffer_b = io.BytesIO()
                        doc_b = SimpleDocTemplate(pdf_buffer_b, pagesize=landscape(A4), rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=50)
                        elements_b = []
                        styles_b = getSampleStyleSheet()
                        title_style_b = ParagraphStyle("TitleStyleB", parent=styles_b["Heading1"], fontSize=14, textColor=colors.HexColor("#1e3a8a"), alignment=1, spaceAfter=15)
                        
                        elements_b.append(Paragraph(f"BILAN MENSUEL D'ASSIDUITÉ ({mois_noms[mois_choisi_num]} {libelle_annee}) — CLASSE : {classe_bilan} ({school_name})", title_style_b))
                        elements_b.append(Spacer(1, 10))

                        df_pdf_b = df_recap.drop(columns=["eleve_id"]) if "eleve_id" in df_recap.columns else df_recap
                        table_data_b = [list(df_pdf_b.columns)]
                        for _, row in df_pdf_b.iterrows():
                            table_data_b.append([str(val) for val in row])

                        col_widths_b = [780 / len(df_pdf_b.columns)] * len(df_pdf_b.columns)
                        t_b = Table(table_data_b, colWidths=col_widths_b)
                        t_b.setStyle(TableStyle([
                            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a8a")),
                            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                            ("FONTSIZE", (0, 0), (-1, 0), 9),
                            ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f8fafc")),
                            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                            ("FONTSIZE", (0, 1), (-1, -1), 9),
                        ]))
                        elements_b.append(t_b)

                        def add_footer_b(canvas, doc_obj):
                            canvas.saveState()
                            footer_text = f"<b>{school_name}</b> | Adresse : {school_adresse} | Contacts : {school_contacts} | Devise : <i>{school_devise}</i>"
                            footer_style = ParagraphStyle("FooterStyleB", parent=styles_b["Normal"], fontSize=8, textColor=colors.HexColor("#475569"), alignment=1)
                            p = Paragraph(footer_text, footer_style)
                            p.wrap(doc_obj.pagesize[0] - 60, 22)
                            p.drawOn(canvas, 30, 22)
                            canvas.restoreState()

                        doc_b.build(elements_b, onFirstPage=add_footer_b)
                        st.download_button("Télécharger Bilan PDF", data=pdf_buffer_b.getvalue(), file_name=f"Bilan_Mensuel_{classe_bilan}_{mois_noms[mois_choisi_num]}.pdf", mime="application/pdf", key="dl_pdf_bilan")

                    with col_ex_b2:
                        components.html('<button onclick="parent.window.print()" style="background-color: #2563eb; color: white; border: none; padding: 0.5rem 1rem; font-size: 0.9rem; border-radius: 6px; cursor: pointer; font-family: sans-serif;">Imprimer le Bilan</button>', height=45)

                    with col_ex_b3:
                        csv_data_b = df_recap.drop(columns=["eleve_id"]).to_csv(index=False).encode("utf-8")
                        st.download_button("Télécharger Bilan CSV", data=csv_data_b, file_name=f"Bilan_Mensuel_{classe_bilan}_{mois_noms[mois_choisi_num]}.csv", mime="text/csv", key="dl_csv_bilan")

                    st.markdown("---")
                    st.markdown("#### Fiche de Suivi Détaillé par Élève")
                    noms_eleves_options = {f"{e.nom} {e.prenom} ({e.matricule or 'N/A'})": e.id for e in eleves_bilan}
                    eleve_selectionne_str = st.selectbox("Choisir un élève pour voir son historique", options=list(noms_eleves_options.keys()), key="select_eleve_detail")

                    if eleve_selectionne_str:
                        id_eleve_actif = noms_eleves_options[eleve_selectionne_str]
                        historique_eleve = [p for p in presences_mois_filtrees if p.eleve_id == id_eleve_actif]

                        if not historique_eleve:
                            st.info("Aucun enregistrement d'assiduité pour cet élève ce mois-ci.")
                        else:
                            data_hist = []
                            for h in historique_eleve:
                                data_hist.append({
                                    "Date": h.date.strftime('%d/%m/%Y') if hasattr(h.date, 'strftime') else str(h.date),
                                    "Statut": h.statut,
                                    "Motif / Précisions": h.motif or "Aucun"
                                })
                            df_hist = pd.DataFrame(data_hist)
                            st.table(df_hist)

    finally:
        db.close()

afficher_gestion_presence = afficher_presence
afficher_presence = afficher_presence
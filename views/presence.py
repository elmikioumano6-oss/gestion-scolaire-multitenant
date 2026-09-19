from datetime import datetime
import io
from database.queries import get_classes_cached
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
    # --- STYLE CSS DÉDIÉ POUR L'IMPRESSION SUR PAGE A4 ---
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

    st.subheader("📋 Gestion de l'Assiduité & Registre des Présences")
    st.markdown(
        "Suivi des présences en temps réel, saisie par les enseignants et tableau"
        " de bord de contrôle pour le Censeur."
    )
    st.markdown("---")

    school_id = st.session_state.get("school_id")
    is_super_admin = st.session_state.get("is_super_admin", False)
    role_utilisateur = str(st.session_state.get("role", "")).lower()
    username = st.session_state.get("username", "admin")
    cycle_en_cours = st.session_state.get("cycle_actif", "Collège")

    if not school_id and not is_super_admin:
        st.warning("⚠️ Veuillez vous connecter pour accéder à cette section.")
        return

    db = SessionLocal()
    try:
        target_school_id = school_id
        if is_super_admin and not target_school_id:
            ecole_defaut = db.query(School).first()
            target_school_id = ecole_defaut.id if ecole_defaut else 1

        if school_id:
            ecole_courante = (
                db.query(School).filter(School.id == school_id).first()
            )
            school_name = (
                ecole_courante.nom
                if ecole_courante
                else st.session_state.get("school_name", "Établissement")
            )
            school_devise = (
                ecole_courante.devise
                if ecole_courante
                else "Excellence - Persévérance - Réussite"
            )
            school_adresse = (
                ecole_courante.adresse
                if ecole_courante and ecole_courante.adresse
                else "Niamey - Niger"
            )
            school_contacts = (
                ecole_courante.contacts
                if ecole_courante and ecole_courante.contacts
                else "N/D"
            )
        else:
            school_name = st.session_state.get("school_name", "Établissement")
            school_devise = "Excellence - Persévérance - Réussite"
            school_adresse = "Niamey - Niger"
            school_contacts = "N/D"

        # Récupération de l'année scolaire active
        annee_active = (
            db.query(AnneeScolaire)
            .filter(
                AnneeScolaire.school_id == target_school_id,
                AnneeScolaire.active == True,
            )
            .first()
        )
        libelle_annee = annee_active.libelle if annee_active else str(datetime.now().year)

        # Isolation des classes par cycle et par école
        classes_query = db.query(Classe).filter(Classe.cycle == cycle_en_cours)
        if not is_super_admin and school_id:
            classes_query = classes_query.filter(Classe.school_id == school_id)
        else:
            classes_query = classes_query.filter(
                Classe.school_id == target_school_id
            )
        classes_cycle = classes_query.all()

        # --- ZONE IMPRIMABLE ---
        st.markdown('<div class="printable-area">', unsafe_allow_html=True)

        st.markdown(
            f"### Suivi d'Assiduité ({libelle_annee}) — **{school_name} ({cycle_en_cours})**"
        )

        if not classes_cycle:
            st.warning(
                f"⚠️ Aucune classe configurée pour le cycle **{cycle_en_cours}**."
            )
            st.markdown("</div>", unsafe_allow_html=True)
            return

        noms_classes = [
            (
                c.libelle
                if hasattr(c, "libelle") and c.libelle
                else getattr(c, "nom", "")
            )
            for c in classes_cycle
        ]

        col_sel1, col_sel2 = st.columns(2)
        with col_sel1:
            classe_choisie = st.selectbox(
                "Sélectionner la classe", noms_classes, key="presence_classe_select"
            )
        with col_sel2:
            date_appel = st.date_input(
                "Date concernée",
                value=datetime.now().date(),
                key="presence_date_select",
            )

        classe_obj = next(
            (
                c
                for c in classes_cycle
                if (
                    c.libelle
                    if hasattr(c, "libelle")
                    else getattr(c, "nom", "")
                )
                == classe_choisie
            ),
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
            st.info(f"Aucun élève inscrit dans la classe **{classe_choisie}**.")
            st.markdown("</div>", unsafe_allow_html=True)
            return

        # --- ROUTAGE DES INTERFACES SELON LE RÔLE ---
        is_censeur_or_admin = role_utilisateur in [
            "censeur",
            "directeur",
            "super_admin",
            "surveillant",
        ]

        # 📋 LISTES DÉROULANTES OFFICIELLES
        liste_statuts_assiduite = [
            "Présent",
            "Absent non justifié",
            "Absent justifié",
            "Retard < 15 min",
            "Retard > 15 min",
        ]

        liste_motifs = [
            "Aucun",
            "Maladie / Certificat médical",
            "Permission familiale",
            "Problème de transport",
            "Retard indépendant de la volonté",
            "Rendez-vous médical",
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
            # ==========================================
            # ESPACE CENSEUR / ADMINISTRATION
            # ==========================================
            st.info(
                f"📐 Espace Censeur / Direction — Tableau de contrôle et de régularisation"
                f" pour la classe de **{classe_choisie}** au"
                f" {date_appel.strftime('%d/%m/%Y')} ({len(eleves)} élèves)."
            )

            if not existantes:
                st.warning(
                    "⚠️ Aucun appel n'a encore été transmis par le professeur pour"
                    " cette date. La liste complète des élèves s'affiche ci-dessous"
                    " pour un contrôle ou une saisie administrative par exception."
                )

            data_suivi_censeur = []
            for e in eleves:
                p_ex = dict_existantes.get(e.id)
                statut_defaut = p_ex.statut if p_ex else "Présent"
                motif_defaut = p_ex.motif if p_ex and p_ex.motif in liste_motifs else "Aucun"

                data_suivi_censeur.append({
                    "eleve_id": e.id,
                    "Matricule": e.matricule,
                    "Nom & Prénom": f"{e.nom} {e.prenom}",
                    "Statut": statut_defaut,
                    "Motif / Remarque": motif_defaut,
                })

            df_suivi = pd.DataFrame(data_suivi_censeur)

            edited_df_censeur = st.data_editor(
                df_suivi,
                column_config={
                    "eleve_id": None,
                    "Matricule": st.column_config.TextColumn(
                        "Matricule", disabled=True
                    ),
                    "Nom & Prénom": st.column_config.TextColumn(
                        "Nom & Prénom", disabled=True
                    ),
                    "Statut": st.column_config.SelectboxColumn(
                        "Statut administratif",
                        options=liste_statuts_assiduite,
                        required=True,
                    ),
                    "Motif / Remarque": st.column_config.SelectboxColumn(
                        "Motif / Visa de la Censure",
                        options=liste_motifs,
                        required=True,
                    ),
                },
                hide_index=True,
                use_container_width=True,
                key=f"editor_censeur_{classe_choisie}_{date_appel}",
            )

            # --- BOUTONS D'ACTIONS ---
            col_exp1, col_exp2, col_exp3, col_exp4 = st.columns([2, 1.2, 1.2, 2])

            with col_exp1:
                if st.button(
                    "🛡️ Enregistrer les modifications de la Censure", type="primary"
                ):
                    eleve_ids = [
                        row["eleve_id"] for _, row in edited_df_censeur.iterrows()
                    ]
                    db.query(Presence).filter(
                        Presence.school_id == target_school_id,
                        Presence.date == date_appel,
                        Presence.eleve_id.in_(eleve_ids),
                    ).delete(synchronize_session=False)

                    for _, row in edited_df_censeur.iterrows():
                        nouvelle_presence = Presence(
                            school_id=target_school_id,
                            eleve_id=row["eleve_id"],
                            date=date_appel,
                            statut=row["Statut"],
                            motif=(
                                row["Motif / Remarque"].strip()
                                if row["Motif / Remarque"]
                                and row["Motif / Remarque"] != "Aucun"
                                else None
                            ),
                        )
                        db.add(nouvelle_presence)

                    nouveau_log = ActivityLog(
                        school_id=target_school_id,
                        timestamp=datetime.now(),
                        username=username,
                        action=(
                            f"Validation/Régularisation censure — Classe {classe_choisie}"
                            f" ({date_appel.strftime('%d/%m/%Y')}) par {username}"
                        ),
                        module="Présence",
                        statut="Succès",
                    )
                    db.add(nouveau_log)
                    db.commit()

                    st.success(
                        f"✅ Registre officiel de la classe **{classe_choisie}** mis à jour"
                        " et archivé avec succès !"
                    )
                    st.rerun()

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
                    fontSize=14,
                    textColor=colors.HexColor("#1e3a8a"),
                    alignment=1,
                    spaceAfter=15,
                )

                elements.append(
                    Paragraph(
                        f"REGISTRE DE PRÉSENCE ({libelle_annee}) — CLASSE : {classe_choisie} ({school_name}) — Date : {date_appel.strftime('%d/%m/%Y')}",
                        title_style,
                    )
                )
                elements.append(Spacer(1, 10))

                df_pdf = df_suivi.drop(columns=["eleve_id"]) if "eleve_id" in df_suivi.columns else df_suivi
                table_data = [list(df_pdf.columns)]
                for _, row in df_pdf.iterrows():
                    table_data.append([str(val) for val in row])

                col_widths = [780 / len(df_pdf.columns)] * len(df_pdf.columns)
                t = Table(table_data, colWidths=col_widths)
                t.setStyle(
                    TableStyle([
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a8a")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 9),
                        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f8fafc")),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                        ("FONTSIZE", (0, 1), (-1, -1), 9),
                        ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
                        ("TOPPADDING", (0, 1), (-1, -1), 6),
                    ])
                )
                elements.append(t)

                def add_footer(canvas, doc_obj):
                    canvas.saveState()
                    footer_y = 22
                    footer_text = f"<b>{school_name}</b> | Adresse : {school_adresse} | Contacts : {school_contacts} | Devise : <i>{school_devise}</i>"
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
                    file_name=f"Registre_Presence_{classe_choisie}_{date_appel.strftime('%Y%m%d')}.pdf",
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

            with col_exp4:
                csv_data = df_suivi.drop(columns=["eleve_id"]).to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="📥 CSV",
                    data=csv_data,
                    file_name=(
                        f"appel_{classe_choisie}_{date_appel.strftime('%Y%m%d')}.csv"
                    ),
                    mime="text/csv",
                )

        else:
            # ==========================================
            # ESPACE ENSEIGNANT
            # ==========================================
            st.info(
                f"👨‍🏫 Espace Enseignant — Feuille d'appel active pour la classe de"
                f" **{classe_choisie}** ({len(eleves)} élèves)."
            )

            data_appel = []
            for e in eleves:
                p_ex = dict_existantes.get(e.id)
                statut_defaut = p_ex.statut if p_ex else "Présent"
                motif_defaut = p_ex.motif if p_ex and p_ex.motif in liste_motifs else "Aucun"

                data_appel.append({
                    "eleve_id": e.id,
                    "Matricule": e.matricule,
                    "Nom & Prénom": f"{e.nom} {e.prenom}",
                    "Statut": statut_defaut,
                    "Motif": motif_defaut,
                })

            df_appel = pd.DataFrame(data_appel)

            edited_df = st.data_editor(
                df_appel,
                column_config={
                    "eleve_id": None,
                    "Matricule": st.column_config.TextColumn(
                        "Matricule", disabled=True
                    ),
                    "Nom & Prénom": st.column_config.TextColumn(
                        "Nom & Prénom", disabled=True
                    ),
                    "Statut": st.column_config.SelectboxColumn(
                        "Statut",
                        options=liste_statuts_assiduite,
                        required=True,
                    ),
                    "Motif": st.column_config.SelectboxColumn(
                        "Précisions / Motif (si absent ou retard)",
                        options=liste_motifs,
                        required=True,
                    ),
                },
                hide_index=True,
                use_container_width=True,
                key=f"editor_presence_{classe_choisie}_{date_appel}",
            )

            col_ens1, col_ens2 = st.columns(2)
            with col_ens1:
                if st.button(
                    "💾 Transmettre l'appel à la Censure", type="primary"
                ):
                    eleve_ids = [row["eleve_id"] for _, row in edited_df.iterrows()]
                    db.query(Presence).filter(
                        Presence.school_id == target_school_id,
                        Presence.date == date_appel,
                        Presence.eleve_id.in_(eleve_ids),
                    ).delete(synchronize_session=False)

                    for _, row in edited_df.iterrows():
                        nouvelle_presence = Presence(
                            school_id=target_school_id,
                            eleve_id=row["eleve_id"],
                            date=date_appel,
                            statut=row["Statut"],
                            motif=row["Motif"].strip() if row["Motif"] and row["Motif"] != "Aucun" else None,
                        )
                        db.add(nouvelle_presence)

                    nouveau_log = ActivityLog(
                        school_id=target_school_id,
                        timestamp=datetime.now(),
                        username=username,
                        action=(
                            f"Saisie appel de classe - {classe_choisie}"
                            f" ({date_appel.strftime('%d/%m/%Y')}) par le professeur"
                            f" {username}"
                        ),
                        module="Présence",
                        statut="Succès",
                    )
                    db.add(nouveau_log)
                    db.commit()

                    st.success(
                        f"✅ Feuille d'appel transmise avec succès pour la classe"
                        f" **{classe_choisie}** !"
                    )
                    st.rerun()

            with col_ens2:
                csv_data_ens = df_appel.drop(columns=["eleve_id"]).to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="📥 Télécharger la feuille (CSV)",
                    data=csv_data_ens,
                    file_name=(
                        f"appel_{classe_choisie}_{date_appel.strftime('%Y%m%d')}.csv"
                    ),
                    mime="text/csv",
                )

        # --- PIED DE PAGE INSTITUTIONNEL ---
        st.markdown(
            f"""
            <div class="print-footer" style="margin-top: 40px; padding: 15px; border-top: 1px solid rgba(255,255,255,0.1); text-align: center; color: #94a3b8; font-size: 0.85rem;">
                <b>{school_name}</b> | Adresse : {school_adresse} | Contacts : {school_contacts} | Devise : <i>{school_devise}</i>
            </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    finally:
        db.close()


# Alias de compatibilité
afficher_gestion_presence = afficher_presence
afficher_presence = afficher_presence
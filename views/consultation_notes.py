from datetime import datetime
from io import BytesIO
from database.db_config import SessionLocal
from database.models import ActivityLog, AnneeScolaire, Classe, Eleve, Matiere, Note, School
from database.queries import get_classes_cached, get_matieres_cached
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import reportlab
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle


def afficher_consultation_notes():
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

    st.subheader("📊 Consultation Détaillée des Notes & Résultats")
    st.markdown(
        "Recherche et affichage dynamique des notes par évaluation, ou des"
        " moyennes par semestre et annuelle avec isolation multi-tenant et"
        " persistance en base de données."
    )
    st.markdown("---")

    school_id = st.session_state.get("school_id")
    is_super_admin = st.session_state.get("is_super_admin", False)

    db = SessionLocal()
    try:
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
                AnneeScolaire.school_id == school_id,
                AnneeScolaire.active == True,
            )
            .first()
        )
        libelle_annee = annee_active.libelle if annee_active else str(datetime.now().year)

    finally:
        db.close()

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

        # Isolation multi-écoles et multi-cycles pour les classes et matières
        classes_query = db.query(Classe).filter(Classe.cycle == cycle_en_cours)
        matieres_query = db.query(Matiere).filter(Matiere.cycle == cycle_en_cours)

        if not is_super_admin and school_id:
            classes_query = classes_query.filter(Classe.school_id == school_id)
            matieres_query = matieres_query.filter(Matiere.school_id == school_id)
        else:
            classes_query = classes_query.filter(
                Classe.school_id == target_school_id
            )
            matieres_query = matieres_query.filter(
                Matiere.school_id == target_school_id
            )

        classes_cycle = classes_query.all()
        matieres_cycle = matieres_query.all()

        # --- ZONE IMPRIMABLE ---
        st.markdown('<div class="printable-area">', unsafe_allow_html=True)

        st.markdown(
            f"### Consultation des Notes ({libelle_annee}) — **{school_name} ({cycle_en_cours})**"
        )

        if not classes_cycle:
            st.warning(
                f"⚠️ Aucune classe disponible pour le cycle **{cycle_en_cours}** dans"
                f" l'établissement **{school_name}**."
            )
            st.info(
                "Veuillez d'abord enregistrer vos classes dans le module **Classes &"
                " Tarifs** du menu latéral."
            )
            st.markdown("</div>", unsafe_allow_html=True)
            return

        noms_classes = [c.libelle for c in classes_cycle]

        # --- FILTRES DE CONSULTATION ---
        col_c1, col_c2, col_c3 = st.columns(3)
        with col_c1:
            classe_choisie = st.selectbox(
                "Sélectionner la classe", noms_classes, key="consult_notes_classe"
            )
        with col_c2:
            semestre_choisi = st.selectbox(
                "Semestre / Période",
                [
                    "Semestre 1",
                    "Semestre 2",
                    "Trimestre 1",
                    "Trimestre 2",
                    "Trimestre 3",
                ],
                key="consult_notes_semestre",
            )
        with col_c3:
            type_vue = st.selectbox(
                "Type d'affichage / Évaluation",
                [
                    "Interro 1",
                    "Interro 2",
                    "Devoir 1",
                    "Devoir 2",
                    "Compo",
                    "Moyen-S1",
                    "Moyen-S2",
                    "Moyen-an",
                ],
                key="consult_notes_vue",
            )

        classe_obj = next(
            (c for c in classes_cycle if c.libelle == classe_choisie), None
        )
        if classe_obj:
            eleves_query = db.query(Eleve).filter(Eleve.classe_id == classe_obj.id)
            if not is_super_admin and school_id:
                eleves_query = eleves_query.filter(Eleve.school_id == school_id)
            else:
                eleves_query = eleves_query.filter(
                    Eleve.school_id == target_school_id
                )
            eleves = eleves_query.order_by(Eleve.nom).all()

            if not eleves:
                st.info(
                    f"Aucun élève enregistré dans la classe de **{classe_choisie}**."
                )
                st.markdown("</div>", unsafe_allow_html=True)
            else:
                st.success(
                    f"Résultats affichés pour la classe de **{classe_choisie}** — Vue"
                    f" : **{type_vue}** ({semestre_choisi}) [{len(eleves)} élèves]."
                )

                # --- 1. AFFICHAGE DES NOTES PAR ÉVALUATION (Matrice Élèves x Matières) ---
                if type_vue in [
                    "Interro 1",
                    "Interro 2",
                    "Devoir 1",
                    "Devoir 2",
                    "Compo",
                ]:
                    notes_db = (
                        db.query(Note)
                        .join(Eleve)
                        .filter(
                            Note.school_id == target_school_id,
                            Eleve.classe_id == classe_obj.id,
                            Note.semestre == semestre_choisi,
                            Note.type_evaluation == type_vue,
                        )
                        .all()
                    )

                    dict_notes = {
                        (n.eleve_id, n.matiere_id): float(n.valeur) for n in notes_db if n.valeur is not None
                    }

                    dict_coeffs = {m.id: (m.coefficient or 1.0) for m in matieres_cycle}

                    data_tableau = []
                    for e in eleves:
                        sexe_eleve = str(getattr(e, "sexe", "M")).strip().upper()
                        ligne = {
                            "Matricule": e.matricule,
                            "Nom & Prénom": f"{e.nom} {e.prenom}",
                            "_sexe": sexe_eleve,
                        }
                        total_pts = 0.0
                        total_coefs = 0.0

                        for mat in matieres_cycle:
                            mat_lib = mat.libelle if hasattr(mat, 'libelle') else getattr(mat, 'nom', '')
                            val_note = dict_notes.get((e.id, mat.id), 0.0)
                            ligne[mat_lib] = f"{val_note:.2f}"
                            
                            c_val = dict_coeffs.get(mat.id, 1.0)
                            total_pts += val_note * c_val
                            total_coefs += c_val

                        moy_val = round(total_pts / total_coefs, 2) if total_coefs > 0 else 0.0
                        ligne["_moy_val"] = moy_val
                        ligne["Moyenne"] = f"{moy_val:.2f}/20"
                        
                        data_tableau.append(ligne)

                    # Tri des moyennes pour attribution du rang tenant compte du genre (1er / 1ère)
                    data_tableau = sorted(data_tableau, key=lambda x: x["_moy_val"], reverse=True)
                    for r_idx, item in enumerate(data_tableau, start=1):
                        sexe_val = item.get("_sexe", "M")
                        is_feminin = sexe_val in ["F", "FÉMININ", "FEMININ", "FILLE"]
                        
                        if r_idx == 1:
                            item["Rang"] = "1ère" if is_feminin else "1er"
                        else:
                            item["Rang"] = f"{r_idx}ème" if is_feminin else f"{r_idx}è"
                            
                        item.pop("_moy_val", None)
                        item.pop("_sexe", None)

                    df_res = pd.DataFrame(data_tableau)

                    # --- BOUTONS D'ACTIONS (PDF, IMPRESSION, CSV) ---
                    col_ex1, col_ex2, col_ex3, _ = st.columns([1.3, 1.3, 1.3, 3.5])

                    with col_ex1:
                        pdf_buffer = BytesIO()
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
                            fontSize=13,
                            textColor=colors.HexColor("#1e3a8a"),
                            alignment=1,
                            spaceAfter=15,
                        )

                        elements.append(
                            Paragraph(
                                f"CONSULTATION DES NOTES ({libelle_annee}) — CLASSE : {classe_choisie} ({type_vue} - {semestre_choisi}) — {school_name}",
                                title_style,
                            )
                        )
                        elements.append(Spacer(1, 10))

                        table_data = [list(df_res.columns)]
                        for _, row in df_res.iterrows():
                            table_data.append([str(val) for val in row])

                        col_widths = [780 / len(df_res.columns)] * len(df_res.columns)
                        t = Table(table_data, colWidths=col_widths)
                        t.setStyle(
                            TableStyle([
                                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a8a")),
                                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                                ("FONTSIZE", (0, 0), (-1, 0), 8),
                                ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f8fafc")),
                                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
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
                            file_name=f"Consultation_Notes_{classe_choisie}_{type_vue}.pdf",
                            mime="application/pdf",
                        )

                    with col_ex2:
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

                    with col_ex3:
                        st.download_button(
                            label="📥 CSV",
                            data=df_res.to_csv(index=False).encode("utf-8"),
                            file_name=(
                                f"consultation_notes_{classe_choisie}_{type_vue}_"
                                f"{semestre_choisi.replace(' ', '')}.csv"
                            ),
                            mime="text/csv",
                        )

                    st.markdown("<br>", unsafe_allow_html=True)
                    st.dataframe(df_res, use_container_width=True)

                    # --- STATISTIQUES ET SYNTHÈSE PÉDAGOGIQUE ---
                    st.markdown("### 📈 Indicateurs & Synthèse Pédagogique")

                    stats_matieres = []
                    for mat in matieres_cycle:
                        mat_lib = mat.libelle if hasattr(mat, 'libelle') else getattr(mat, 'nom', '')
                        notes_mat = [
                            dict_notes.get((e.id, mat.id), 0.0)
                            for e in eleves
                        ]
                        if notes_mat:
                            moy_mat = round(sum(notes_mat) / len(notes_mat), 2)
                            max_mat = max(notes_mat)
                            min_mat = min(notes_mat)
                        else:
                            moy_mat, max_mat, min_mat = 0.0, 0.0, 0.0

                        stats_matieres.append({
                            "Matière": mat_lib,
                            "Moyenne de classe": f"{moy_mat:.2f}",
                            "Plus forte moyenne": f"{max_mat:.2f}",
                            "Plus faible moyenne": f"{min_mat:.2f}",
                        })

                    df_stats = pd.DataFrame(stats_matieres)
                    st.dataframe(df_stats, use_container_width=True)

                # --- 2. AFFICHAGE DES MOYENNES ---
                else:
                    if type_vue == "Moyen-S1":
                        semestres_cibles = ["Semestre 1", "Trimestre 1", "Trimestre 2"]
                    elif type_vue == "Moyen-S2":
                        semestres_cibles = ["Semestre 2", "Trimestre 3"]
                    else:
                        semestres_cibles = None

                    query_notes = (
                        db.query(Note)
                        .join(Eleve)
                        .filter(
                            Note.school_id == target_school_id,
                            Eleve.classe_id == classe_obj.id,
                        )
                    )
                    if semestres_cibles:
                        query_notes = query_notes.filter(
                            Note.semestre.in_(semestres_cibles)
                        )

                    toutes_notes = query_notes.all()

                    stats_eleves = {}
                    for e in eleves:
                        stats_eleves[e.id] = {
                            "total_points": 0.0,
                            "total_coeffs": 0.0,
                            "nb_notes": 0,
                            "sexe": str(getattr(e, "sexe", "M")).strip().upper(),
                        }

                    dict_coeffs = {m.id: m.coefficient for m in matieres_cycle}

                    for n in toutes_notes:
                        if n.eleve_id in stats_eleves:
                            coeff = dict_coeffs.get(n.matiere_id, 1.0)
                            stats_eleves[n.eleve_id]["total_points"] += n.valeur * coeff
                            stats_eleves[n.eleve_id]["total_coeffs"] += coeff
                            stats_eleves[n.eleve_id]["nb_notes"] += 1

                    data_moyennes = []
                    for e in eleves:
                        st_el = stats_eleves[e.id]
                        if st_el["total_coeffs"] > 0:
                            moyenne = round(
                                st_el["total_points"] / st_el["total_coeffs"], 2
                            )
                        else:
                            moyenne = 0.0

                        data_moyennes.append({
                            "eleve_id": e.id,
                            "Matricule": e.matricule,
                            "Nom & Prénom": f"{e.nom} {e.prenom}",
                            "Moyenne": moyenne,
                            "sexe": st_el["sexe"],
                        })

                    data_moyennes.sort(
                        key=lambda x: x["Moyenne"],
                        reverse=True,
                    )

                    tableau_final = []
                    for idx, item in enumerate(data_moyennes):
                        moy_val = item["Moyenne"]
                        moy_str = f"{moy_val:.2f}/20"
                        
                        is_feminin = item["sexe"] in ["F", "FÉMININ", "FEMININ", "FILLE"]
                        if idx == 0:
                            rang = "1ère" if is_feminin else "1er"
                        else:
                            rang = f"{idx + 1}ème" if is_feminin else f"{idx + 1}è"

                        if moy_val >= 16:
                            mention = "Très Bien"
                        elif moy_val >= 14:
                            mention = "Bien"
                        elif moy_val >= 12:
                            mention = "Assez Bien"
                        elif moy_val >= 10:
                            mention = "Passable"
                        else:
                            mention = "Insuffisant"

                        tableau_final.append({
                            "Rang": rang,
                            "Matricule": item["Matricule"],
                            "Nom & Prénom": item["Nom & Prénom"],
                            "Moyenne Périodique": moy_str,
                            "Mention": mention,
                        })

                    df_moy = pd.DataFrame(tableau_final)
                    st.dataframe(df_moy, use_container_width=True)

                    st.download_button(
                        label="📥 Télécharger le procès-verbal des moyennes (CSV)",
                        data=df_moy.to_csv(index=False).encode("utf-8"),
                        file_name=(
                            f"moyennes_{classe_choisie}_{type_vue}_"
                            f"{semestre_choisi.replace(' ', '')}.csv"
                        ),
                        mime="text/csv",
                    )

                # Traçabilité dans le journal d'activité
                nouveau_log = ActivityLog(
                    school_id=target_school_id,
                    timestamp=datetime.utcnow(),
                    username=st.session_state.get("username", "admin"),
                    action=(
                        f"Consultation des notes ({type_vue} - {semestre_choisi}) -"
                        f" Classe {classe_choisie}"
                    ),
                    module="Consultation des notes",
                    statut="Succès",
                )
                db.add(nouveau_log)
                db.commit()

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


# Alias de compatibilité complète pour le routeur
afficher_consultation_notes = afficher_consultation_notes
afficher_consultation_des_notes = afficher_consultation_notes
afficher_consultations_notes = afficher_consultation_notes
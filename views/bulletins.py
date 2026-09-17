import base64
from datetime import datetime
from io import BytesIO
import os
import streamlit as st
import streamlit.components.v1 as components
from database.db_config import SessionLocal
from database.models import ActivityLog, Classe, Eleve, Matiere, Note, School


def get_image_base64(path):
    if os.path.exists(path):
        with open(path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode()
    return ""


def afficher_bulletins(niveau_actif="Collège"):
    school_id = st.session_state.get("school_id")
    is_super_admin = st.session_state.get("is_super_admin", False)
    username = st.session_state.get("username", "admin")

    db = SessionLocal()
    try:
        target_school_id = school_id
        if is_super_admin and not target_school_id:
            ecole_defaut = db.query(School).first()
            target_school_id = ecole_defaut.id if ecole_defaut else 1

        ecole_active_id = school_id if school_id else target_school_id

        nom_ecole = "COMPLEXE SCOLAIRE PRIVE RAHMAT-FH"
        devise_ecole = "Excellence - Persévérance - Réussite"
        adresse_ecole = "QUARTIER AEROPORT NIAMEY-NIGER"
        contacts_ecole = "TEL : 99 79 71 63 / 97 32 77 52 / 92 53 27 10"

        if ecole_active_id:
            ecole = db.query(School).filter(School.id == ecole_active_id).first()
            if ecole:
                nom_ecole = ecole.nom.upper()
                devise_ecole = getattr(ecole, "devise", devise_ecole)
                adresse_ecole = getattr(ecole, "adresse", adresse_ecole).upper()
                contacts_ecole = getattr(ecole, "contacts", contacts_ecole)

        st.subheader("📄 Édition des Bulletins Scolaires Officiels")
        st.markdown(
            f"Générez, imprimez et vérifiez l'authenticité des bulletins conformes"
            f" au modèle institutionnel de **{nom_ecole}** pour le cycle : **{niveau_actif}**."
        )
        st.markdown("---")

        classes_query = db.query(Classe).filter(Classe.cycle == niveau_actif)
        if hasattr(Classe, "deleted_at"):
            classes_query = classes_query.filter(Classe.deleted_at.is_(None))

        if school_id:
            classes_query = classes_query.filter(Classe.school_id == school_id)
        else:
            classes_query = classes_query.filter(
                Classe.school_id == target_school_id
            )

        classes = classes_query.all()

        if not classes:
            st.warning(
                f"Aucune classe active disponible pour le cycle {niveau_actif} dans cet établissement."
            )
            return

        def get_label(obj):
            for attr in ["libelle", "nom", "name", "titre"]:
                if hasattr(obj, attr):
                    return getattr(obj, attr)
            return f"ID {obj.id}"

        with st.container():
            st.markdown("### ⚙️ Paramètres d'Édition & Filtres")
            col_f1, col_f2, col_f3 = st.columns(3)

            with col_f1:
                classe_noms = {get_label(c): c.id for c in classes}
                classe_choisie = st.selectbox(
                    "🏫 Sélectionnez la Classe :",
                    options=list(classe_noms.keys()),
                )
                classe_id = classe_noms[classe_choisie]

            with col_f2:
                semestre = st.selectbox(
                    "📅 Période Académique :", options=["Semestre 1", "Semestre 2"]
                )

            with col_f3:
                portee = st.radio(
                    "🎯 Portée de l'édition :",
                    options=["Élève unique", "Toute la classe"],
                    horizontal=True,
                )

        eleves_query = db.query(Eleve).filter(Eleve.classe_id == classe_id)
        if hasattr(Eleve, "deleted_at"):
            eleves_query = eleves_query.filter(Eleve.deleted_at.is_(None))

        if school_id:
            eleves_query = eleves_query.filter(Eleve.school_id == school_id)
        else:
            eleves_query = eleves_query.filter(
                Eleve.school_id == target_school_id
            )

        eleves = eleves_query.all()

        if not eleves:
            st.info(
                f"Aucun élève actif inscrit dans la classe de {classe_choisie}."
            )
            return

        eleve_id_selectionne = None
        if portee == "Élève unique":
            st.markdown("")
            eleve_dict = {
                f"{getattr(e, 'matricule', 'N/A')} - {e.nom} {e.prenom}": e.id
                for e in eleves
            }
            eleve_choisi_str = st.selectbox(
                "👨‍🎓 Sélectionnez l'Élève :", options=list(eleve_dict.keys())
            )
            eleve_id_selectionne = eleve_dict[eleve_choisi_str]

        st.markdown("---")

        nouveau_log = ActivityLog(
            school_id=ecole_active_id,
            timestamp=datetime.utcnow(),
            username=username,
            action=(
                f"Édition des bulletins ({semestre}) pour la classe de"
                f" {classe_choisie} ({nom_ecole})"
            ),
            module="Bulletins",
            statut="Succès",
        )
        db.add(nouveau_log)
        db.commit()

        matieres_query = db.query(Matiere).filter(
            Matiere.cycle == niveau_actif
        )
        if hasattr(Matiere, "deleted_at"):
            matieres_query = matieres_query.filter(Matiere.deleted_at.is_(None))

        if school_id:
            matieres_query = matieres_query.filter(
                Matiere.school_id == school_id
            )
        else:
            matieres_query = matieres_query.filter(
                Matiere.school_id == target_school_id
            )

        matieres_brutes = matieres_query.all()
        matieres_dict_unique = {}
        for m in matieres_brutes:
            nom_m = get_label(m)
            if nom_m not in matieres_dict_unique:
                matieres_dict_unique[nom_m] = m

        matieres_toutes = list(matieres_dict_unique.values())

        is_troisieme = (
            "3" in classe_choisie.upper()
            or "TROISIEME" in classe_choisie.upper()
        )
        matieres = []
        for m in matieres_toutes:
            nom_m_lower = get_label(m).lower()
            if is_troisieme and (
                "economie familiale" in nom_m_lower
                or "familiale et sociale" in nom_m_lower
            ):
                continue
            matieres.append(m)

        toutes_notes_classe = (
            db.query(Note).join(Eleve).filter(Eleve.classe_id == classe_id).all()
        )
        notes_periode = [
            n
            for n in toutes_notes_classe
            if str(getattr(n, "semestre", "")) == str(semestre)
        ]
        notes_s1 = [
            n
            for n in toutes_notes_classe
            if str(getattr(n, "semestre", "")) in ["Semestre 1"]
        ]

        def calculer_moyennes_notes(notes_subset):
            matrice = {}
            for n in notes_subset:
                e_id = n.eleve_id
                m_id = getattr(n, "matiere_id", None)
                val = float(getattr(n, "valeur", 0.0))
                if e_id not in matrice:
                    matrice[e_id] = {}
                if m_id not in matrice[e_id]:
                    matrice[e_id][m_id] = []
                matrice[e_id][m_id].append(val)

            moy_dict = {}
            for e in eleves:
                notes_e = matrice.get(e.id, {})
                if notes_e:
                    mots_moy = []
                    for m in matieres:
                        if m.id in notes_e and notes_e[m.id]:
                            mots_moy.append(sum(notes_e[m.id]) / len(notes_e[m.id]))
                    moy_dict[e.id] = (
                        round(sum(mots_moy) / len(mots_moy), 2)
                        if mots_moy
                        else 0.0
                    )
                else:
                    moy_dict[e.id] = 0.0
            return matrice, moy_dict

        matrice_notes, moyennes_generales = calculer_moyennes_notes(notes_periode)
        _, moyennes_s1 = calculer_moyennes_notes(notes_s1)

        moyennes_annuelles = {}
        for e in eleves:
            m_s1 = moyennes_s1.get(e.id, 0.0)
            m_s2 = moyennes_generales.get(e.id, 0.0)
            if ("2" in semestre) and (m_s1 > 0 or m_s2 > 0):
                moyennes_annuelles[e.id] = round((m_s1 + m_s2) / 2.0, 2)
            else:
                moyennes_annuelles[e.id] = m_s2 if ("2" in semestre) else m_s1

        classement_trie = sorted(
            moyennes_generales.items(), key=lambda x: x[1], reverse=True
        )
        classement_annuel_trie = sorted(
            moyennes_annuelles.items(), key=lambda x: x[1], reverse=True
        )

        effectif = len(eleves)
        garcons = sum(
            1
            for el in eleves
            if str(getattr(el, "sexe", "")).strip().upper()
            in ["M", "MASCULIN", "GARÇON", "GARCON", "G"]
        )
        filles = sum(
            1
            for el in eleves
            if str(getattr(el, "sexe", "")).strip().upper()
            in ["F", "FÉMININ", "FEMININ", "FILLE"]
        )

        logo_b64 = get_image_base64("Logo CSP-RAHMAT-FH.png")
        logo_img_tag = (
            f'<img src="data:image/png;base64,{logo_b64}" style="max-height: 40px; max-width: 40px; object-fit: contain;" />'
            if logo_b64
            else "<b>LOGO</b>"
        )

        vals_moyennes = [v for v in moyennes_generales.values() if v > 0]
        moy_classe_val = (
            round(sum(vals_moyennes) / len(vals_moyennes), 2)
            if vals_moyennes
            else 0.0
        )
        max_moy_val = round(max(vals_moyennes), 2) if vals_moyennes else 0.0
        min_moy_val = round(min(vals_moyennes), 2) if vals_moyennes else 0.0

        def rendre_bulletin(eleve_obj):
            moy_eleve = moyennes_generales.get(eleve_obj.id, 0.0)
            moy_s1_eleve = moyennes_s1.get(eleve_obj.id, 0.0)
            moy_annuelle_eleve = moyennes_annuelles.get(eleve_obj.id, 0.0)

            position_idx = 1
            for idx, (id_el, _) in enumerate(classement_trie, start=1):
                if id_el == eleve_obj.id:
                    position_idx = idx
                    break

            position_annuelle_idx = 1
            for idx, (id_el, _) in enumerate(classement_annuel_trie, start=1):
                if id_el == eleve_obj.id:
                    position_annuelle_idx = idx
                    break

            sexe_eleve = str(getattr(eleve_obj, "sexe", "")).strip().upper()
            is_fille = sexe_eleve in ["F", "FÉMININ", "FEMININ", "FILLE"]
            rang_eleve = (
                "1ère"
                if (position_idx == 1 and is_fille)
                else ("1er" if position_idx == 1 else f"{position_idx} ème")
            )
            rang_annuel = (
                "1ère"
                if (position_annuelle_idx == 1 and is_fille)
                else (
                    "1er"
                    if position_annuelle_idx == 1
                    else f"{position_annuelle_idx} ème"
                )
            )

            conduite_obj = next(
                (
                    m
                    for m in matieres
                    if "conduite"
                    in (
                        m.libelle
                        if hasattr(m, "libelle")
                        else getattr(m, "nom", "")
                    ).lower()
                ),
                None,
            )
            note_conduite_eleve = 18.0
            if conduite_obj:
                notes_cond_list = matrice_notes.get(eleve_obj.id, {}).get(
                    conduite_obj.id, []
                )
                if notes_cond_list:
                    note_conduite_eleve = sum(notes_cond_list) / len(
                        notes_cond_list
                    )

            box_checked = '<span style="display:inline-block; width:11px; height:11px; border:1px solid #000; text-align:center; line-height:10px; font-weight:bold; font-size:9px; background-color:#e2e8f0; margin-right:3px;">X</span>'
            box_unchecked = '<span style="display:inline-block; width:11px; height:11px; border:1px solid #000; margin-right:3px; vertical-align:middle;"></span>'

            chk_bien = box_checked if note_conduite_eleve >= 14 else box_unchecked
            chk_passable = box_checked if 10 <= note_conduite_eleve < 14 else box_unchecked
            chk_mal = box_checked if 8 <= note_conduite_eleve < 10 else box_unchecked
            chk_avertissement = box_checked if 6 <= note_conduite_eleve < 8 else box_unchecked
            chk_blame = box_checked if note_conduite_eleve < 6 else box_unchecked

            chk_inscrit = box_checked if moy_eleve >= 10 else box_unchecked
            chk_felicitations = box_checked if moy_eleve >= 16 else box_unchecked
            chk_encouragements = box_checked if 14 <= moy_eleve < 16 else box_unchecked
            chk_non_inscrit = box_checked if moy_eleve < 10 else box_unchecked

            lignes_html = ""
            total_coef = 0
            total_moyen_coef = 0
            notes_eleve = matrice_notes.get(eleve_obj.id, {})

            for m in matieres:
                m_nom = get_label(m)
                notes_m = notes_eleve.get(m.id, [])
                coef = int(getattr(m, "coefficient", 2) or 2)

                if notes_m:
                    note_classe = sum(notes_m) / len(notes_m)
                    note_compo = note_classe
                    moyen_coef = note_classe * coef
                    total_coef += coef
                    total_moyen_coef += moyen_coef

                    appreciation = (
                        "Très Bien"
                        if note_classe >= 16
                        else (
                            "Bien"
                            if note_classe >= 14
                            else (
                                "Assez Bien"
                                if note_classe >= 12
                                else ("Passable" if note_classe >= 10 else "Faible")
                            )
                        )
                    )
                    note_classe_str = f"{note_classe:.2f}"
                    note_compo_str = f"{note_compo:.2f}"
                    moyen_coef_str = f"{round(moyen_coef, 2):.2f}"
                    rang_str = rang_eleve
                else:
                    note_classe_str = ""
                    note_compo_str = ""
                    moyen_coef_str = ""
                    appreciation = "Non noté"
                    rang_str = ""

                lignes_html += f"""
                            <tr style="height: 28px; min-height: 28px; max-height: 28px;">
                                <td style="border: 1px solid #000080; padding: 4px 8px; text-align: left; font-size: 0.8rem; height: 28px; line-height: 18px; overflow: hidden; white-space: nowrap; text-overflow: ellipsis;">{m_nom}</td>
                                <td style="border: 1px solid #000080; padding: 4px 8px; text-align: center; font-size: 0.8rem; height: 28px; line-height: 18px;">{note_classe_str}</td>
                                <td style="border: 1px solid #000080; padding: 4px 8px; text-align: center; font-size: 0.8rem; height: 28px; line-height: 18px;">{note_compo_str}</td>
                                <td style="border: 1px solid #000080; padding: 4px 8px; text-align: center; font-size: 0.8rem; height: 28px; line-height: 18px;">{coef}</td>
                                <td style="border: 1px solid #000080; padding: 4px 8px; text-align: center; font-size: 0.8rem; height: 28px; line-height: 18px;">{moyen_coef_str}</td>
                                <td style="border: 1px solid #000080; padding: 4px 8px; text-align: center; font-size: 0.8rem; height: 28px; line-height: 18px;">{rang_str}</td>
                                <td style="border: 1px solid #000080; padding: 4px 8px; text-align: center; font-size: 0.8rem; height: 28px; line-height: 18px;">{appreciation if note_classe_str else ''}</td>
                                <td style="border: 1px solid #000080; padding: 4px 8px; text-align: center; font-size: 0.8rem; height: 28px; line-height: 18px;"></td>
                            </tr>
                        """

            recap_annuel_html = ""
            if "2" in semestre:
                recap_annuel_html = f"""
                        <div style="border: 1px solid #000080; background-color: #000080; color: #FFFFFF; padding: 5px; text-align: center; font-size: 0.8rem; margin-bottom: 6px;">
                            <div style="display: flex; justify-content: space-around; font-weight: bold;">
                                <span>Moyenne S1 : <b>{moy_s1_eleve:.2f} / 20</b></span>
                                <span>Moyenne Actuelle : <b>{moy_eleve:.2f} / 20</b></span>
                                <span style="color: #38BDF8;">Moyenne Annuelle : <b>{moy_annuelle_eleve:.2f} / 20</b> (Rang : {rang_annuel})</span>
                            </div>
                        </div>
                        """

            verification_url = f"https://api.whatsapp.com/send?phone=22799797163&text=Bonjour,%20je%20souhaite%20verifier%20l'authenticite%20du%20bulletin%20de%20l'eleve%20{getattr(eleve_obj, 'nom', '')}%20{getattr(eleve_obj, 'prenom', '')}%20(Matricule:%20{getattr(eleve_obj, 'matricule', 'N/A')})."
            qr_code_api = f"https://api.qrserver.com/v1/create-qr-code/?size=100x100&data={verification_url}"

            conduite_classe_val = 18.0

            bulletin_html = f"""
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <meta charset="utf-8">
                        <style>
                            @page {{
                                size: A4 portrait;
                                margin: 5mm;
                            }}
                            @media print {{
                                body {{ background: #FFFFFF; margin: 0; }}
                                .no-print {{ display: none !important; }}
                                .bulletin-page {{
                                    border: 2px solid #000080 !important;
                                    box-shadow: none !important;
                                    margin: 0 auto !important;
                                    padding: 10mm 12mm !important;
                                    width: 195mm !important;
                                    box-sizing: border-box !important;
                                }}
                            }}
                            body {{ 
                                background: #f0f2f5; 
                                font-family: Arial, sans-serif; 
                                margin: 0; 
                                padding: 10px 0;
                            }}
                            .print-container {{
                                text-align: center;
                                margin-bottom: 12px;
                            }}
                            .print-btn {{
                                background-color: #ff8800;
                                color: white;
                                padding: 10px 24px;
                                font-size: 14px;
                                font-weight: bold;
                                border: none;
                                border-radius: 6px;
                                cursor: pointer;
                                box-shadow: 0 2px 4px rgba(0,0,0,0.2);
                            }}
                            .print-btn:hover {{
                                background-color: #e07700;
                            }}
                            .bulletin-page {{
                                width: 210mm;
                                max-width: 100%;
                                padding: 10mm 12mm;
                                margin: 15px auto;
                                background-color: #FFFFFF;
                                color: #000000;
                                border: 2px solid #000080;
                                box-sizing: border-box;
                                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                            }}
                        </style>
                    </head>
                    <body>
                        <div class="print-container no-print">
                            <button class="print-btn" onclick="window.print()">🖨️ Imprimer / Enregistrer en PDF (A4)</button>
                        </div>

                        <div class="bulletin-page">
                            <div style="border: 1px solid #000080; padding: 6px; margin-bottom: 6px;">
                                <div style="display: flex; justify-content: space-between; align-items: center;">
                                    <div style="text-align: left; width: 38%; font-size: 0.68rem; font-weight: bold; line-height: 1.25;">
                                        REPUBLIQUE DU NIGER<br>
                                        MINISTERE DE L'EDUCATION NATIONALE<br>
                                        <span style="color: #000080;">{nom_ecole}</span><br>
                                        <span style="font-size: 0.6rem; font-weight: normal; font-style: italic;">{devise_ecole}</span>
                                    </div>
                                    <div style="text-align: center; width: 24%;">
                                        <img src="{qr_code_api}" style="width: 50px; height: 50px; display: block; margin: 0 auto;" alt="QR Code" />
                                    </div>
                                    <div style="text-align: right; width: 38%;">
                                        {logo_img_tag}
                                    </div>
                                </div>
                            </div>

                            <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #000080; padding-bottom: 4px; margin-bottom: 6px; font-size: 0.85rem;">
                                <div style="font-weight: bold; color: #000080;">{nom_ecole}</div>
                                <div style="text-align: center;">
                                    <b>BULLETIN : {semestre.upper()}</b><br>
                                    <span style="font-size: 0.75rem;">Année Scolaire : 2026-2027</span>
                                </div>
                                <div></div>
                            </div>

                            <div style="display: flex; justify-content: space-between; border: 1px solid #000080; padding: 8px 12px; margin-bottom: 6px; font-size: 0.8rem; background: #FAFAFA;">
                                <div style="line-height: 1.35;">
                                    <b>Nom et Prénom :</b> {getattr(eleve_obj, 'nom', '')} {getattr(eleve_obj, 'prenom', '')}<br>
                                    <b>Matricule :</b> {getattr(eleve_obj, 'matricule', 'N/A')}<br>
                                    <b>Moyenne :</b> {moy_eleve:.2f} / 20<br>
                                    <b>Rang :</b> {rang_eleve}
                                </div>
                                <div style="line-height: 1.35;">
                                    <b>Classe :</b> {classe_choisie}<br>
                                    <b>Effectif :</b> {effectif}<br>
                                    <b>Garçons :</b> {garcons}<br>
                                    <b>Filles :</b> {filles}
                                </div>
                            </div>

                            <table style="width: 100%; border-collapse: collapse; font-size: 0.8rem; margin-bottom: 6px; table-layout: fixed;">
                                <colgroup>
                                    <col style="width: 24%;">
                                    <col style="width: 10%;">
                                    <col style="width: 10%;">
                                    <col style="width: 7%;">
                                    <col style="width: 11%;">
                                    <col style="width: 8%;">
                                    <col style="width: 16%;">
                                    <col style="width: 14%;">
                                </colgroup>
                                <thead>
                                    <tr style="background-color: #800020; color: #FFFFFF; text-align: center; height: 28px;">
                                        <th style="border: 1px solid #000080; padding: 4px;">Matières</th>
                                        <th style="border: 1px solid #000080; padding: 4px;">Note Classe</th>
                                        <th style="border: 1px solid #000080; padding: 4px;">Note Compo</th>
                                        <th style="border: 1px solid #000080; padding: 4px;">Coef</th>
                                        <th style="border: 1px solid #000080; padding: 4px;">Moyen Coef</th>
                                        <th style="border: 1px solid #000080; padding: 4px;">Rang</th>
                                        <th style="border: 1px solid #000080; padding: 4px;">Appréciation</th>
                                        <th style="border: 1px solid #000080; padding: 4px;">Signature</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {lignes_html}
                                </tbody>
                            </table>

                            <div style="border: 1px solid #000080; background-color: #000080; color: #FFFFFF; padding: 6px; text-align: center; font-size: 0.8rem; margin-bottom: 6px;">
                                <div style="display: flex; justify-content: space-around; font-weight: bold;">
                                    <span>Total de la période</span>
                                    <span>{total_coef}</span>
                                    <span>{total_moyen_coef:.2f} sur {total_coef * 20}</span>
                                </div>
                                <div style="display: flex; justify-content: space-around; margin-top: 3px; font-weight: bold; border-top: 1px solid #334155; padding-top: 3px;">
                                    <span>Moyenne Périodique</span>
                                    <span style="color: #FBBF24;">{moy_eleve:.2f} sur 20</span>
                                </div>
                            </div>

                            {recap_annuel_html}

                            <div style="display: grid; grid-template-columns: 1.4fr 1.2fr 1.3fr 1fr; border: 1px solid #000080; font-size: 0.75rem; margin-bottom: 6px; background: #FFFFFF;">
                                <div style="border-right: 1px solid #000080; padding: 6px; line-height: 1.4;">
                                    <b style="text-decoration: underline; display: block; text-align: center; margin-bottom: 3px; color: #000080;">Travail de la Classe</b>
                                    Conduite classe : {conduite_classe_val:.2f}<br>
                                    Moyenne classe : {moy_classe_val:.2f}<br>
                                    Plus Forte : {max_moy_val:.2f}<br>
                                    Plus Faible : {min_moy_val:.2f}<br>
                                    Nb Moyennes : {sum(1 for v in vals_moyennes if v >= 10)}
                                </div>
                                <div style="border-right: 1px solid #000080; padding: 6px; line-height: 1.5;">
                                    <b style="text-decoration: underline; display: block; text-align: center; margin-bottom: 3px; color: #000080;">Conduite</b>
                                    {chk_bien} Bien<br>{chk_passable} Passable<br>{chk_mal} Mal<br>{chk_avertissement} Avertissement<br>{chk_blame} Blame
                                </div>
                                <div style="border-right: 1px solid #000080; padding: 6px; line-height: 1.5;">
                                    <b style="text-decoration: underline; display: block; text-align: center; margin-bottom: 3px; color: #000080;">Tableau d'honneur</b>
                                    {chk_inscrit} Inscrit(e)<br>{chk_felicitations} Félicitations<br>{chk_encouragements} Encouragements<br>{chk_non_inscrit} Non Inscrit(e)
                                </div>
                                <div style="padding: 6px; text-align: center; line-height: 1.3;">
                                    <b style="text-decoration: underline; display: block; margin-bottom: 3px; color: #000080;">Assiduité</b>
                                    <br>
                                    <span style="color: red; font-weight: bold; font-size: 0.85rem;">R - A - S</span>
                                </div>
                            </div>

                            <div style="display: flex; justify-content: space-between; margin-top: 15px; font-size: 0.8rem;">
                                <div style="text-align: center; width: 40%;">
                                    <b>Le Proviseur</b><br><br><br><br>
                                    _________________________________
                                </div>
                                <div style="text-align: center; width: 40%;">
                                    <b>Appréciation des Parents</b><br><br><br><br>
                                    _________________________________
                                </div>
                            </div>

                            <div style="text-align: center; margin-top: 15px; font-size: 0.65rem; border-top: 1px solid #000080; padding-top: 3px; font-weight: bold; color: #000080;">
                                {adresse_ecole}<br>
                                {contacts_ecole} — Service de Vérification & Authentification
                            </div>
                        </div>
                    </body>
                    </html>
                    """
            components.html(bulletin_html, height=1140, scrolling=False)

        if portee == "Élève unique" and eleve_id_selectionne:
            eleve_s = (
                db.query(Eleve).filter(Eleve.id == eleve_id_selectionne).first()
            )
            if eleve_s:
                rendre_bulletin(eleve_s)
        elif portee == "Toute la classe":
            st.markdown("<br>", unsafe_allow_html=True)
            st.info(
                "💡 **Impression de classe entière** : Utilisez le bouton d'impression sur chaque bulletin ci-dessous."
            )
            for eleve_item in eleves:
                rendre_bulletin(eleve_item)

    finally:
        db.close()


# Alias de compatibilité
afficher_bulletin = afficher_bulletins
afficher_generation_bulletins = afficher_bulletins
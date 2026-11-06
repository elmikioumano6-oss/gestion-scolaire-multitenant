from datetime import datetime
from io import BytesIO
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from database.db_config import SessionLocal
from database.models import ActivityLog, CahierTexte, Classe, Enseignant, Matiere, Programme, School
import unicodedata

SYNONYMES_MATIERES = {
    "sciences physiques": "physique chimie",
    "physique chimie": "physique chimie",
    "svt": "science de la vie et de la terre",
    "science de la vie et de la terre": "science de la vie et de la terre",
    "eps": "eps",
    "education physique": "eps",
    "education physique et sportive": "eps",
    "economie familiale": "economie familiale et sociale",
    "economie familiale et sociale": "economie familiale et sociale",
    "economie familiale sociale": "economie familiale et sociale",
    "histoire geographie": "histoire geographie",
    "histoire-geographie": "histoire geographie",
    "education civique": "education civique et morale",
    "education civique et morale": "education civique et morale",
    "education civique morale": "education civique et morale",
    "conduite": "conduite",
}

BAREME_OFFICIEL_COLLEGE = {
    "francais": 140.0,
    "anglais": 140.0,
    "histoire geographie": 70.0,
    "mathematiques": 175.0,
    "physique chimie": 105.0,
    "science de la vie et de la terre": 105.0,
    "economie familiale et sociale": 35.0,
    "eps": 70.0,
    "education civique et morale": 35.0,
    "conduite": 0.0,
}

def normaliser_chaine(texte):
    if not texte or pd.isna(texte):
        return ""
    nfkd = unicodedata.normalize("NFKD", str(texte))
    sans_accent = "".join([c for c in nfkd if not unicodedata.combining(c)])
    nettoye = " ".join(sans_accent.lower().replace("-", " ").replace("_", " ").replace("è", "e").replace("é", " e").split())
    return SYNONYMES_MATIERES.get(nettoye, nettoye)

def parse_duree_seance(duree_c):
    if not duree_c:
        return 1.0
    chiffres = "".join([c for c in str(duree_c) if c.isdigit() or c == '.'])
    try:
        val = float(chiffres)
        return val if val > 0 else 1.0
    except ValueError:
        return 1.0


def afficher_supervision_progression():
    st.subheader("📚 Pilotage, Suivi & Avancement Global des Programmes")
    st.markdown(
        "Tableau de bord exécutif de la Direction des Études : analyse croisée "
        "des volumes prévisionnels issus des programmes uploadés, des heures réalisées issues du "
        "registre officiel et des alertes de retard par discipline."
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
            school_adresse = getattr(ecole_courante, "adresse", "QUARTIER AEROPORT NIAMEY-NIGER") if ecole_courante else "QUARTIER AEROPORT NIAMEY-NIGER"
        else:
            school_name = st.session_state.get("school_name", "Établissement")
            school_adresse = "QUARTIER AEROPORT NIAMEY-NIGER"
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

        ecole_active_id = school_id if school_id else target_school_id

        classes_query = db.query(Classe).filter(
            Classe.cycle == cycle_en_cours, Classe.school_id == ecole_active_id
        )
        if hasattr(Classe, "deleted_at"):
            classes_query = classes_query.filter(Classe.deleted_at.is_(None))
        classes_cycle = classes_query.all()

        if not classes_cycle:
            st.warning(
                f"⚠️ Aucune classe configurée pour le cycle **{cycle_en_cours}**."
            )
            return

        noms_classes = [
            c.libelle or getattr(c, "nom", f"Classe {c.id}") for c in classes_cycle
        ]
        classe_selectionnee = st.selectbox(
            "🔍 Filtrer le suivi par classe :",
            noms_classes,
            key="suivi_prog_classe_select",
        )

        classe_obj = next(
            (
                c
                for c in classes_cycle
                if (c.libelle or getattr(c, "nom", f"Classe {c.id}"))
                == classe_selectionnee
            ),
            None,
        )

        matieres_query = db.query(Matiere).filter(
            Matiere.classe_id == classe_obj.id if classe_obj else True,
            Matiere.school_id == ecole_active_id
        )
        if hasattr(Matiere, "deleted_at"):
            matieres_query = matieres_query.filter(Matiere.deleted_at.is_(None))
        matieres_brutes = matieres_query.all()

        if not matieres_brutes:
            matieres_query_cycle = db.query(Matiere).filter(
                Matiere.cycle == cycle_en_cours, Matiere.school_id == ecole_active_id
            )
            if hasattr(Matiere, "deleted_at"):
                matieres_query_cycle = matieres_query_cycle.filter(Matiere.deleted_at.is_(None))
            matieres_brutes = matieres_query_cycle.all()

        matieres_uniques_dict = {}
        for mat in matieres_brutes:
            nom_brut = mat.libelle if hasattr(mat, "libelle") and mat.libelle else getattr(mat, "nom", "Matière")
            norm_key = normaliser_chaine(nom_brut)
            if norm_key not in matieres_uniques_dict:
                matieres_uniques_dict[norm_key] = mat
        matieres_cycle = list(matieres_uniques_dict.values())

        st.markdown(
            f"### Synthèse des Programmes pour **{classe_selectionnee}** — **{school_name} ({cycle_en_cours})**"
        )

        if not matieres_cycle:
            st.warning(
                f"⚠️ Aucune matière enregistrée pour la classe **{classe_selectionnee}**."
            )
            return

        toutes_entrees = (
            db.query(CahierTexte)
            .filter(
                CahierTexte.school_id == ecole_active_id,
                CahierTexte.classe_id == classe_obj.id if classe_obj else True,
            )
            .all()
        )

        programmes_ecole = db.query(Programme).filter(Programme.school_id == ecole_active_id).all()
        tous_enseignants = db.query(Enseignant).filter(Enseignant.school_id == ecole_active_id).all()

        data_suivi = []
        total_prevu_globale = 0.0
        total_realise_globale = 0.0

        for mat in matieres_cycle:
            mat_lib = (
                mat.libelle
                if hasattr(mat, "libelle") and mat.libelle
                else getattr(mat, "nom", "Matière")
            )
            mat_norm = normaliser_chaine(mat_lib)

            enseignant_affecte = "Non assigné"
            for ens in tous_enseignants:
                mat_attr = str(getattr(ens, "matieres_attribuees", "") or getattr(ens, "matieres", "")).lower()
                cls_attr = str(getattr(ens, "classes_attribuees", "") or getattr(ens, "classes", "")).lower()
                
                if (mat_norm in normaliser_chaine(mat_attr) or mat_lib.lower() in mat_attr) and \
                   (classe_selectionnee.lower() in cls_attr or not cls_attr):
                    enseignant_affecte = f"{getattr(ens, 'nom', '')} {getattr(ens, 'prenom', '')}".strip()
                    break

            if enseignant_affecte == "Non assigné":
                seances_mat_check = [e for e in toutes_entrees if getattr(e, 'matiere_id', None) == mat.id]
                for s in seances_mat_check:
                    if hasattr(s, "enseignant_id") and s.enseignant_id:
                        ens_lie = db.query(Enseignant).filter(Enseignant.id == s.enseignant_id).first()
                        if ens_lie:
                            enseignant_affecte = f"{getattr(ens_lie, 'nom', '')} {getattr(ens_lie, 'prenom', '')}".strip()
                            break

            volume_prevu = 0.0
            coefficient_val = int(getattr(mat, "coefficient", 1) or 1)

            if cycle_en_cours.lower() in ["collège", "college"]:
                for attr_v in ["volume_horaire", "volume", "heures", "masse_horaire", "duree", "volume_hebdo"]:
                    val = getattr(mat, attr_v, None)
                    if val is not None:
                        try:
                            v_f = float(val)
                            if v_f > 0:
                                volume_prevu = v_f
                                break
                        except Exception:
                            pass
                
                if volume_prevu == 0.0:
                    for p in programmes_ecole:
                        p_nom = normaliser_chaine(getattr(p, 'nom_matiere', getattr(p, 'matiere', '')))
                        if p_nom == mat_norm and p.volume_horaire:
                            volume_prevu = float(p.volume_horaire)
                            break
                
                if volume_prevu == 0.0 and mat_norm in BAREME_OFFICIEL_COLLEGE:
                    volume_prevu = BAREME_OFFICIEL_COLLEGE[mat_norm]
            else:
                prog_obj = None
                classe_norm = normaliser_chaine(classe_selectionnee)
                for p in programmes_ecole:
                    p_nom = normaliser_chaine(getattr(p, 'nom_matiere', getattr(p, 'matiere', '')))
                    texte_ligne = normaliser_chaine(f"{getattr(p, 'classe', '')} {getattr(p, 'code_matiere', '')} {getattr(p, 'matiere', '')} {getattr(p, 'nom_matiere', '')}")
                    if p_nom == mat_norm and (classe_norm in texte_ligne):
                        prog_obj = p
                        break
                
                if not prog_obj:
                    for p in programmes_ecole:
                        p_nom = normaliser_chaine(getattr(p, 'nom_matiere', getattr(p, 'matiere', '')))
                        if p_nom == mat_norm:
                            prog_obj = p
                            break

                volume_prevu = float(prog_obj.volume_horaire) if prog_obj and prog_obj.volume_horaire else float(getattr(mat, "volume_horaire", 0) or 0)
                if prog_obj and prog_obj.coefficient:
                    coefficient_val = int(prog_obj.coefficient)

            seances_mat = [e for e in toutes_entrees if getattr(e, 'matiere_id', None) == mat.id or normaliser_chaine(getattr(e, 'matiere', getattr(e, 'discipline', ''))) == mat_norm]

            volume_realise = 0.0
            dernier_chapitre = "Aucun cours enregistré"
            
            for seance in seances_mat:
                duree_val = parse_duree_seance(getattr(seance, 'duree_seance', getattr(seance, 'duree', 1.0)))
                volume_realise += duree_val

            if seances_mat:
                dernier_cours = seances_mat[-1]
                contenu_cours = getattr(dernier_cours, "contenu", "") or ""
                dernier_chapitre = contenu_cours[:60] + "..." if len(contenu_cours) > 60 else (contenu_cours if contenu_cours else "N/D")

            total_prevu_globale += volume_prevu
            total_realise_globale += volume_realise

            progression_pct = round((volume_realise / volume_prevu) * 100, 1) if volume_prevu > 0 else 0.0
            if progression_pct > 100.0:
                progression_pct = 100.0

            if volume_prevu == 0.0:
                appreciation = "⚠️ Volume horaire non défini"
            elif progression_pct >= 75:
                appreciation = "🟢 Rythme excellent et conforme"
            elif progression_pct >= 40:
                appreciation = "🟡 Rythme satisfaisant"
            elif progression_pct > 0:
                appreciation = "🟠 Rythme insuffisant"
            else:
                appreciation = "🔴 En attente de première saisie"

            data_suivi.append({
                "Matière": mat_lib.title(),
                "Enseignant(e)": enseignant_affecte,
                "Heures Prévues": f"{volume_prevu:g} h",
                "Heures Réalisées": f"{volume_realise:g} h",
                "Progression (%)": f"{progression_pct}%",
                "Dernier Chapitre / Notions": dernier_chapitre,
                "Appréciation Inspection": appreciation,
            })

        taux_global = (total_realise_globale / total_prevu_globale * 100) if total_prevu_globale > 0 else 0.0

        st.markdown("#### 📊 Synthèse Globale de la Classe")
        col_k1, col_k2, col_k3 = st.columns(3)
        col_k1.metric("Volume Prévu Global", f"{total_prevu_globale:g} h")
        col_k2.metric("Volume Dispensé Global", f"{total_realise_globale:g} h")
        col_k3.metric("Taux d'Exécution Moyen", f"{taux_global:.1f} %")
        st.markdown("<br>", unsafe_allow_html=True)

        lignes_html = ""
        for i, row in enumerate(data_suivi, 1):
            lignes_html += f"<tr><td style='text-align: center;'>{i}</td><td><b>{row['Matière']}</b></td><td>{row['Enseignant(e)']}</td><td style='text-align: center;'>{row['Heures Prévues']}</td><td style='text-align: center;'>{row['Heures Réalisées']}</td><td style='text-align: center;'>{row['Progression (%)']}</td><td>{row['Dernier Chapitre / Notions']}</td><td>{row['Appréciation Inspection']}</td><td></td></tr>"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset='utf-8'>
            <style>
                @page {{ size: A4 landscape; margin: 10mm; }}
                body {{ font-family: Arial, sans-serif; color: #000; background: #FFF; }}
                table {{ width: 100%; border-collapse: collapse; font-size: 0.8rem; margin-top: 15px; }}
                th, td {{ border: 1px solid #000080; padding: 6px 8px; }}
                th {{ background-color: #800020; color: #FFFFFF; text-align: center; }}
            </style>
        </head>
        <body>
            <div style='text-align:center; margin-bottom:15px;'>
                <button onclick='window.print()' style='background:#000080; color:white; padding:10px 24px; font-weight:bold; border:none; border-radius:6px; cursor:pointer;'>🖨️ Imprimer le Rapport d'Avancement (A4 Paysage)</button>
            </div>
            <div style='width:277mm; margin:0 auto; background:#FFF; padding:12mm; border:1.5px solid #000080;'>
                <table>
                    <tr>
                        <td style='border:none; font-weight:bold; font-size: 0.9rem;'>{school_name}<br>{school_adresse}</td>
                        <td style='border:none; text-align:right; font-size: 0.9rem;'><b>RAPPORT D'AVANCEMENT DES PROGRAMMES</b><br>Classe : <b>{classe_selectionnee}</b> | Cycle : <b>{cycle_en_cours}</b><br>Date d'édition : <b>{datetime.today().strftime('%d/%m/%Y')}</b></td>
                    </tr>
                </table>
                <table>
                    <thead>
                        <tr>
                            <th>N°</th>
                            <th>Matière</th>
                            <th>Enseignant(e)</th>
                            <th>Heures Prévues</th>
                            <th>Heures Réalisées</th>
                            <th>Progression</th>
                            <th>Dernier Chapitre / Notions</th>
                            <th>Appréciation / Statut</th>
                            <th>Visa / Observations</th>
                        </tr>
                    </thead>
                    <tbody>
                        {lignes_html}
                    </tbody>
                    <tfoot>
                        <tr style='background:#000080; color:#FFF; font-weight:bold;'>
                            <td colspan='3' style='text-align:right;'>TOTAUX GLOBAUX / MOYENNE :</td>
                            <td style='text-align:center;'>{total_prevu_globale:g} h</td>
                            <td style='text-align:center;'>{total_realise_globale:g} h</td>
                            <td style='text-align:center;' colspan='4'>Taux d'exécution moyen : {taux_global:.1f} %</td>
                            <td></td>
                        </tr>
                    </tfoot>
                </table>
            </div>
        </body>
        </html>
        """

        components.html(html_content, height=520, scrolling=True)

        st.markdown("#### Détail par Discipline")
        df_suivi = pd.DataFrame(data_suivi)
        st.dataframe(df_suivi, use_container_width=True, column_config={
            "Enseignant(e)": st.column_config.TextColumn("Enseignant(e)", width="large"),
            "Dernier Chapitre / Notions": st.column_config.TextColumn("Dernier Chapitre / Notions", width="large")
        })

    finally:
        db.close()
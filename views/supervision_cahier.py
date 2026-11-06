from datetime import datetime
import unicodedata
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from database.db_config import SessionLocal
from database.models import AnneeScolaire, CahierTexte, Classe, Enseignant, Matiere, Programme, School

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
    "efs": "economie familiale et sociale",
    "histoire geographie": "histoire geographie",
    "histoire-geographie": "histoire geographie",
    "education civique et morale": "education civique et morale",
    "education civique": "education civique et morale",
}

BAREME_STANDARD = {
    "mathematiques": 175,
    "francais": 140,
    "anglais": 140,
    "physique chimie": 105,
    "science de la vie et de la terre": 105,
    "histoire geographie": 70,
    "eps": 70,
    "economie familiale et sociale": 35,
    "education civique et morale": 35,
    "conduite": 0
}

def normaliser_chaine(texte):
    if not texte or pd.isna(texte):
        return ""
    nfkd = unicodedata.normalize("NFKD", str(texte))
    sans_accent = "".join([c for c in nfkd if not unicodedata.combining(c)])
    return " ".join(sans_accent.lower().replace("-", " ").replace("_", " ").split())

def parse_duree_seance(duree_c):
    if not duree_c:
        return 1.0
    chiffres = "".join([c for c in str(duree_c) if c.isdigit() or c == '.'])
    try:
        val = float(chiffres)
        return val if val > 0 else 1.0
    except ValueError:
        return 1.0

def afficher_supervision_cahier():
    st.markdown("""
    <style>
        .audit-card {
            background: linear-gradient(135deg, #141e30 0%, #243b55 100%);
            border-radius: 12px;
            padding: 20px;
            color: white;
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.2);
            margin-bottom: 25px;
            display: flex;
            align-items: center;
            border-left: 5px solid #d4af37;
        }
        .audit-card h2 { margin: 0; color: #ffffff; font-weight: 600; font-size: 1.8rem; padding-bottom: 5px; }
        .audit-card p { margin: 0; opacity: 0.9; font-size: 1rem; color: #e2e8f0; }
        .filter-box {
            background-color: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 10px;
            padding: 15px 20px;
            margin-bottom: 20px;
        }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("## 📋 Contrôle d'Inspection Pédagogique & Registre Officiel")
    st.markdown("Portail officiel d'audit aux normes internationales (SIA) pour la direction, le censeur et les inspecteurs.")
    st.markdown("---")

    school_id = st.session_state.get("school_id")
    is_super_admin = st.session_state.get("is_super_admin", False)
    cycle_en_cours = st.session_state.get("cycle_actif", "Collège")

    if not school_id and not is_super_admin:
        st.warning("⚠️ Veuillez vous connecter pour accéder à cette section.")
        return

    db = SessionLocal()
    try:
        resolved_school_id = school_id if school_id else 1
        if is_super_admin and not school_id:
            ecole_defaut = db.query(School).first()
            if ecole_defaut:
                resolved_school_id = ecole_defaut.id

        ecole_courante = db.query(School).filter(School.id == resolved_school_id).first()
        school_name = ecole_courante.nom.upper() if ecole_courante else "COMPLEXE SCOLAIRE PRIVE RAHMAT-FH"
        school_devise = ecole_courante.devise if ecole_courante else "Excellence - Persévérance - Réussite"
        school_adresse = getattr(ecole_courante, "adresse", "QUARTIER AEROPORT NIAMEY-NIGER").upper() if ecole_courante else "QUARTIER AEROPORT NIAMEY-NIGER"

        annee_active = db.query(AnneeScolaire).filter(
            AnneeScolaire.school_id == resolved_school_id,
            AnneeScolaire.active == True,
        ).first()
        libelle_annee = annee_active.libelle if annee_active else "2026-2027"

        st.markdown(f"""
            <div class="audit-card">
                <div style="font-size: 3.5rem; margin-right: 25px;">🏛️</div>
                <div>
                    <h2>{school_name} — Cycle : {cycle_en_cours}</h2>
                    <p>Devise : <i>{school_devise}</i> | Année Scolaire : <b>{libelle_annee}</b> | {school_adresse}</p>
                </div>
            </div>
        """, unsafe_allow_html=True)

        classes_cycle = db.query(Classe).filter(Classe.school_id == resolved_school_id, Classe.cycle == cycle_en_cours).all()
        if not classes_cycle:
            st.warning(f"⚠️ Aucune classe enregistrée pour le cycle **{cycle_en_cours}**.")
            return

        dict_classes_id = {c.id: c for c in classes_cycle}

        st.markdown('<div class="filter-box">', unsafe_allow_html=True)
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            noms_classes = [c.libelle or getattr(c, "nom", f"Classe {c.id}") for c in classes_cycle]
            classe_suivie = st.selectbox("Sélectionner la classe à inspecter", noms_classes, key="sup_classe_select")
        with col_f2:
            periode_inspection = st.selectbox("Période d'évaluation / Semestre", ["Année complète", "Semestre 1", "Semestre 2"], key="sup_periode_select")
        st.markdown('</div>', unsafe_allow_html=True)

        classe_obj = next((c for c in classes_cycle if (c.libelle or getattr(c, "nom", f"Classe {c.id}")) == classe_suivie), None)
        if not classe_obj:
            st.warning("⚠️ Classe sélectionnée invalide.")
            return

        matieres_classe = db.query(Matiere).filter(Matiere.classe_id == classe_obj.id, Matiere.school_id == resolved_school_id).all()
        if not matieres_classe:
            matieres_classe = db.query(Matiere).filter(Matiere.cycle == cycle_en_cours, Matiere.school_id == resolved_school_id).all()

        all_programmes = db.query(Programme).filter(Programme.school_id == resolved_school_id).all()
        enseignants_db = db.query(Enseignant).filter(Enseignant.school_id == resolved_school_id).all()
        dict_enseignants = {e.id: e for e in enseignants_db}
        toutes_matieres_db = db.query(Matiere).filter(Matiere.school_id == resolved_school_id).all()
        dict_matieres_id = {m.id: m for m in toutes_matieres_db}

        if not matieres_classe:
            st.info(f"Aucune matière configurée pour la classe de **{classe_suivie}**.")
            return

        # Association officielle des enseignants par matière
        enseignant_par_mat = {}
        for mat in matieres_classe:
            nom_ens_officiel = "Non assigné"
            ens_id_mat = getattr(mat, "enseignant_id", None)
            if ens_id_mat and ens_id_mat in dict_enseignants:
                e_obj = dict_enseignants[ens_id_mat]
                nom_ens_officiel = f"{str(getattr(e_obj, 'nom', '')).strip().upper()} {str(getattr(e_obj, 'prenom', '')).strip().title()}".strip()
            enseignant_par_mat[mat.id] = nom_ens_officiel

        libelle_classe_norm = normaliser_chaine(classe_suivie)
        niveau_cible = ""
        for mot, lib_long in [("6", "6ème"), ("5", "5ème"), ("4", "4ème"), ("3", "3ème")]:
            if mot in libelle_classe_norm or mot + "e" in libelle_classe_norm:
                niveau_cible = lib_long
                break

        map_norm_matieres_classe = {}
        for mat in matieres_classe:
            m_lib = mat.libelle if hasattr(mat, "libelle") and mat.libelle else getattr(mat, "nom", "")
            norm_k = normaliser_chaine(m_lib)
            map_norm_matieres_classe[norm_k] = mat.id
            if norm_k in SYNONYMES_MATIERES:
                map_norm_matieres_classe[SYNONYMES_MATIERES[norm_k]] = mat.id

        heures_realisees_par_mat = {mat.id: 0.0 for mat in matieres_classe}
        entrees_par_mat = {mat.id: [] for mat in matieres_classe}

        cahier_entries = db.query(CahierTexte).filter(CahierTexte.school_id == resolved_school_id).all()

        for entry in cahier_entries:
            cls_entry = dict_classes_id.get(getattr(entry, "classe_id", None))
            match_cls = False
            if cls_entry and cls_entry.id == classe_obj.id:
                match_cls = True
            else:
                txt_e = normaliser_chaine(f"{getattr(entry, 'titre', '')} {getattr(entry, 'contenu', '')}")
                if libelle_classe_norm in txt_e:
                    match_cls = True

            if not match_cls:
                continue

            matched_mat_id = None
            mat_id_e = getattr(entry, "matiere_id", None)
            if mat_id_e in dict_matieres_id:
                m_obj = dict_matieres_id[mat_id_e]
                m_name = normaliser_chaine(getattr(m_obj, "libelle", "") or getattr(m_obj, "nom", ""))
                if m_name in map_norm_matieres_classe:
                    matched_mat_id = map_norm_matieres_classe[m_name]
                elif m_name in SYNONYMES_MATIERES and SYNONYMES_MATIERES[m_name] in map_norm_matieres_classe:
                    matched_mat_id = map_norm_matieres_classe[SYNONYMES_MATIERES[m_name]]

            if not matched_mat_id:
                txt_e = normaliser_chaine(f"{getattr(entry, 'titre', '')} {getattr(entry, 'contenu', '')}")
                for norm_k, m_id in map_norm_matieres_classe.items():
                    if norm_k in txt_e:
                        matched_mat_id = m_id
                        break

            if not matched_mat_id or matched_mat_id not in heures_realisees_par_mat:
                continue

            if enseignant_par_mat[matched_mat_id] == "Non assigné":
                matched_ens_id = getattr(entry, "enseignant_id", None)
                if matched_ens_id and matched_ens_id in dict_enseignants:
                    ens_obj = dict_enseignants[matched_ens_id]
                    enseignant_par_mat[matched_mat_id] = f"{str(getattr(ens_obj, 'nom', '')).strip().upper()} {str(getattr(ens_obj, 'prenom', '')).strip().title()}".strip()

            duree_val = parse_duree_seance(getattr(entry, 'duree_seance', getattr(entry, 'duree', 1.0)))
            heures_realisees_par_mat[matched_mat_id] += duree_val
            entrees_par_mat[matched_mat_id].append(entry)

        data_suivi = []
        total_heures_prevues_globale = 0.0
        total_heures_realisees_globale = 0.0

        for mat in matieres_classe:
            mat_lib = mat.libelle if hasattr(mat, "libelle") and mat.libelle else getattr(mat, "nom", "Matière")
            norm_key = normaliser_chaine(mat_lib)
            canonical_key = SYNONYMES_MATIERES.get(norm_key, norm_key)

            heures_prevues = 0.0
            if hasattr(mat, "volume_horaire") and mat.volume_horaire and float(mat.volume_horaire) > 0:
                heures_prevues = float(mat.volume_horaire)
            else:
                prog_obj = None
                for p in all_programmes:
                    p_classe = str(getattr(p, 'classe', ''))
                    p_code = str(getattr(p, 'code_matiere', ''))
                    p_mat = str(getattr(p, 'matiere', ''))
                    p_nom_mat = str(getattr(p, 'nom_matiere', ''))
                    texte_ligne = normaliser_chaine(p_classe + " " + p_code + " " + p_mat + " " + p_nom_mat)
                    
                    p_nom = normaliser_chaine(p_nom_mat or p_mat)
                    p_norm_canon = SYNONYMES_MATIERES.get(p_nom, p_nom)
                    
                    if (p_norm_canon == canonical_key or p_nom == norm_key) and (libelle_classe_norm in texte_ligne or (niveau_cible and niveau_cible.lower() in texte_ligne)):
                        prog_obj = p
                        break
                
                if prog_obj and prog_obj.volume_horaire and float(prog_obj.volume_horaire) > 0:
                    heures_prevues = float(prog_obj.volume_horaire)
                elif canonical_key in BAREME_STANDARD:
                    heures_prevues = float(BAREME_STANDARD[canonical_key])

            if periode_inspection in ["Semestre 1", "Semestre 2"]:
                heures_prevues_periode = round(heures_prevues / 2.0, 1)
            else:
                heures_prevues_periode = heures_prevues

            heures_realisees = heures_realisees_par_mat[mat.id]
            entrees_mat = entrees_par_mat[mat.id]
            enseignant_ref = enseignant_par_mat[mat.id]

            total_heures_prevues_globale += heures_prevues_periode
            total_heures_realisees_globale += heures_realisees

            progression_pct = round((heures_realisees / heures_prevues_periode) * 100, 1) if heures_prevues_periode > 0 else 0.0
            if progression_pct > 100.0:
                progression_pct = 100.0

            if entrees_mat:
                contenu_cours = getattr(entrees_mat[-1], "contenu", "") or ""
                dernier_chapitre = contenu_cours[:60] + "..." if len(contenu_cours) > 60 else (contenu_cours or "N/D")
            else:
                dernier_chapitre = "Aucun cours enregistré"

            if heures_prevues_periode == 0.0:
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
                "Enseignant(e)": enseignant_ref,
                "Heures Prévues": f"{heures_prevues_periode:g} h",
                "Heures Réalisées": f"{heures_realisees:g} h",
                "Progression (%)": f"{progression_pct}%",
                "Dernier Chapitre / Notions": dernier_chapitre,
                "Appréciation Inspection": appreciation,
            })
        
        taux_global_classe = (total_heures_realisees_globale / total_heures_prevues_globale * 100) if total_heures_prevues_globale > 0 else 0.0
        
        st.markdown("#### 📊 Synthèse Globale de la Classe")
        col_k1, col_k2, col_k3 = st.columns(3)
        col_k1.metric("Volume Prévu (Période)", f"{total_heures_prevues_globale:g} h")
        col_k2.metric("Volume Dispensé", f"{total_heures_realisees_globale:g} h")
        col_k3.metric("Taux d'Exécution Moyen", f"{taux_global_classe:.1f} %")
        st.markdown("<br>", unsafe_allow_html=True)

        lignes_html = ""
        for i, row in enumerate(data_suivi, 1):
            lignes_html += (
                f"<tr>"
                f"<td style='text-align: center;'>{i}</td>"
                f"<td><b>{row['Matière']}</b></td>"
                f"<td>{row['Enseignant(e)']}</td>"
                f"<td style='text-align: center;'>{row['Heures Prévues']}</td>"
                f"<td style='text-align: center;'>{row['Heures Réalisées']}</td>"
                f"<td style='text-align: center;'>{row['Progression (%)']}</td>"
                f"<td>{row['Dernier Chapitre / Notions']}</td>"
                f"<td>{row['Appréciation Inspection']}</td>"
                f"<td></td>"
                f"</tr>"
            )

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset='utf-8'>
            <style>
                @page {{ 
                    size: A4 landscape; 
                    margin: 5mm; 
                }}
                html, body {{
                    margin: 0;
                    padding: 0;
                    background: #FFF;
                    font-family: Arial, sans-serif;
                    color: #000;
                }}
                body {{ 
                    box-sizing: border-box;
                }}
                table {{ 
                    width: 100%; 
                    border-collapse: collapse; 
                    font-size: 0.75rem; 
                    margin-top: 10px; 
                }}
                th, td {{ 
                    border: 1px solid #000080; 
                    padding: 4px 6px; 
                }}
                th {{ 
                    background-color: #800020; 
                    color: #FFFFFF; 
                    text-align: center; 
                }}
                @media print {{
                    button {{ display: none !important; }}
                    body {{ -webkit-print-color-adjust: exact; }}
                }}
            </style>
        </head>
        <body>
            <div style='text-align:center; margin-bottom:10px;'>
                <button onclick='window.print()' style='background:#000080; color:white; padding:8px 20px; font-weight:bold; border:none; border-radius:6px; cursor:pointer;'>🖨️ Imprimer le Rapport Pédagogique (A4 Paysage)</button>
            </div>
            <div style='width:277mm; margin:0 auto; background:#FFF; padding:8mm; border:1.5px solid #000080;'>
                <table>
                    <tr>
                        <td style='border:none; font-weight:bold; font-size: 0.85rem;'>{school_name}<br>{school_adresse}</td>
                        <td style='border:none; text-align:right; font-size: 0.85rem;'><b>RAPPORT D'INSPECTION PÉDAGOGIQUE</b><br>Classe : <b>{classe_suivie}</b> | Période : <b>{periode_inspection}</b><br>Date d'édition : <b>{datetime.today().strftime('%d/%m/%Y')}</b></td>
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
                            <th>Appréciation Inspection</th>
                            <th>Visa / Observations</th>
                        </tr>
                    </thead>
                    <tbody>
                        {lignes_html}
                    </tbody>
                    <tfoot>
                        <tr style='background:#000080; color:#FFF; font-weight:bold;'>
                            <td colspan='3' style='text-align:right;'>TOTAUX GLOBAUX / MOYENNE :</td>
                            <td style='text-align:center;'>{total_heures_prevues_globale:g} h</td>
                            <td style='text-align:center;'>{total_heures_realisees_globale:g} h</td>
                            <td style='text-align:center;' colspan='4'>Taux d'exécution moyen : {taux_global_classe:.1f} %</td>
                            <td></td>
                        </tr>
                    </tfoot>
                </table>
            </div>
        </body>
        </html>
        """
        
        components.html(html_content, height=480, scrolling=True)

        st.markdown("#### Détail par Discipline")
        df_suivi = pd.DataFrame(data_suivi)
        st.dataframe(df_suivi, use_container_width=True, column_config={
            "Enseignant(e)": st.column_config.TextColumn("Enseignant(e)", width="large"),
            "Dernier Chapitre / Notions": st.column_config.TextColumn("Dernier Chapitre / Notions", width="large")
        })

    except Exception as e:
        st.error(f"Une erreur technique est survenue : {e}")
    finally:
        db.close()
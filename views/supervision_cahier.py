from datetime import datetime
from io import BytesIO
import unicodedata
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from database.db_config import SessionLocal
from database.models import (
    ActivityLog,
    AnneeScolaire,
    CahierTexte,
    Classe,
    Matiere,
    Programme,
    School,
)

SYNONYMES_MATIERES = {
    "sciences physiques": "physique chimie",
    "physique chimie": "physique chimie",
    "svt": "science de la vie et de la terre",
    "science de la vie et de la terre": "science de la vie et de la terre",
    "eps": "education physique et sportive",
    "education physique et sportive": "education physique et sportive",
    "economie familiale": "economie familiale et sociale",
    "economie familiale et sociale": "economie familiale et sociale",
    "histoire geographie": "histoire geographie",
    "histoire-geographie": "histoire geographie",
}


def normaliser_chaine(texte):
    if not texte or pd.isna(texte):
        return ""
    nfkd = unicodedata.normalize("NFKD", str(texte))
    sans_accent = "".join([c for c in nfkd if not unicodedata.combining(c)])
    nettoye = " ".join(
        sans_accent.lower().replace("-", " ").replace("_", " ").split()
    )
    return SYNONYMES_MATIERES.get(nettoye, nettoye)


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
        @media print {
            body { background-color: white !important; color: black !important; }
            .stButton, .stSelectbox, sidebar, header, footer, [data-testid="stSidebar"], .filter-box { display: none !important; }
            .printable-area { width: 100% !important; padding: 10px !important; margin: 0 !important; }
            .audit-card { background: white !important; color: black !important; border: 2px solid black; border-left: none; box-shadow: none; }
            .audit-card h2, .audit-card p { color: black !important; }
        }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("## 📋 Contrôle d'Inspection Pédagogique & Registre Officiel")
    st.markdown("Portail officiel d'audit aux normes internationales (SIA) pour la direction, le censeur et les inspecteurs.")
    st.markdown("---")

    school_id = st.session_state.get("school_id")
    is_super_admin = st.session_state.get("is_super_admin", False)
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

        resolved_school_id = school_id if school_id else target_school_id

        ecole_courante = db.query(School).filter(School.id == resolved_school_id).first()
        school_name = ecole_courante.nom if ecole_courante else st.session_state.get("school_name", "Établissement")
        school_devise = ecole_courante.devise if ecole_courante else "Excellence - Persévérance - Réussite"
        school_adresse = ecole_courante.adresse if ecole_courante and ecole_courante.adresse else "Niamey - Niger"

        annee_active = db.query(AnneeScolaire).filter(
            AnneeScolaire.school_id == resolved_school_id,
            AnneeScolaire.active == True,
        ).first()
        libelle_annee = annee_active.libelle if annee_active else "2026-2027"

        st.markdown('<div class="printable-area">', unsafe_allow_html=True)
        
        st.markdown(f"""
            <div class="audit-card">
                <div style="font-size: 3.5rem; margin-right: 25px;">🏛️</div>
                <div>
                    <h2>{school_name} — Cycle : {cycle_en_cours}</h2>
                    <p>Devise : <i>{school_devise}</i> | Année Scolaire : <b>{libelle_annee}</b> | {school_adresse}</p>
                </div>
            </div>
        """, unsafe_allow_html=True)

        classes_cycle = db.query(Classe).filter(
            Classe.school_id == resolved_school_id,
        ).all()

        if not classes_cycle:
            st.warning(f"⚠️ Aucune classe enregistrée pour cet établissement.")
            st.markdown("</div>", unsafe_allow_html=True)
            return

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
            st.markdown("</div>", unsafe_allow_html=True)
            return

        matieres_query = db.query(Matiere).filter(
            Matiere.classe_id == classe_obj.id,
            Matiere.school_id == resolved_school_id,
        )
        if hasattr(Matiere, "deleted_at"):
            matieres_query = matieres_query.filter(Matiere.deleted_at.is_(None))
        matieres_classe = matieres_query.all()

        all_programmes = db.query(Programme).filter(Programme.school_id == resolved_school_id).all()

        if not matieres_classe:
            st.info(f"Aucune matière configurée pour la classe de **{classe_suivie}**.")
            st.markdown("</div>", unsafe_allow_html=True)
            return

        libelle_classe_norm = normaliser_chaine(classe_suivie)
        niveau_cible = ""
        for mot, lib_long in [("6", "6ème"), ("5", "5ème"), ("4", "4ème"), ("3", "3ème")]:
            if mot in libelle_classe_norm or mot + "e" in libelle_classe_norm or mot + "è" in libelle_classe_norm:
                niveau_cible = lib_long
                break

        data_suivi = []
        is_college = cycle_en_cours.lower() in ["collège", "college"]
        
        total_heures_prevues_globale = 0.0
        total_heures_realisees_globale = 0.0

        # Récupération de TOUTES les entrées du cahier de texte de l'établissement
        toutes_entrees_ecole = db.query(CahierTexte).filter(
            CahierTexte.school_id == resolved_school_id,
        ).all()

        for mat in matieres_classe:
            mat_lib = mat.libelle if hasattr(mat, "libelle") and mat.libelle else getattr(mat, "nom", "Matière")
            norm_key = normaliser_chaine(mat_lib)

            heures_prevues = 0.0
            if not is_college:
                prog_obj = None
                for p in all_programmes:
                    p_nom = normaliser_chaine(getattr(p, 'nom_matiere', getattr(p, 'matiere', '')))
                    texte_ligne = normaliser_chaine(f"{getattr(p, 'classe', '')} {getattr(p, 'code_matiere', '')} {getattr(p, 'matiere', '')} {getattr(p, 'nom_matiere', '')}")
                    if p_nom == norm_key and (libelle_classe_norm in texte_ligne):
                        prog_obj = p
                        break
                if not prog_obj:
                    for p in all_programmes:
                        p_nom = normaliser_chaine(getattr(p, 'nom_matiere', getattr(p, 'matiere', '')))
                        if p_nom == norm_key:
                            prog_obj = p
                            break
                heures_prevues = float(prog_obj.volume_horaire) if prog_obj and prog_obj.volume_horaire else float(getattr(mat, "volume_horaire", 0) or 0)
            else:
                prog_classe = next(
                    (p for p in all_programmes if normaliser_chaine(getattr(p, 'nom_matiere', '')) == norm_key and (not niveau_cible or normaliser_chaine(niveau_cible) in normaliser_chaine(getattr(p, 'code_matiere', '')))),
                    None
                )
                if prog_classe and prog_classe.volume_horaire and prog_classe.volume_horaire > 0:
                    heures_prevues = prog_classe.volume_horaire
                else:
                    BAREME_COLLEGE = {
                        "6ème": {"francais": 205, "anglais": 140, "histoire geographie": 70, "mathematiques": 240, "physique chimie": 35, "science de la vie et de la terre": 70, "economie familiale et sociale": 35, "education physique et sportive": 70, "education civique": 35},
                        "5ème": {"francais": 140, "anglais": 140, "histoire geographie": 70, "mathematiques": 175, "physique chimie": 35, "science de la vie et de la terre": 70, "economie familiale et sociale": 35, "education physique et sportive": 70, "education civique": 35},
                        "4ème": {"francais": 140, "anglais": 140, "histoire geographie": 70, "mathematiques": 175, "physique chimie": 105, "science de la vie et de la terre": 70, "economie familiale et sociale": 35, "education physique et sportive": 70, "education civique": 35},
                        "3ème": {"francais": 140, "anglais": 140, "histoire geographie": 70, "mathematiques": 175, "physique chimie": 105, "science de la vie et de la terre": 105, "economie familiale et sociale": 35, "education physique et sportive": 70, "education civique": 35},
                    }
                    if niveau_cible in BAREME_COLLEGE and norm_key in BAREME_COLLEGE[niveau_cible]:
                        heures_prevues = float(BAREME_COLLEGE[niveau_cible][norm_key])
                    elif mat.volume_horaire and mat.volume_horaire > 0:
                        heures_prevues = mat.volume_horaire
                    else:
                        heures_prevues = 0.0

            if periode_inspection in ["Semestre 1", "Semestre 2"]:
                heures_prevues_periode = round(heures_prevues / 2.0, 1)
            else:
                heures_prevues_periode = heures_prevues

            # CORRECTION SANS ERREUR D'ATTRIBUT : Utilisation sécurisée de l'auteur et des liaisons
            entrees_cahier = []
            for e in toutes_entrees_ecole:
                e_classe_id = getattr(e, 'classe_id', None)
                appartient_classe = (e_classe_id == classe_obj.id)
                if not appartient_classe and e_classe_id:
                    cls_entree = db.query(Classe).filter(Classe.id == e_classe_id).first()
                    if cls_entree and normaliser_chaine(cls_entree.libelle) == libelle_classe_norm:
                        appartient_classe = True

                if appartient_classe:
                    e_mat_id = getattr(e, 'matiere_id', None)
                    matiere_entree = db.query(Matiere).filter(Matiere.id == e_mat_id).first() if e_mat_id else None
                    nom_matiere_entree = normaliser_chaine(getattr(matiere_entree, 'libelle', None) or getattr(matiere_entree, 'nom', '')) if matiere_entree else ""
                    texte_entree = normaliser_chaine(f"{getattr(e, 'titre', '')} {getattr(e, 'contenu', '')}")

                    if (e_mat_id == mat.id) or (nom_matiere_entree == norm_key) or (norm_key in texte_entree) or (e_mat_id is None):
                        entrees_cahier.append(e)

            heures_realisees = 0.0
            for e in entrees_cahier:
                duree_val = float(getattr(e, 'duree', 0.0) or 0.0)
                if duree_val > 0:
                    heures_realisees += duree_val
                else:
                    d_str = str(getattr(e, "duree_seance", "1 heure"))
                    try:
                        chiffre = float("".join(filter(str.isdigit, d_str)) or 1)
                        heures_realisees += chiffre
                    except Exception:
                        heures_realisees += 1.0

            total_heures_prevues_globale += heures_prevues_periode
            total_heures_realisees_globale += heures_realisees

            progression_pct = round((heures_realisees / heures_prevues_periode) * 100, 1) if heures_prevues_periode > 0 else 0.0
            if progression_pct > 100.0:
                progression_pct = 100.0

            if entrees_cahier:
                dernier_cours = entrees_cahier[-1]
                contenu_cours = getattr(dernier_cours, "contenu", "") or ""
                dernier_chapitre = contenu_cours[:60] + "..." if len(contenu_cours) > 60 else (contenu_cours if contenu_cours else "N/D")
                enseignant_ref = getattr(dernier_cours, "auteur_saisie", "Corps professoral") or "Corps professoral"
            else:
                dernier_chapitre = "Aucun cours enregistré"
                enseignant_ref = "Non assigné"

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
                "Heures Prévues": f"{heures_prevues_periode}h",
                "Heures Réalisées": f"{heures_realisees}h",
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

        col_btn1, col_btn2 = st.columns([1, 1])
        with col_btn1:
            components.html(
                """
                <div style="display: flex; align-items: center; height: 38px;">
                    <button onclick="parent.window.print()" style="background-color: #2b5876; color: white; border: none; padding: 0.5rem 1.2rem; font-size: 0.9rem; font-weight: 600; border-radius: 6px; cursor: pointer; font-family: sans-serif; white-space: nowrap; width: 100%;">🖨️ Imprimer le Rapport Pédagogique</button>
                </div>
                """,
                height=45,
            )
        with col_btn2:
            df_suivi = pd.DataFrame(data_suivi)
            st.download_button(
                label="📥 Exporter au format Excel (CSV)",
                data=df_suivi.to_csv(index=False).encode("utf-8"),
                file_name=f"rapport_inspection_{classe_suivie}_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )

        st.markdown("#### Détail par Discipline")
        st.dataframe(df_suivi, use_container_width=True)

        st.markdown("</div>", unsafe_allow_html=True)
    finally:
        db.close()

afficher_supervision_cahier = afficher_supervision_cahier
from datetime import datetime
from io import BytesIO
import pandas as pd
import streamlit as st
from database.db_config import SessionLocal
from database.models import ActivityLog, CahierTexte, Classe, Matiere, Programme, School
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

# Grille de secours officielle MEN pour les volumes horaires du collège par matière normalisée
BAREME_OFFICIEL_COLLEGE = {
    "francis": 140.0,
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
        else:
            school_name = st.session_state.get("school_name", "Établissement")
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

        # 1. Sélection de la classe pour un suivi précis par niveau
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

        # --- RÉCUPÉRATION STRICTE DES MATIÈRES DE LA CLASSE SÉLECTIONNÉE ---
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

        data_suivi = []
        for mat in matieres_cycle:
            mat_lib = (
                mat.libelle
                if hasattr(mat, "libelle") and mat.libelle
                else getattr(mat, "nom", "Matière")
            )
            mat_norm = normaliser_chaine(mat_lib)

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
                
                # Secours ultime par barème officiel si toujours à 0
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

            # Filtrage des séances pour cette matière spécifique
            seances_mat = [e for e in toutes_entrees if getattr(e, 'matiere_id', None) == mat.id or normaliser_chaine(getattr(e, 'matiere', getattr(e, 'discipline', ''))) == mat_norm]

            volume_realise = 0.0
            for seance in seances_mat:
                duree_val = float(getattr(seance, 'duree', 0.0) or 0.0)
                if duree_val > 0:
                    volume_realise += duree_val
                else:
                    d_str = str(getattr(seance, "duree_seance", "1 heure"))
                    try:
                        chiffre = float("".join(filter(str.isdigit, d_str)) or 1)
                        volume_realise += chiffre
                    except Exception:
                        volume_realise += 1.0

            taux = (
                min(100, int((volume_realise / volume_prevu) * 100))
                if volume_prevu > 0
                else 0
            )

            if volume_prevu == 0:
                remarques = "⚪ Non configuré"
            elif taux < 20:
                remarques = "🔴 En retard critique"
            elif taux < 40:
                remarques = "🟠 En léger retard"
            elif taux <= 80:
                remarques = "🟢 Rythme conforme"
            else:
                remarques = "🔵 Programme bien avancé"

            data_suivi.append({
                "Discipline / Matière": mat_lib.title(),
                "Coefficient": coefficient_val,
                "Volume Prévu": f"{volume_prevu:g}h",
                "Volume Réalisé": f"{volume_realise:g}h",
                "Taux d'Avancement": f"{taux}%",
                "Analyse & Remarque": remarques,
            })

        df_suivi = pd.DataFrame(data_suivi)
        st.dataframe(df_suivi, use_container_width=True)

        def to_excel_buffer(df):
            output = BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="SuiviProgrammes")
            return output.getvalue()

        excel_data = to_excel_buffer(df_suivi)
        st.download_button(
            label="📥 Télécharger le rapport de suivi des programmes (.xlsx)",
            data=excel_data,
            file_name=(
                f"Suivi_Programmes_{classe_selectionnee}_{school_name}.xlsx"
            ),
            mime=(
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ),
        )

        db.add(
            ActivityLog(
                school_id=ecole_active_id,
                timestamp=datetime.utcnow(),
                username=st.session_state.get("username", "admin"),
                action=(
                    f"Consultation du suivi global des programmes"
                    f" ({classe_selectionnee}) - {school_name}"
                ),
                module="Suivi des Programmes",
                statut="Succès",
            )
        )
        db.commit()

    finally:
        db.close()

# Alias de compatibilité
afficher_suivi_programmes = afficher_supervision_progression
afficher_suivi_des_programmes = afficher_supervision_progression
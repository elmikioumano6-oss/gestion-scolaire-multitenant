from datetime import datetime
from io import BytesIO
import pandas as pd
import streamlit as st
from database.db_config import SessionLocal
from database.models import ActivityLog, CahierTexte, Classe, Matiere, School
from database.queries import get_classes_cached, get_matieres_cached
import unicodedata

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
    nettoye = " ".join(sans_accent.lower().replace("-", " ").replace("_", " ").split())
    return SYNONYMES_MATIERES.get(nettoye, nettoye)


def afficher_supervision_progression():
    st.subheader("📚 Pilotage, Suivi & Avancement Global des Programmes")
    st.markdown(
        "Tableau de bord exécutif de la Direction des Études : analyse croisée "
        "des volumes prévisionnels par niveau, des heures réalisées issues du "
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
            "🔍 Filtrer le suivi par classe (pour un volume par niveau exact) :",
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

        # Détermination du niveau
        nom_cl_lower = str(classe_selectionnee).lower()
        niveau_detecte = "3ème"
        if "6" in nom_cl_lower:
            niveau_detecte = "6ème"
        elif "5" in nom_cl_lower:
            niveau_detecte = "5ème"
        elif "4" in nom_cl_lower:
            niveau_detecte = "4ème"
        elif "3" in nom_cl_lower:
            niveau_detecte = "3ème"

        # Barème officiel strict par niveau pour le collège
        BAREME_COLLEGE = {
            "6ème": {
                "francais": 205,
                "anglais": 140,
                "histoire geographie": 70,
                "mathematiques": 240,
                "physique chimie": 35,
                "science de la vie et de la terre": 70,
                "economie familiale et sociale": 35,
                "education physique et sportive": 70,
                "education civique": 35,
            },
            "5ème": {
                "francais": 140,
                "anglais": 140,
                "histoire geographie": 70,
                "mathematiques": 175,
                "physique chimie": 35,
                "science de la vie et de la terre": 70,
                "economie familiale et sociale": 35,
                "education physique et sportive": 70,
                "education civique": 35,
            },
            "4ème": {
                "francais": 140,
                "anglais": 140,
                "histoire geographie": 70,
                "mathematiques": 175,
                "physique chimie": 105,
                "science de la vie et de la terre": 70,
                "economie familiale et sociale": 35,
                "education physique et sportive": 70,
                "education civique": 35,
            },
            "3ème": {
                "francais": 140,
                "anglais": 140,
                "histoire geographie": 70,
                "mathematiques": 175,
                "physique chimie": 105,
                "science de la vie et de la terre": 105,
                "economie familiale et sociale": 35,
                "education physique et sportive": 70,
                "education civique": 35,
            },
        }

        # --- RÉCUPÉRATION STRICTE DES MATIÈRES DE LA CLASSE SÉLECTIONNÉE ---
        matieres_query = db.query(Matiere).filter(
            Matiere.classe_id == classe_obj.id if classe_obj else True,
            Matiere.school_id == ecole_active_id
        )
        if hasattr(Matiere, "deleted_at"):
            matieres_query = matieres_query.filter(Matiere.deleted_at.is_(None))
        matieres_brutes = matieres_query.all()

        # Si aucune matière n'est trouvée par classe_id direct, on élargit au cycle avec déduplication
        if not matieres_brutes:
            matieres_query_cycle = db.query(Matiere).filter(
                Matiere.cycle == cycle_en_cours, Matiere.school_id == ecole_active_id
            )
            if hasattr(Matiere, "deleted_at"):
                matieres_query_cycle = matieres_query_cycle.filter(Matiere.deleted_at.is_(None))
            matieres_brutes = matieres_query_cycle.all()

        # Déduplication stricte par nom normalisé pour éliminer les doublons
        matieres_uniques_dict = {}
        for mat in matieres_brutes:
            nom_brut = mat.libelle if hasattr(mat, "libelle") and mat.libelle else getattr(mat, "nom", "Matière")
            norm_key = normaliser_chaine(nom_brut)
            if norm_key not in matieres_uniques_dict:
                matieres_uniques_dict[norm_key] = mat
        matieres_cycle = list(matieres_uniques_dict.values())

        st.markdown(
            f"### Synthèse des Programmes pour **{classe_selectionnee} ({niveau_detecte})** — **{school_name}**"
        )

        if not matieres_cycle:
            st.warning(
                f"⚠️ Aucune matière enregistrée pour la classe **{classe_selectionnee}**."
            )
            return

        # Récupération des entrées du cahier de texte pour la classe sélectionnée
        toutes_entrees = (
            db.query(CahierTexte)
            .filter(
                CahierTexte.school_id == ecole_active_id,
                CahierTexte.classe_id == classe_obj.id if classe_obj else True,
            )
            .all()
        )

        data_suivi = []
        for mat in matieres_cycle:
            mat_lib = (
                mat.libelle
                if hasattr(mat, "libelle") and mat.libelle
                else getattr(mat, "nom", "Matière")
            )

            # Filtrage des séances pour cette matière spécifique
            seances_mat = [e for e in toutes_entrees if getattr(e, 'matiere_id', None) == mat.id or normaliser_chaine(getattr(e, 'matiere', getattr(e, 'discipline', ''))) == normaliser_chaine(mat_lib)]

            # Calcul cumulé du volume horaire réalisé
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

            # Normalisation du nom de la matière pour le barème
            mat_norm = normaliser_chaine(mat_lib)

            # Volume horaire prévu : strict selon le cycle (Collège vs Lycée)
            volume_prevu = 0.0
            is_college = cycle_en_cours.lower() in ["collège", "college"]

            if is_college:
                if (
                    niveau_detecte in BAREME_COLLEGE
                    and mat_norm in BAREME_COLLEGE[niveau_detecte]
                ):
                    volume_prevu = float(BAREME_COLLEGE[niveau_detecte][mat_norm])
                elif hasattr(mat, "volume_horaire") and mat.volume_horaire:
                    volume_prevu = float(mat.volume_horaire)
                else:
                    volume_prevu = 45.0
            else:
                if hasattr(mat, "volume_horaire") and mat.volume_horaire:
                    volume_prevu = float(mat.volume_horaire)
                else:
                    volume_prevu = 0.0

            # Calcul du taux de couverture
            taux = (
                min(100, int((volume_realise / volume_prevu) * 100))
                if volume_prevu > 0
                else 0
            )

            # Analyse de la progression
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
                "Coefficient": int(getattr(mat, "coefficient", 1) or 1),
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
from datetime import datetime
import io
import unicodedata
from database.db_config import SessionLocal
from database.models import ActivityLog, Classe, Matiere, Programme, School
import pandas as pd
import streamlit as st

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


def afficher_upload_programmes():
    st.subheader("📥 Import des Programmes & Coefficients par Classe")
    st.markdown(
        "Importez vos programmes académiques par classe pour gérer finement"
        " les volumes horaires selon les niveaux."
    )
    st.markdown("---")

    school_id = st.session_state.get("school_id")
    is_super_admin = st.session_state.get("is_super_admin", False)

    db = SessionLocal()
    try:
        target_school_id = school_id
        if is_super_admin and not target_school_id:
            ecole_defaut = db.query(School).first()
            target_school_id = ecole_defaut.id if ecole_defaut else 1

        resolved_school_id = school_id if school_id else target_school_id
        ecole_courante = (
            db.query(School).filter(School.id == resolved_school_id).first()
        )
        school_name = (
            ecole_courante.nom
            if ecole_courante
            else st.session_state.get("school_name", "Établissement")
        )
    finally:
        db.close()

    cycle_en_cours = st.session_state.get("cycle_actif", "Collège")

    if not school_id and not is_super_admin:
        st.warning("⚠️ Veuillez vous connecter pour accéder à cette section.")
        return

    st.markdown(
        f"### Import de données — **{school_name} ({cycle_en_cours})**"
    )

    uploaded_file = st.file_uploader(
        "Sélectionnez le fichier rempli (.xlsx ou .csv)", type=["xlsx", "csv"]
    )

    if uploaded_file is not None:
        try:
            df_import = (
                pd.read_csv(uploaded_file)
                if uploaded_file.name.endswith(".csv")
                else pd.read_excel(uploaded_file)
            )
            st.success("✅ Fichier chargé avec succès ! Aperçu des données :")
            st.dataframe(df_import, use_container_width=True)

            if st.button("Enregistrer les données importées", type="primary"):
                db = SessionLocal()
                try:
                    count_added = 0
                    count_updated = 0

                    for _, row in df_import.iterrows():
                        nom_mat = str(row.get("Matière", "")).strip()
                        nom_classe = str(row.get("Classe", "")).strip()
                        coef = float(row.get("Coefficient", 1) or 1)
                        vol = float(row.get("Volume Horaire Prévu", 45) or 45)

                        if not nom_mat or nom_mat == "nan" or not nom_classe or nom_classe == "nan":
                            continue

                        norm_mat = normaliser_chaine(nom_mat)
                        norm_classe = normaliser_chaine(nom_classe)

                        # Recherche ou création de la classe spécifique
                        classe_obj = db.query(Classe).filter(
                            Classe.school_id == resolved_school_id,
                            Classe.cycle == cycle_en_cours,
                        ).all()
                        classe_cible = next(
                            (c for c in classe_obj if normaliser_chaine(c.libelle or getattr(c, 'nom', '')) == norm_classe),
                            None
                        )

                        if not classe_cible:
                            classe_cible = Classe(
                                school_id=resolved_school_id,
                                cycle=cycle_en_cours,
                                libelle=nom_classe
                            )
                            db.add(classe_cible)
                            db.flush()

                        # Enregistrement dans Programme en stockant le niveau/classe dans nom_matiere ou via attributs disponibles
                        prog_obj = db.query(Programme).filter(
                            Programme.school_id == resolved_school_id,
                            Programme.nom_matiere == norm_mat,
                        ).first()

                        # Recherche si un programme spécifique existe pour cette classe/niveau
                        # Stockons l'association dans Programme en utilisant code_matiere pour stocker la classe (ex: "3eme")
                        prog_classe = db.query(Programme).filter(
                            Programme.school_id == resolved_school_id,
                            Programme.nom_matiere == norm_mat,
                            Programme.code_matiere == norm_classe
                        ).first()

                        if prog_classe:
                            prog_classe.volume_horaire = vol
                            prog_classe.coefficient = coef
                            count_updated += 1
                        else:
                            nouveau_prog = Programme(
                                school_id=resolved_school_id,
                                nom_matiere=norm_mat,
                                code_matiere=norm_classe, # On stocke la classe ici de façon propre
                                volume_horaire=vol,
                                coefficient=coef,
                            )
                            db.add(nouveau_prog)
                            count_added += 1

                    db.add(
                        ActivityLog(
                            school_id=resolved_school_id,
                            timestamp=datetime.utcnow(),
                            username=st.session_state.get("username", "admin"),
                            action=f"Import programmes par classe : {count_added} ajouts, {count_updated} màj ({cycle_en_cours})",
                            module="Import Programmes",
                            statut="Succès",
                        )
                    )
                    db.commit()
                    st.success(f"✅ Importation réussie : **{count_added}** ajout(s) et **{count_updated}** mise(s) à jour !")
                except Exception as ex:
                    db.rollback()
                    st.error(f"⚠️ Erreur lors de l'enregistrement : {ex}")
                finally:
                    db.close()
        except Exception as e:
            st.error(f"⚠️ Erreur lors de la lecture du fichier : {e}")

afficher_import_programmes_pdf = afficher_upload_programmes
afficher_import_programmes = afficher_upload_programmes
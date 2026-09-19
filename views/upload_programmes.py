from datetime import datetime
import io
from database.db_config import SessionLocal
from database.models import ActivityLog, Classe, Matiere, School
import pandas as pd
import streamlit as st


def afficher_upload_programmes():
    st.subheader("📥 Import des Programmes & Coefficients par Classe")
    st.markdown(
        "Importez vos programmes académiques en spécifiant la classe pour "
        "gerer finement les coefficients et volumes horaires selon les niveaux."
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

        ecole_active_id = school_id if school_id else target_school_id

        if ecole_active_id:
            ecole_courante = (
                db.query(School).filter(School.id == ecole_active_id).first()
            )
            school_name = (
                ecole_courante.nom
                if ecole_courante
                else st.session_state.get("school_name", "Établissement")
            )
        else:
            school_name = st.session_state.get("school_name", "Établissement")
            
        # Récupération des classes de l'école pour validation
        classes_query = db.query(Classe)
        if school_id:
            classes_query = classes_query.filter(Classe.school_id == school_id)
        classes_disponibles = classes_query.all()
        classes_dict = {c.libelle.strip().lower(): c.id for c in classes_disponibles}

    finally:
        db.close()

    cycle_en_cours = st.session_state.get("cycle_actif", "Collège")

    if not school_id and not is_super_admin:
        st.warning("⚠️ Veuillez vous connecter pour accéder à cette section.")
        return

    st.markdown(
        f"### Import de données — **{school_name} ({cycle_en_cours})**"
    )

    st.markdown("#### Étape 1 : Télécharger le modèle officiel mis à jour")
    st.markdown(
        "Le modèle intègre désormais une colonne **Classe** pour différencier les volumes et coefficients (ex: 6ème, 3ème)."
    )

    # Modèle Excel avec la colonne Classe
    df_modele = pd.DataFrame({
        "Matière": [
            "Mathématiques",
            "Mathématiques",
            "Français",
            "Physique-Chimie",
        ],
        "Classe": [
            "6ème",
            "3ème",
            "6ème",
            "3ème",
        ],
        "Coefficient": [5, 4, 5, 3],
        "Volume Horaire Prévu": [50, 45, 50, 35],
    })

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_modele.to_excel(writer, index=False, sheet_name="Modele_Programmes")
    excel_data = output.getvalue()

    st.download_button(
        label="📊 Télécharger le modèle Excel avec Classes (.xlsx)",
        data=excel_data,
        file_name=f"modele_programmes_par_classe_{cycle_en_cours.lower()}.xlsx",
        mime=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
    )

    st.markdown("---")
    st.markdown("#### Étape 2 : Importer et prévisualiser votre fichier")

    uploaded_file = st.file_uploader(
        "Sélectionnez le fichier rempli (.xlsx ou .csv)", type=["xlsx", "csv"]
    )
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith(".csv"):
                df_import = pd.read_csv(uploaded_file)
            else:
                df_import = pd.read_excel(uploaded_file)

            st.success("✅ Fichier chargé avec succès ! Aperçu des données :")
            st.dataframe(df_import, use_container_width=True)

            if st.button("Enregistrer les données importées", type="primary"):
                db = SessionLocal()
                try:
                    resolved_school_id = school_id if school_id else target_school_id
                    count_added = 0
                    
                    for _, row in df_import.iterrows():
                        nom_mat = str(row.get("Matière", "")).strip()
                        nom_classe = str(row.get("Classe", "")).strip()
                        coef = float(row.get("Coefficient", 1) or 1)
                        vol = float(row.get("Volume Horaire Prévu", 45) or 45)

                        if nom_mat and nom_mat != "nan":
                            # Recherche de l'ID de la classe correspondante si nécessaire
                            # (Ajustez selon si votre table Matiere possède un classe_id ou reste par cycle/niveau)
                            
                            nouvelle_matiere = Matiere(
                                school_id=resolved_school_id,
                                cycle=cycle_en_cours,
                                libelle=nom_mat,
                                coefficient=coef,
                                volume_horaire=vol,
                            )
                            db.add(nouvelle_matiere)
                            count_added += 1

                    db.add(
                        ActivityLog(
                            school_id=resolved_school_id,
                            timestamp=datetime.utcnow(),
                            username=st.session_state.get("username", "admin"),
                            action=(
                                f"Importation de programmes par classe ({count_added} entrées) "
                                f"pour le cycle {cycle_en_cours}"
                            ),
                            module="Import Programmes",
                            statut="Succès",
                        )
                    )
                    db.commit()
                    st.success(
                        f"✅ {count_added} ligne(s) de programme importée(s) et rattachée(s) à "
                        f"**{school_name}** ({cycle_en_cours}) avec succès !"
                    )
                except Exception as ex:
                    db.rollback()
                    st.error(
                        f"⚠️ Erreur lors de l'enregistrement en base de données : {ex}"
                    )
                finally:
                    db.close()
        except Exception as e:
            st.error(f"⚠️ Erreur lors de la lecture du fichier : {e}")

# Alias de compatibilité
afficher_import_programmes_pdf = afficher_upload_programmes
afficher_import_programmes = afficher_upload_programmes
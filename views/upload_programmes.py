from datetime import datetime
import io
from database.db_config import SessionLocal
from database.models import ActivityLog, Matiere, School
from database.queries import get_classes_cached, get_matieres_cached
import pandas as pd
import streamlit as st


def afficher_upload_programmes():
  st.subheader("📥 Import des Programmes & Coefficients")
  st.markdown(
      "Importez facilement vos programmes académiques, coefficients et volumes"
      " horaires par cycle et par établissement avec isolation multi-tenant"
      " stricte."
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
  finally:
    db.close()

  cycle_en_cours = st.session_state.get("cycle_actif", "Collège")

  if not school_id and not is_super_admin:
    st.warning("⚠️ Veuillez vous connecter pour accéder à cette section.")
    return

  st.markdown(
      f"### Import de données — **{school_name} ({cycle_en_cours})**"
  )
  st.info(
      f"Les programmes importés seront automatiquement rattachés au cycle actif"
      f" : **{cycle_en_cours}** pour l'établissement **{school_name}**."
  )

  st.markdown("#### Étape 1 : Télécharger le modèle officiel")
  st.markdown(
      "Récupérez le fichier modèle pré-formaté au format Excel. Remplissez-le"
      " avec les matières, chapitres et coefficients de votre établissement."
  )

  df_modele = pd.DataFrame({
      "Matière": [
          "Mathématiques",
          "Français",
          "Histoire-Géo",
          "Physique-Chimie",
      ],
      "Coefficient": [4, 4, 2, 3],
      "Volume Horaire Prévu": [45, 45, 30, 35],
  })

  output = io.BytesIO()
  with pd.ExcelWriter(output, engine="openpyxl") as writer:
    df_modele.to_excel(writer, index=False, sheet_name="Modele_Programmes")
  excel_data = output.getvalue()

  st.download_button(
      label="📊 Télécharger le modèle Excel (.xlsx)",
      data=excel_data,
      file_name=f"modele_programmes_{cycle_en_cours.lower()}.xlsx",
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
            coef = float(row.get("Coefficient", 1) or 1)
            vol = float(row.get("Volume Horaire Prévu", 45) or 45)

            if nom_mat and nom_mat != "nan":
              existante = (
                  db.query(Matiere)
                  .filter(
                      Matiere.school_id == resolved_school_id,
                      Matiere.cycle == cycle_en_cours,
                      (Matiere.libelle == nom_mat) | (Matiere.nom == nom_mat),
                  )
                  .first()
              )
              if not existante:
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
                      f"Importation de programmes ({count_added} matières) pour"
                      f" le cycle {cycle_en_cours}"
                  ),
                  module="Import Programmes PDF",
                  statut="Succès",
              )
          )
          db.commit()
          st.success(
              f"✅ {count_added} matière(s) importée(s) et rattachée(s) à"
              f" **{school_name}** ({cycle_en_cours}) avec succès !"
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


# Alias de compatibilité complète pour le routeur
afficher_import_programmes_pdf = afficher_upload_programmes
afficher_import_programmes = afficher_upload_programmes
afficher_import_programmes_et_coefficients = afficher_upload_programmes
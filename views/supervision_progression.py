from datetime import datetime
from io import BytesIO
import pandas as pd
import streamlit as st
from database.db_config import SessionLocal
from database.models import ActivityLog, CahierTexte, Matiere, School


def afficher_supervision_progression():
  st.subheader("📚 Pilotage, Suivi & Avancement Global des Programmes")
  st.markdown(
      "Tableau de bord exécutif de la Direction des Études : analyse croisée"
      " des volumes prévisionnels, des heures réalisées issues du registre"
      " officiel et des alertes de retard par discipline."
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

    # Récupération de toutes les matières du cycle actif pour l'établissement
    matieres_query = db.query(Matiere).filter(
        Matiere.cycle == cycle_en_cours, Matiere.school_id == ecole_active_id
    )
    if hasattr(Matiere, "deleted_at"):
      matieres_query = matieres_query.filter(Matiere.deleted_at.is_(None))
    matieres_cycle = matieres_query.all()

    st.markdown(
        f"### Synthèse des Programmes — **{school_name} ({cycle_en_cours})**"
    )

    if not matieres_cycle:
      st.warning(
          f"⚠️ Aucune matière enregistrée pour le cycle **{cycle_en_cours}** dans"
          f" l'établissement **{school_name}**."
      )
      st.info(
          "Veuillez d'abord configurer vos disciplines dans le menu **Matières"
          " & Coeffs**."
      )
      return

    # Récupération de toutes les entrées persistantes du cahier de texte en base de données pour l'école
    toutes_entrees = (
        db.query(CahierTexte)
        .filter(CahierTexte.school_id == ecole_active_id)
        .all()
    )

    data_suivi = []
    for mat in matieres_cycle:
      # Filtrage des séances dispensées pour cette matière (liaison par id de matière)
      seances_mat = [e for e in toutes_entrees if e.matiere_id == mat.id]

      # Calcul cumulé du volume horaire réalisé
      volume_realise = 0.0
      for seance in seances_mat:
        duree_str = str(getattr(seance, "duree_seance", "2 heures"))
        if "1" in duree_str:
          volume_realise += 1.0
        elif "2" in duree_str:
          volume_realise += 2.0
        elif "3" in duree_str:
          volume_realise += 3.0
        elif "4" in duree_str:
          volume_realise += 4.0
        else:
          volume_realise += 2.0  # Estimation standard par défaut

      # Volume horaire annuel prévu (standard réglementaire de 45h ou valeur spécifique)
      volume_prevu = float(getattr(mat, "volume_horaire", 45) or 45)

      # Calcul du taux de couverture
      taux = (
          min(100, int((volume_realise / volume_prevu) * 100))
          if volume_prevu > 0
          else 0
      )

      # Analyse croisée et attribution de la remarque / statut de retard
      if taux < 20:
        remarque = "🔴 En retard critique"
      elif taux < 40:
        remarque = "🟠 En léger retard"
      elif taux <= 80:
        remarque = "🟢 Rythme conforme"
      else:
        remarque = "🔵 Programme bien avancé"

      data_suivi.append({
          "Discipline / Matière": mat.libelle,
          "Coefficient": int(getattr(mat, "coefficient", 1) or 1),
          "Volume Prévu": f"{volume_prevu}h",
          "Volume Réalisé": f"{volume_realise}h",
          "Taux d'Avancement": f"{taux}%",
          "Analyse & Remarque": remarque,
      })

    df_suivi = pd.DataFrame(data_suivi)
    st.dataframe(df_suivi, use_container_width=True)

    # Fonction d'export Excel (.xlsx) propre en mémoire
    def to_excel_buffer(df):
      output = BytesIO()
      with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="SuiviProgrammes")
      return output.getvalue()

    excel_data = to_excel_buffer(df_suivi)
    st.download_button(
        label="📥 Télécharger le rapport de suivi des programmes (.xlsx)",
        data=excel_data,
        file_name=f"Suivi_Programmes_{school_name}_{cycle_en_cours}.xlsx",
        mime=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
    )

    # Traçabilité de l'audit dans le journal d'activité
    db.add(
        ActivityLog(
            school_id=ecole_active_id,
            timestamp=datetime.utcnow(),
            username=st.session_state.get("username", "admin"),
            action=(
                f"Consultation du suivi global des programmes"
                f" ({cycle_en_cours}) - {school_name}"
            ),
            module="Suivi des Programmes",
            statut="Succès",
        )
    )
    db.commit()

  finally:
    db.close()


# Alias de compatibilité exhaustive pour éviter toute erreur du routeur app.py
afficher_suivi_programmes = afficher_supervision_progression
afficher_suivi_des_programmes = afficher_supervision_progression
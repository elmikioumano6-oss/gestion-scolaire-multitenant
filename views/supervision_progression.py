from datetime import datetime
from io import BytesIO
import pandas as pd
import streamlit as st
from database.db_config import SessionLocal
from database.models import ActivityLog, CahierTexte, Classe, Matiere, School
from database.queries import get_classes_cached, get_matieres_cached


def afficher_supervision_progression():
  st.subheader("📚 Pilotage, Suivi & Avancement Global des Programmes")
  st.markdown(
      "Tableau de bord exécutif de la Direction des Études : analyse croisée"
      " des volumes prévisionnels par niveau, des heures réalisées issues du"
      " registre officiel et des alertes de retard par discipline."
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

    # 1. Sélection de la classe pour un suivi précis par niveau (évite d'amalgamer 6ème et 3ème)
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

    # Détermination du niveau (6ème, 5ème, 4ème, 3ème)
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

    # Récupération de toutes les matières du cycle actif
    matieres_query = db.query(Matiere).filter(
        Matiere.cycle == cycle_en_cours, Matiere.school_id == ecole_active_id
    )
    if hasattr(Matiere, "deleted_at"):
      matieres_query = matieres_query.filter(Matiere.deleted_at.is_(None))
    matieres_cycle = matieres_query.all()

    st.markdown(
        f"### Synthèse des Programmes pour **{classe_selectionnee} ({niveau_detecte})** — **{school_name}**"
    )

    if not matieres_cycle:
      st.warning(
          f"⚠️ Aucune matière enregistrée pour le cycle **{cycle_en_cours}**."
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
      seances_mat = [e for e in toutes_entrees if e.matiere_id == mat.id]

      # Calcul cumulé du volume horaire réalisé
      volume_realise = 0.0
      for seance in seances_mat:
        d_str = str(getattr(seance, "duree_seance", "1 heure"))
        try:
          chiffre = float("".join(filter(str.isdigit, d_str)) or 1)
          volume_realise += chiffre
        except Exception:
          volume_realise += 1.0

      # Normalisation du nom de la matière pour le barème
      mat_norm = mat_lib.lower().strip()
      if "physique" in mat_norm:
        mat_norm = "physique chimie"
      elif "svt" in mat_norm or "vie" in mat_norm:
        mat_norm = "science de la vie et de la terre"
      elif "eps" in mat_norm or "physique et sportive" in mat_norm:
        mat_norm = "education physique et sportive"
      elif "eco" in mat_norm or "familiale" in mat_norm:
        mat_norm = "economie familiale et sociale"

      # Volume horaire prévu selon le niveau exact de la classe
      volume_prevu = 45.0
      if (
          niveau_detecte in BAREME_COLLEGE
          and mat_norm in BAREME_COLLEGE[niveau_detecte]
      ):
        volume_prevu = float(BAREME_COLLEGE[niveau_detecte][mat_norm])
      elif hasattr(mat, "volume_horaire") and mat.volume_horaire:
        volume_prevu = float(mat.volume_horaire)

      # Calcul du taux de couverture
      taux = (
          min(100, int((volume_realise / volume_prevu) * 100))
          if volume_prevu > 0
          else 0
      )

      # Analyse de la progression
      if taux < 20:
        remarque = "🔴 En retard critique"
      elif taux < 40:
        remarque = "🟠 En léger retard"
      elif taux <= 80:
        remarque = "🟢 Rythme conforme"
      else:
        remarque = "🔵 Programme bien avancé"

      data_suivi.append({
          "Discipline / Matière": mat_lib.title(),
          "Coefficient": int(getattr(mat, "coefficient", 1) or 1),
          "Volume Prévu": f"{volume_prevu:g}h",
          "Volume Réalisé": f"{volume_realise:g}h",
          "Taux d'Avancement": f"{taux}%",
          "Analyse & Remarque": remarque,
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
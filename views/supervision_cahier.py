from datetime import datetime
import pandas as pd
import streamlit as st
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
from database.queries import get_classes_cached, get_matieres_cached
from sqlalchemy import or_


def afficher_supervision_cahier():
  st.subheader(
      "📋 Contrôle d'Inspection Pédagogique, Archivage & Registre Officiel"
  )
  st.markdown(
      "Portail officiel d'audit aux normes internationales (SIA) pour la"
      " direction, le censeur et les inspecteurs de l'enseignement."
  )
  st.markdown("---")

  school_id = st.session_state.get("school_id")
  is_super_admin = st.session_state.get("is_super_admin", False)
  username = st.session_state.get("username", "admin")

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
      school_devise = (
          ecole_courante.devise
          if ecole_courante
          else "Excellence - Persévérance - Réussite"
      )
    else:
      school_name = st.session_state.get("school_name", "Établissement")
      school_devise = "Excellence - Persévérance - Réussite"

    # Récupération de l'année scolaire active
    annee_active = (
        db.query(AnneeScolaire)
        .filter(AnneeScolaire.school_id == school_id, AnneeScolaire.active == True)
        .first()
    )
    libelle_annee = annee_active.libelle if annee_active else "2026-2027"
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

    # --- En-tête Institutionnel Administratif ---
    st.markdown(f"### 🏫 **{school_name}** — Cycle : **{cycle_en_cours}**")
    st.caption(
        f"Devise : {school_devise} | Année Scolaire : {libelle_annee} | Niamey,"
        " Niger"
    )

    classes_query = db.query(Classe).filter(Classe.cycle == cycle_en_cours)
    if not is_super_admin and school_id:
      classes_query = classes_query.filter(Classe.school_id == school_id)
    else:
      classes_query = classes_query.filter(
          Classe.school_id == target_school_id
      )
    classes_cycle = classes_query.all()

    if not classes_cycle:
      st.warning(
          f"⚠️ Aucune classe enregistrée pour le cycle **{cycle_en_cours}**"
          f" dans l'établissement **{school_name}**."
      )
      return

    # Filtres de supervision avancés
    col_f1, col_f2 = st.columns(2)
    with col_f1:
      noms_classes = [c.libelle if hasattr(c, 'libelle') and c.libelle else getattr(c, 'nom', f"Classe {c.id}") for c in classes_cycle]
      classe_suivie = st.selectbox(
          "Sélectionner la classe à inspecter",
          noms_classes,
          key="sup_classe_select",
      )
    with col_f2:
      periode_inspection = st.selectbox(
          "Période d'évaluation / Trimestre",
          [
              "Année complète",
              "Trimestre 1",
              "Trimestre 2",
              "Trimestre 3",
          ],
          key="sup_periode_select",
      )

    classe_obj = next(
        (c for c in classes_cycle if (c.libelle if hasattr(c, 'libelle') and c.libelle else getattr(c, 'nom', f"Classe {c.id}")) == classe_suivie), None
    )
    st.info(
        f"🔍 Registre d'inspection actif pour la classe de **{classe_suivie}** ("
        f"{periode_inspection})."
    )

    matieres_query = db.query(Matiere).filter(Matiere.cycle == cycle_en_cours)
    if not is_super_admin and school_id:
      matieres_query = matieres_query.filter(Matiere.school_id == school_id)
    else:
      matieres_query = matieres_query.filter(
          Matiere.school_id == target_school_id
      )
    matieres_cycle = matieres_query.all()

    if not matieres_cycle or not classe_obj:
      st.info(f"Aucune matière configurée pour le cycle **{cycle_en_cours}**.")
      return

    data_suivi = []
    for mat in matieres_cycle:
      mat_lib = mat.libelle if hasattr(mat, 'libelle') and mat.libelle else getattr(mat, 'nom', 'Matière')
      mat_code = getattr(mat, 'code', '') or ''
      
      # Récupération exacte des heures prévues depuis les programmes importés
      prog_obj = (
          db.query(Programme)
          .filter(
              Programme.school_id == target_school_id,
              or_(
                  Programme.code_matiere == mat_code,
                  Programme.nom_matiere == mat_lib,
              ),
          )
          .first()
      )

      heures_prevues = (
          prog_obj.volume_horaire
          if prog_obj and prog_obj.volume_horaire > 0
          else 0.0
      )

      # Entrées du cahier de texte en base pour cette classe et cette matière
      entrees_cahier = (
          db.query(CahierTexte)
          .filter(
              CahierTexte.school_id == target_school_id,
              CahierTexte.classe_id == classe_obj.id,
              CahierTexte.matiere_id == mat.id,
          )
          .all()
      )

      # Calcul précis des heures réalisées
      heures_realisees = 0.0
      for e in entrees_cahier:
        duree_str = getattr(e, "duree_seance", "1 heure")
        try:
          val_duree = float(duree_str.split()[0])
        except Exception:
          val_duree = 1.0
        heures_realisees += val_duree

      progression_pct = (
          round((heures_realisees / heures_prevues) * 100, 1)
          if heures_prevues > 0
          else 0.0
      )
      if progression_pct > 100.0:
        progression_pct = 100.0

      if entrees_cahier:
        dernier_cours = entrees_cahier[-1]
        dernier_chapitre = (
            dernier_cours.contenu[:60] + "..."
            if dernier_cours.contenu
            else "N/D"
        )
        enseignant_ref = (
            dernier_cours.enseignant_user.username
            if dernier_cours.enseignant_user
            else (dernier_cours.auteur_saisie or "Corps professoral")
        )
      else:
        dernier_chapitre = "Aucun cours enregistré"
        enseignant_ref = "Non assigné"

      if heures_prevues == 0.0:
        appreciation = "⚠️ Volume horaire non défini (Programme manquant)"
      elif progression_pct >= 75:
        appreciation = "🟢 Rythme excellent et conforme"
      elif progression_pct >= 40:
        appreciation = "🟡 Rythme satisfaisant"
      elif progression_pct > 0:
        appreciation = "🟠 Rythme insuffisant - Retard à rattraper"
      else:
        appreciation = "🔴 En attente de première saisie"

      data_suivi.append({
          "Matière": mat_lib,
          "Enseignant(e)": enseignant_ref,
          "Heures Prévues": f"{heures_prevues}h",
          "Heures Réalisées": f"{heures_realisees}h",
          "Progression (%)": f"{progression_pct}%",
          "Dernier Chapitre / Notions": dernier_chapitre,
          "Appréciation Inspection": appreciation,
      })

    df_suivi = pd.DataFrame(data_suivi)
    st.dataframe(df_suivi, use_container_width=True)

    # --- Options d'Export Officiel pour l'Administration et l'Inspection ---
    st.download_button(
        label=(
            "📥 Télécharger le rapport officiel d'inspection (Format CSV"
            " Archivage)"
        ),
        data=df_suivi.to_csv(index=False).encode("utf-8"),
        file_name=(
            f"rapport_inspection_officiel_{classe_suivie}_"
            f"{datetime.now().strftime('%Y%m%d')}.csv"
        ),
        mime="text/csv",
    )

    # --- Section de Visa, Observations Pédagogiques & Contrôle Censeur/Inspecteur ---
    st.markdown(
        "### ✍️ Visa Officiel, Observations du Censeur & Contrôle d'Inspection"
    )
    with st.form("form_visa_inspection"):
      observation_censeur = st.text_area(
          "Observations de la Direction / Rapport de l'Inspecteur (remarques"
          " sur la tenue du cahier, avancement, discipline pédagogique...)",
          key="obs_insp_texte",
      )
      col_v1, col_v2, col_v3 = st.columns(3)
      with col_v1:
        qualite_visiteur = st.selectbox(
            "Qualité du signataire",
            ["Censeur / Directeur des Études", "Inspecteur Pédagogique", "Proviseur"],
        )
      with col_v2:
        statut_registre = st.selectbox(
            "Statut du registre",
            [
                "Visé & Conforme",
                "Observations notifiées",
                "Retard signalé - Entretien requis",
                "Validé pour archive officielle",
            ],
        )
      with col_v3:
        certifie_conforme = st.checkbox(
            "Certifier et apposer le sceau numérique"
        )

      submitted_visa = st.form_submit_button(
          "🛡️ Valider, Archiver et Consigner le Visa Officiel"
      )
      if submitted_visa:
        nouveau_log = ActivityLog(
            school_id=target_school_id,
            timestamp=datetime.now(),
            username=username,
            action=(
                f"Visa officiel [{qualite_visiteur}] - Classe {classe_suivie}"
                f" [{statut_registre}]"
            ),
            module="Supervision Cahier",
            statut="Certifié" if certifie_conforme else "En cours",
            valeur_apres=observation_censeur,
        )
        db.add(nouveau_log)
        db.commit()
        st.success(
            f"✅ Le registre de la classe **{classe_suivie}** a été officiellement"
            f" visé par **{qualite_visiteur}** et archivé dans les registres"
            " sécurisés de l'établissement."
        )

    # Enregistrement du log de consultation standard pour l'historique
    nouveau_log_consult = ActivityLog(
        school_id=target_school_id,
        timestamp=datetime.now(),
        username=username,
        action=f"Consultation registre inspection - Classe {classe_suivie}",
        module="Supervision Cahier",
        statut="Succès",
    )
    db.add(nouveau_log_consult)
    db.commit()

  finally:
    db.close()


# Alias de compatibilité
afficher_supervision_cahier = afficher_supervision_cahier
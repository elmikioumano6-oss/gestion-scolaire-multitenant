from datetime import datetime
import os
from database.audit import log_action_erp
from database.db_config import SessionLocal
from database.models import School
from database.queries import get_classes_cached, get_matieres_cached
import streamlit as st


def afficher_parametres():
  st.subheader("⚙️ Paramètres & Configuration de l'Établissement")
  st.markdown(
      "Personnalisation des informations institutionnelles, du logo officiel,"
      " de l'exercice comptable et des paramètres spécifiques."
  )
  st.markdown("---")

  school_id = st.session_state.get("school_id")
  is_super_admin = st.session_state.get("is_super_admin", False)

  if not school_id and not is_super_admin:
    st.warning("⚠️ Veuillez vous connecter pour accéder à cette section.")
    return

  db = SessionLocal()
  try:
    target_id = school_id
    if is_super_admin and not target_id:
      ecoles = db.query(School).all()
      if not ecoles:
        st.warning("Aucune école enregistrée.")
        return
      choix_ecole = st.selectbox(
          "Sélectionner l'établissement à configurer",
          options=[e.nom for e in ecoles],
      )
      ecole_courante = next(
          (e for e in ecoles if e.nom == choix_ecole), ecoles[0]
      )
      target_id = ecole_courante.id
    else:
      ecole_courante = db.query(School).filter(School.id == target_id).first()

    if not ecole_courante:
      st.error("Établissement introuvable.")
      return

    with st.form("form_parametres_ecole"):
      st.markdown(f"### 🏫 Modification des informations : {ecole_courante.nom}")

      col1, col2 = st.columns(2)
      with col1:
        nouveau_nom = st.text_input(
            "Nom de l'établissement", value=ecole_courante.nom
        )
        nouvelle_devise_institutionnelle = st.text_input(
            "Devise / Slogan de l'établissement",
            value=ecole_courante.devise
            or "Excellence - Persévérance - Réussite",
        )
        nouvelle_adresse = st.text_input(
            "Adresse / Quartier",
            value=getattr(ecole_courante, "adresse", "Quartier, Niamey - Niger"),
        )
      with col2:
        nouveaux_contacts = st.text_input(
            "Numéros de téléphone (séparés par des /)",
            value=getattr(ecole_courante, "contacts", "N/D"),
        )

        exercice_actuel = getattr(
            ecole_courante, "exercice_comptable", "2025-2026"
        )
        nouvel_exercice = st.selectbox(
            "📅 Exercice Comptable / Année Scolaire Active",
            ["2024-2025", "2025-2026", "2026-2027", "2027-2028"],
            index=(
                ["2024-2025", "2025-2026", "2026-2027", "2027-2028"].index(
                    exercice_actuel
                )
                if exercice_actuel
                in ["2024-2025", "2025-2026", "2026-2027", "2027-2028"]
                else 1
            ),
        )

        devise_monetaire_actuelle = getattr(
            ecole_courante, "devise_monetaire", "FCFA (XOF)"
        )
        nouvelle_devise_monetaire = st.text_input(
            "💰 Unité Monétaire Officielle", value=devise_monetaire_actuelle
        )

      st.markdown("---")
      st.markdown("#### 🖼️ Logo Officiel de l'Établissement")

      # Affichage du logo actuel s'il existe
      logo_actuel = getattr(ecole_courante, "logo_path", None)
      if logo_actuel and os.path.exists(logo_actuel):
        st.image(logo_actuel, width=120, caption="Logo actuel")
      else:
        st.info(
            "Aucun logo personnalisé enregistré. Le système utilise le logo"
            " par défaut."
        )

      logo_file = st.file_uploader(
          "Téléverser un nouveau logo (Formats PNG, JPG)",
          type=["png", "jpg", "jpeg"],
      )

      submitted = st.form_submit_button(
          "💾 Enregistrer les modifications", type="primary"
      )
      if submitted:
        ecole_courante.nom = nouveau_nom.strip()
        ecole_courante.devise = nouvelle_devise_institutionnelle.strip()
        ecole_courante.adresse = nouvelle_adresse.strip()
        ecole_courante.contacts = nouveaux_contacts.strip()

        if hasattr(ecole_courante, "exercice_comptable"):
          ecole_courante.exercice_comptable = nouvel_exercice
        if hasattr(ecole_courante, "devise_monetaire"):
          ecole_courante.devise_monetaire = nouvelle_devise_monetaire.strip()

        # Gestion du téléversement du logo
        if logo_file is not None:
          os.makedirs("assets/logos", exist_ok=True)
          logo_path = f"assets/logos/school_{ecole_courante.id}.png"
          with open(logo_path, "wb") as f:
            f.write(logo_file.getbuffer())

          if hasattr(ecole_courante, "logo_path"):
            ecole_courante.logo_path = logo_path

        db.commit()
        st.success(
            "✅ Paramètres et logo mis à jour avec succès pour l'établissement !"
        )
        st.rerun()

  finally:
    db.close()


# Alias de compatibilité complète pour le routeur
afficher_parametre = afficher_parametres
afficher_configuration = afficher_parametres
afficher_gestion_parametres = afficher_parametres
from datetime import datetime, timedelta
import urllib.parse
import random
import string
import bcrypt
from database.audit import log_action_erp
from database.db_config import SessionLocal
from database.models import Enseignant, School, User
import pandas as pd
import streamlit as st


def afficher_gestion_utilisateurs():
  st.subheader("👥 Gestion des Comptes Utilisateurs & Rôles")
  st.markdown(
      "Administration sécurisée des accès, des comptes et des rôles du"
      " personnel avec isolation multi-tenant stricte et suivi des statuts en"
      " temps réel."
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
    tab_liste, tab_ajout = st.tabs([
        "📋 Liste des Utilisateurs",
        "➕ Nouvel Utilisateur",
    ])

    with tab_liste:
      st.markdown(
          f"### Utilisateurs Actifs — **{school_name} ({cycle_en_cours})**"
      )

      # FILTRAGE STRICT PAR ÉCOLE ACTIVE
      users_query = db.query(User)
      if school_id:
        users_query = users_query.filter(User.school_id == school_id)

      utilisateurs_db = users_query.all()
      if not utilisateurs_db:
        st.info("Aucun utilisateur enregistré dans cet établissement.")
      else:
        data_u = []
        noms_vus = set()
        maintenant = datetime.now()

        for u in utilisateurs_db:
          if u.username not in noms_vus:
            noms_vus.add(u.username)

            # Détermination du statut en ligne (actif il y a moins de 5 minutes)
            statut_connexion = "🔴 Hors ligne"
            if hasattr(u, "derniere_activite") and u.derniere_activite:
              # Gestion de la différence de temps
              diff = maintenant - u.derniere_activite
              if diff < timedelta(minutes=5):
                statut_connexion = "🟢 En ligne"

            data_u.append({
                "Nom d'utilisateur": u.username,
                "Rôle / Fonction": getattr(u, "role", "N/D"),
                "Statut Actuel": statut_connexion,
                "Mot de passe à changer": (
                    "Oui" if getattr(u, "changer_mdp_requis", False) else "Non"
                ),
            })

        df_users = pd.DataFrame(data_u)
        st.dataframe(df_users, use_container_width=True)

    with tab_ajout:
      st.markdown(
          f"### Création d'un Nouveau Compte Utilisateur — **{school_name}**"
      )

      if "temp_gen_pwd" not in st.session_state:
        st.session_state["temp_gen_pwd"] = ""

      col_g1, col_g2 = st.columns([3, 1])
      with col_g2:
        if st.button("🎲 Générer un MDP sécurisé"):
          chars = string.ascii_letters + string.digits + "@#$%&!"
          st.session_state["temp_gen_pwd"] = "".join(
              random.choice(chars) for _ in range(8)
          )
          st.rerun()

      enseignants_db = (
          db.query(Enseignant)
          .filter(Enseignant.school_id == (school_id or 1))
          .all()
      )
      noms_enseignants = [f"{e.nom} {e.prenom}" for e in enseignants_db]

      with st.form("form_creation_compte"):
        col1, col2 = st.columns(2)
        with col1:
          nouveau_user = st.text_input("Nom d'utilisateur (Identifiant)")
          mot_de_passe = st.text_input(
              "Mot de passe provisoire",
              value=st.session_state["temp_gen_pwd"],
              type="password",
          )
        with col2:
          role_options = {
              "directeur": "Directeur / Administrateur",
              "enseignant": "Enseignant / Professeur",
              "econome": "Économe / Finances",
              "surveillant": "Surveillant Général",
              "inspecteur": "Inspecteur",
              "parent": "Parent d'élève",
          }
          role_attribue = st.selectbox(
              "Rôle / Fonction", options=list(role_options.keys())
          )
          cycle_associe = st.selectbox(
              "Cycle d'affectation",
              ["Collège", "Lycée", "Tous les cycles"],
          )

        role_descriptions = {
            "directeur": (
                "Accès complet à la gestion administrative, financière et"
                " aux paramètres de l'école."
            ),
            "enseignant": (
                "Saisie des notes, émargement du cahier de texte et suivi de"
                " classe."
            ),
            "econome": (
                "Gestion de la trésorerie, encaissements de scolarité et suivi"
                " des dépenses."
            ),
            "surveillant": (
                "Gestion des absences, retours de discipline et cahier de"
                " correspondance."
            ),
            "inspecteur": "Supervision pédagogique et audit des notes.",
            "parent": (
                "Accès restreint au portail famille pour le suivi exclusif de"
                " l'enfant."
            ),
        }
        st.markdown(
            f"<div style='background-color: rgba(217, 119, 6, 0.1); padding: 8px 12px; border-radius: 6px; border-left: 3px solid #D97706; font-size: 0.85rem; color: #E2E8F0; margin-bottom: 10px;'>ℹ️ <b>Permission :</b> {role_descriptions.get(role_attribue, 'Accès standard')}</div>",
            unsafe_allow_html=True,
        )

        prof_lie = None
        if role_attribue == "enseignant" and noms_enseignants:
          prof_lie = st.selectbox(
              "Lier à un enseignant enregistré", ["Aucun"] + noms_enseignants
          )

        contact_tel = st.text_input(
            "Numéro de téléphone (WhatsApp optionnel pour notification)",
            placeholder="Ex: 90123456",
        )

        submitted_user = st.form_submit_button(
            "💾 Créer et Sécuriser le Compte Utilisateur", type="primary"
        )
        if submitted_user:
          if not nouveau_user or not mot_de_passe:
            st.error("⚠️ Veuillez renseigner l'identifiant et le mot de passe.")
          elif len(mot_de_passe) < 6:
            st.error("⚠️ Le mot de passe doit contenir au moins 6 caractères.")
          else:
            existe_deja = (
                db.query(User)
                .filter(User.username == nouveau_user.strip())
                .first()
            )
            if existe_deja:
              st.error(
                  f"⚠️ Un utilisateur portant l'identifiant '{nouveau_user}'"
                  " existe déjà."
              )
            else:
              hashed = bcrypt.hashpw(
                  mot_de_passe.encode("utf-8"), bcrypt.gensalt()
              ).decode("utf-8")
              nouveau_compte = User(
                  school_id=school_id if school_id else 1,
                  username=nouveau_user.strip(),
                  password=hashed,
                  role=role_attribue,
                  changer_mdp_requis=True,
              )
              db.add(nouveau_compte)

              log_action_erp(
                  module="IAM & Sécurité",
                  action=(
                      f"Création du compte utilisateur : {nouveau_user.strip()}"
                      f" (Rôle: {role_attribue}, Cycle: {cycle_associe})"
                  ),
                  statut="Critique",
                  valeur_avant="Inexistant",
                  valeur_apres=f"Compte actif [{role_attribue} - {cycle_associe}]",
              )

              db.commit()

              if "temp_gen_pwd" in st.session_state:
                st.session_state["temp_gen_pwd"] = ""

              st.success(
                  f"✅ Le compte de **{nouveau_user.strip()}** ({role_attribue})"
                  f" a été créé avec succès ! Un changement de mot de passe"
                  f" sera exigé à sa première connexion."
              )

              if contact_tel.strip():
                clean_num = "".join(filter(str.isdigit, contact_tel.strip()))
                if len(clean_num) == 8:
                  clean_num = "227" + clean_num
                msg = (
                    f"Bonjour, votre compte {role_attribue} pour"
                    f" l'établissement {school_name} est créé.\n👤 Identifiant"
                    f" : {nouveau_user.strip()}\n🔑 Mot de passe provisoire :"
                    f" {mot_de_passe}\n⚠️ Modification obligatoire à la"
                    f" connexion."
                )
                wa_url = (
                    f"https://wa.me/{clean_num}?text="
                    + urllib.parse.quote(msg)
                )
                st.markdown(
                    f"""
                            <a href="{wa_url}" target="_blank" style="display:inline-block;background-color:#25D366;color:white;padding:8px 16px;border-radius:5px;text-decoration:none;font-weight:bold;margin-top:10px;">
                                📲 Envoyer les accès par WhatsApp
                            </a>
                            """,
                    unsafe_allow_html=True,
                )

  finally:
    db.close()


# Alias de compatibilité exhaustive
afficher_gestion_comptes = afficher_gestion_utilisateurs
afficher_gestion_compte = afficher_gestion_utilisateurs
afficher_comptes = afficher_gestion_utilisateurs
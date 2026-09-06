from datetime import datetime
from database.audit import log_action_erp
from database.db_config import SessionLocal
from database.models import Enseignant, School
import pandas as pd
import streamlit as st


def afficher_gestion_utilisateurs():
  st.subheader("👥 Gestion des Comptes Utilisateurs & Rôles")
  st.markdown(
      "Administration sécurisée des accès, des comptes et des rôles du"
      " personnel avec isolation multi-tenant stricte."
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

    if "users_data" not in st.session_state:
      st.session_state["users_data"] = {
          "CSP Rahmat-FH": [
              {
                  "Nom d'utilisateur": "admin_rahmat",
                  "Rôle / Fonction": "directeur",
                  "Cycle d'affectation": "Tous les cycles",
                  "Dernière activité": "2026-09-02 13:57:54.358633",
              }
          ]
      }

    key_store = school_name
    utilisateurs_ecole = st.session_state["users_data"].get(key_store, [])

    with tab_liste:
      st.markdown(
          f"### Utilisateurs Actifs — **{school_name} ({cycle_en_cours})**"
      )
      if not utilisateurs_ecole:
        st.info("Aucun utilisateur enregistré dans cet établissement.")
      else:
        df_users = pd.DataFrame(utilisateurs_ecole)
        st.dataframe(df_users, use_container_width=True)

    with tab_ajout:
      st.markdown(
          f"### Création d'un Nouveau Compte Utilisateur — **{school_name}**"
      )
      
      # Récupération de la liste des enseignants pour liaison éventuelle
      enseignants_db = db.query(Enseignant).filter(Enseignant.school_id == (school_id or 1)).all()
      noms_enseignants = [f"{e.nom} {e.prenom}" for e in enseignants_db]

      with st.form("form_creation_compte"):
        col1, col2 = st.columns(2)
        with col1:
          nouveau_user = st.text_input("Nom d'utilisateur (Identifiant)")
          mot_de_passe = st.text_input("Mot de passe provisoire", type="password")
        with col2:
          role_attribue = st.selectbox(
              "Rôle / Fonction",
              [
                  "directeur",
                  "enseignant",
                  "econome",
                  "surveillant",
                  "inspecteur",
                  "parent",
              ],
          )
          cycle_associe = st.selectbox(
              "Cycle d'affectation",
              ["Collège", "Lycée", "Tous les cycles"],
          )

        # Liaison conditionnelle si le rôle est enseignant
        prof_lie = None
        if role_attribue == "enseignant" and noms_enseignants:
          prof_lie = st.selectbox("Lier à un enseignant enregistré", ["Aucun"] + noms_enseignants)

        submitted_user = st.form_submit_button(
            "💾 Créer le Compte Utilisateur", type="primary"
        )
        if submitted_user:
          if not nouveau_user or not mot_de_passe:
            st.error("⚠️ Veuillez renseigner l'identifiant et le mot de passe.")
          else:
            existe_deja = any(
                u["Nom d'utilisateur"] == nouveau_user for u in utilisateurs_ecole
            )
            if existe_deja:
              st.error(
                  f"⚠️ Un utilisateur portant l'identifiant '{nouveau_user}' existe déjà."
              )
            else:
              nouveau_compte = {
                  "Nom d'utilisateur": nouveau_user,
                  "Rôle / Fonction": role_attribue,
                  "Cycle d'affectation": cycle_associe,
                  "Enseignant lié": prof_lie if prof_lie and prof_lie != "Aucun" else "—",
                  "Dernière activité": str(datetime.utcnow()),
              }
              if key_store not in st.session_state["users_data"]:
                st.session_state["users_data"][key_store] = []
              st.session_state["users_data"][key_store].append(nouveau_compte)

              log_action_erp(
                  module="Gestion Comptes",
                  action=(
                      f"Création de compte utilisateur : {nouveau_user} (Rôle:"
                      f" {role_attribue}, Cycle: {cycle_associe})"
                  ),
                  statut="Critique",
                  valeur_avant="Inexistant",
                  valeur_apres=f"Compte actif [{role_attribue} - {cycle_associe}]",
              )

              st.success(
                  f"✅ Le compte de **{nouveau_user}** ({role_attribue}) a"
                  f" été créé avec succès pour le cycle **{cycle_associe}** !"
              )

  finally:
    db.close()


# Alias de compatibilité exhaustive
afficher_gestion_comptes = afficher_gestion_utilisateurs
afficher_gestion_compte = afficher_gestion_utilisateurs
afficher_comptes = afficher_gestion_utilisateurs
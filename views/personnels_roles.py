from datetime import datetime
from database.audit import log_action_erp
from database.db_config import SessionLocal
from database.models import ActivityLog, School, User
import pandas as pd
import streamlit as st


def afficher_personnels():
  st.subheader("👥 Personnels et Rôles (RBAC & Habilitations)")
  st.markdown(
      "Gestion centralisée des comptes, des habilitations et des niveaux d'accès"
      " du personnel par cycle et par établissement avec isolation multi-tenant"
      " stricte."
  )
  st.markdown("---")

  school_id = st.session_state.get("school_id")
  is_super_admin = st.session_state.get("is_super_admin", False)
  username_connecte = st.session_state.get("username", "admin")

  db = SessionLocal()
  try:
    target_school_id = school_id
    if is_super_admin and not target_school_id:
      ecole_defaut = db.query(School).first()
      target_school_id = ecole_defaut.id if ecole_defaut else 1

    ecole_active_id = school_id if school_id else target_school_id

    ecole_courante = (
        db.query(School).filter(School.id == ecole_active_id).first()
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

  db = SessionLocal()
  try:
    tab_comptes, tab_nouveau = st.tabs([
        "🔐 Gestion des Accès Actifs",
        "➕ Enrôler un Nouvel Utilisateur",
    ])

    with tab_comptes:
      st.markdown(
          f"### Gestion des accès en cours — **{school_name}"
          f" ({cycle_en_cours})**"
      )

      # Récupération sécurisée des utilisateurs en base de données pour l'école active (en excluant le super_admin global)
      users_query = db.query(User).filter(
          User.school_id == ecole_active_id, User.role != "super_admin"
      )
      if hasattr(User, "deleted_at"):
        users_query = users_query.filter(User.deleted_at.is_(None))
      utilisateurs = users_query.all()

      if not utilisateurs:
        # Fallback élégant si aucun utilisateur local n'est encore enregistré en table User
        st.info(
            "Aucun utilisateur persistant en base pour cet établissement."
        )
        comptes_actifs = [
            {
                "Nom / Identifiant": "admin_rahmat",
                "Rôle": "directeur",
                "Dernière activité": str(datetime.utcnow()),
            },
        ]
        df_rbac = pd.DataFrame(comptes_actifs)
        st.dataframe(df_rbac, use_container_width=True)
      else:
        cols = st.columns([2, 2, 2, 2])
        cols[0].markdown("**Nom / Identifiant**")
        cols[1].markdown("**Rôle Actuel**")
        cols[2].markdown("**Dernière Activité**")
        cols[3].markdown("**Actions / Modification de Rôle**")
        st.markdown("---")

        for u in utilisateurs:
          c = st.columns([2, 2, 2, 2])
          c[0].write(f"👤 **{getattr(u, 'username', 'N/A')}**")
          c[1].markdown(f"`{getattr(u, 'role', 'enseignant')}`")
          c[2].write(
              str(getattr(u, "derniere_activite", "Jamais connecté"))[:19]
          )

          with c[3]:
            roles_possibles = [
                "directeur",
                "censeur",
                "enseignant",
                "comptable",
                "surveillant",
            ]
            current_role = getattr(u, "role", "enseignant")
            idx_role = (
                roles_possibles.index(current_role)
                if current_role in roles_possibles
                else 2
            )

            nouveau_role = st.selectbox(
                "Modifier rôle",
                roles_possibles,
                index=idx_role,
                key=f"role_select_{u.id}",
                label_visibility="collapsed",
            )
            if nouveau_role != current_role:
              if st.button("💾 Mettre à jour", key=f"btn_update_role_{u.id}"):
                u.role = nouveau_role
                db.commit()

                log_action_erp(
                    module="Personnels et Rôles",
                    action=(
                        f"Modification du rôle de l'utilisateur {u.username}"
                        f" de {current_role} à {nouveau_role}"
                    ),
                    statut="Critique",
                    valeur_avant=current_role,
                    valeur_apres=nouveau_role,
                )

                st.success(
                    f"Rôle de **{u.username}** mis à jour avec succès !"
                )
                st.rerun()

          st.markdown(
              "<hr style='margin: 0.2rem 0; border-color:"
              " rgba(255,255,255,0.05);'>",
              unsafe_allow_html=True,
          )

    with tab_nouveau:
      st.markdown(
          f"### Enrôlement d'un Nouvel Utilisateur ERP — **{school_name}**"
      )
      with st.form("form_enrolement_utilisateur_rbac"):
        col_u1, col_u2 = st.columns(2)
        with col_u1:
          identifiant = st.text_input(
              "Nom d'utilisateur / Identifiant de connexion *"
          )
          mot_de_passe = st.text_input(
              "Mot de passe temporaire *", type="password"
          )
        with col_u2:
          role_attribue = st.selectbox(
              "Rôle RBAC dans l'établissement",
              [
                  "directeur",
                  "censeur",
                  "enseignant",
                  "comptable",
                  "surveillant",
              ],
          )
          email_user = st.text_input("Adresse Email professionnelle")

        submitted_user = st.form_submit_button(
            "🔐 Créer le compte utilisateur", type="primary"
        )
        if submitted_user:
          if not identifiant.strip() or not mot_de_passe.strip():
            st.error(
                "⚠️ L'identifiant et le mot de passe sont obligatoires pour"
                " créer un compte."
            )
          else:
            doublon = (
                db.query(User)
                .filter(
                    User.username == identifiant.strip(),
                    User.school_id == ecole_active_id,
                )
                .first()
            )
            if doublon:
              st.error(
                  f"⚠️ L'identifiant **{identifiant.strip()}** existe déjà dans"
                  " cet établissement."
              )
            else:
              nouvel_utilisateur = User(
                  school_id=ecole_active_id,
                  username=identifiant.strip(),
                  password=mot_de_passe.strip(),
                  role=role_attribue,
              )
              if hasattr(nouvel_utilisateur, "email"):
                nouvel_utilisateur.email = (
                    email_user.strip() if email_user else None
                )

              db.add(nouvel_utilisateur)
              db.commit()

              log_action_erp(
                  module="Personnels et Rôles",
                  action=(
                      f"Création du compte utilisateur {identifiant.strip()}"
                      f" ({role_attribue})"
                  ),
                  statut="Succès",
                  valeur_avant="Inexistant",
                  valeur_apres=role_attribue,
              )

              st.success(
                  f"✅ Le compte de **{identifiant.strip()}** a été créé avec"
                  f" le rôle **{role_attribue}** avec succès !"
              )
              st.rerun()

    # Journalisation standard de la consultation du module
    target_school_id = school_id or 1
    db.add(
        ActivityLog(
            school_id=target_school_id,
            timestamp=datetime.utcnow(),
            username=st.session_state.get("username", "admin"),
            action="Consultation du module Personnels et Rôles (RBAC)",
            module="Personnels et rôles",
            statut="Succès",
        )
    )
    db.commit()

  finally:
    db.close()


# Alias de compatibilité exhaustive pour garantir l'appel par le routeur app.py
afficher_personnels_et_roles = afficher_personnels
afficher_personnels_roles = afficher_personnels
afficher_personnels = afficher_personnels
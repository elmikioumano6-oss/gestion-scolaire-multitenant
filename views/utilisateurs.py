import streamlit as st
import pandas as pd
from database.db_config import SessionLocal
from database.models import User, JournalActivite, School
from database.audit import log_action_erp
import bcrypt

# La fonction reçoit maintenant le nom du menu sur lequel on a cliqué
def afficher_utilisateurs(vue_selectionnee="Utilisateurs connectés"):
    school_id = st.session_state.get("school_id")
    is_super_admin = st.session_state.get("is_super_admin", False)
    username_connecte = st.session_state.get("username", "admin")

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

        # ==========================================
        # VUE 1 : GESTION DES UTILISATEURS
        # ==========================================
        if vue_selectionnee == "Utilisateurs connectés":
            st.subheader("🔐 Gestion des Comptes et Utilisateurs")
            st.info("Ici, vous pouvez créer et gérer les accès du personnel au logiciel avec une isolation multi-tenant stricte.")
            
            # --- CRÉATION DE COMPTE ---
            with st.form("form_ajout_user_v2", clear_on_submit=True):
                st.markdown("### Créer un nouveau compte")
                col1, col2 = st.columns(2)
                
                with col1:
                    username = st.text_input("Nom d'utilisateur (Identifiant) *")
                    role = st.selectbox("Rôle de l'utilisateur", ["admin", "directeur", "enseignant", "comptable", "surveillant"])
                with col2:
                    password = st.text_input("Mot de passe *", type="password")
                    confirm_password = st.text_input("Confirmer le mot de passe *", type="password")

                submit = st.form_submit_button("Créer le compte", type="primary")

                if submit:
                    if username.strip() and password:
                        if password == confirm_password:
                            if len(password) < 6:
                                st.error("⚠️ Le mot de passe doit contenir au moins 6 caractères.")
                            else:
                                existe = db.query(User).filter(
                                    User.username == username.strip(),
                                    User.school_id == ecole_active_id
                                ).first()
                                if existe:
                                    st.error("Ce nom d'utilisateur existe déjà dans cet établissement !")
                                else:
                                    hashed = bcrypt.hashpw(password.strip().encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
                                    nouvel_user = User(
                                        school_id=ecole_active_id,
                                        username=username.strip(),
                                        password=hashed,
                                        role=role,
                                        changer_mdp_requis=True
                                    )
                                    db.add(nouvel_user)
                                    db.commit()

                                    log_action_erp(
                                        school_id=ecole_active_id,
                                        module="IAM & Sécurité",
                                        action=f"Création de l'utilisateur {username.strip()} ({role})",
                                        statut="Succès",
                                        valeur_avant="Inexistant",
                                        valeur_apres=role
                                    )

                                    st.success(f"✅ Compte '{username}' créé avec succès ({role}) !")
                                    st.rerun()
                        else:
                            st.error("❌ Les mots de passe ne correspondent pas.")
                    else:
                        st.error("⚠️ Veuillez remplir tous les champs obligatoires.")

            st.markdown("---")

            # --- LISTE DES UTILISATEURS ---
            st.markdown("### Comptes existants")
            users_query = db.query(User).filter(User.school_id == ecole_active_id)
            if not is_super_admin:
                users_query = users_query.filter(User.role != "super_admin")
            utilisateurs = users_query.all()

            if utilisateurs:
                donnees = []
                for u in utilisateurs:
                    statut_str = "✅ Actif" if getattr(u, 'actif', True) else "❌ Suspendu"
                    donnees.append({
                        "Identifiant": u.username,
                        "Rôle": getattr(u, 'role', 'N/D'),
                        "Statut": statut_str
                    })
                    
                st.dataframe(pd.DataFrame(donnees), use_container_width=True, hide_index=True)

                with st.expander("🗑️ Révoquer / Supprimer un compte"):
                    options_users = {f"{u.username} ({u.role})": u for u in utilisateurs if u.username != "admin"}
                    
                    if options_users:
                        user_a_suppr = st.selectbox("Sélectionnez l'utilisateur à supprimer :", options_users.keys())
                        if st.button("Confirmer la suppression", type="primary"):
                            cible = options_users[user_a_suppr]
                            db.delete(cible)
                            db.commit()

                            log_action_erp(
                                school_id=ecole_active_id,
                                module="IAM & Sécurité",
                                action=f"Suppression du compte utilisateur {cible.username}",
                                statut="Critique",
                                valeur_avant=cible.role,
                                valeur_apres="Supprimé"
                            )

                            st.success("Compte utilisateur supprimé.")
                            st.rerun()
                    else:
                        st.info("Aucun compte modifiable.")
            else:
                st.info("Aucun compte utilisateur configuré.")

        # ==========================================
        # VUE 2 : HISTORIQUE DE CONNEXION / SÉCURITÉ
        # ==========================================
        elif vue_selectionnee in ["Historique de connexion", "Journal de sécurité"]:
            st.subheader("📜 Historique de Connexion et Journal de Sécurité")
            st.info("Ce tableau retrace les dernières actions et événements consignés dans le journal d'audit.")
            
            logs_query = db.query(JournalActivite).filter(JournalActivite.school_id == ecole_active_id)
            logs = logs_query.order_by(JournalActivite.timestamp.desc()).limit(100).all()
            
            if logs:
                donnees_logs = []
                for log in logs:
                    dt_str = log.timestamp.strftime("%d/%m/%Y %H:%M:%S") if hasattr(log, 'timestamp') and log.timestamp else "N/D"
                    donnees_logs.append({
                        "Date & Heure": dt_str,
                        "Utilisateur": getattr(log, 'username', 'Système'),
                        "Module": getattr(log, 'module', 'N/D'),
                        "Statut": getattr(log, 'statut', 'Succès'),
                        "Action": getattr(log, 'action', '-')
                    })
                
                df_logs = pd.DataFrame(donnees_logs)
                st.dataframe(df_logs, use_container_width=True, hide_index=True)
            else:
                st.warning("📭 Le journal d'activité est actuellement vide pour cet établissement.")

    finally:
        db.close()

# Alias de compatibilité
afficher_utilisateurs = afficher_utilisateurs
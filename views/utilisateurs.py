import streamlit as st
import pandas as pd
from database.db_config import SessionLocal
from database.models import Utilisateur, LogActivite

# Essai d'importation de votre fonction de sécurité
try:
    from security.auth import hash_password
except ImportError:
    # Fonction de secours si le fichier auth.py n'est pas trouvé
    def hash_password(password):
        return password

# La fonction reçoit maintenant le nom du menu sur lequel on a cliqué
def afficher_utilisateurs(vue_selectionnee="Utilisateurs connectés"):
    db = SessionLocal()

    # ==========================================
    # VUE 1 : GESTION DES UTILISATEURS
    # ==========================================
    if vue_selectionnee == "Utilisateurs connectés":
        st.subheader("🔐 Gestion des Comptes et Utilisateurs")
        st.info("Ici, vous pouvez créer et gérer les accès du personnel au logiciel.")
        
        # --- CRÉATION DE COMPTE ---
        with st.form("form_ajout_user", clear_on_submit=True):
            st.markdown("### Créer un nouveau compte")
            col1, col2 = st.columns(2)
            
            with col1:
                username = st.text_input("Nom d'utilisateur (Identifiant) *")
                role = st.selectbox("Rôle de l'utilisateur", ["Admin", "Direction", "Comptabilité", "Enseignant"])
            with col2:
                password = st.text_input("Mot de passe *", type="password")
                confirm_password = st.text_input("Confirmer le mot de passe *", type="password")

            submit = st.form_submit_button("Créer le compte", type="primary")

            if submit:
                if username.strip() and password:
                    if password == confirm_password:
                        existe = db.query(Utilisateur).filter(Utilisateur.nom_utilisateur == username.strip()).first()
                        if existe:
                            st.error("Ce nom d'utilisateur existe déjà !")
                        else:
                            nouvel_user = Utilisateur(
                                nom_utilisateur=username.strip(),
                                mot_de_passe=hash_password(password),
                                role=role,
                                actif=True
                            )
                            db.add(nouvel_user)
                            db.commit()
                            st.success(f"✅ Compte '{username}' créé avec succès ({role}) !")
                            st.rerun()
                    else:
                        st.error("❌ Les mots de passe ne correspondent pas.")
                else:
                    st.error("⚠️ Veuillez remplir tous les champs obligatoires.")

        st.markdown("---")

        # --- LISTE DES UTILISATEURS ---
        st.markdown("### Comptes existants")
        utilisateurs = db.query(Utilisateur).all()

        if utilisateurs:
            donnees = []
            for u in utilisateurs:
                donnees.append({
                    "Identifiant": u.nom_utilisateur,
                    "Rôle": u.role,
                    "Statut": "✅ Actif" if u.actif else "❌ Suspendu"
                })
                
            st.dataframe(pd.DataFrame(donnees), use_container_width=True, hide_index=True)

            with st.expander("🗑️ Révoquer / Supprimer un compte"):
                options_users = {f"{u.nom_utilisateur} ({u.role})": u for u in utilisateurs if u.nom_utilisateur != "admin_master"}
                
                if options_users:
                    user_a_suppr = st.selectbox("Sélectionnez l'utilisateur à supprimer :", options_users.keys())
                    if st.button("Confirmer la suppression", type="primary"):
                        db.delete(options_users[user_a_suppr])
                        db.commit()
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
        st.info("Ce tableau retrace les dernières connexions et actions effectuées sur le logiciel.")
        
        logs = db.query(LogActivite).order_by(LogActivite.id.desc()).limit(100).all()
        
        if logs:
            donnees_logs = []
            for log in logs:
                donnees_logs.append({
                    "Date & Heure": log.date_heure,
                    "Utilisateur": log.utilisateur.nom_utilisateur if log.utilisateur else "Système",
                    "Action": log.action,
                    "Détails": log.details if log.details else "-"
                })
            
            df_logs = pd.DataFrame(donnees_logs)
            st.dataframe(df_logs, use_container_width=True, hide_index=True)
        else:
            st.warning("📭 Le journal d'activité est actuellement vide. (Les connexions s'afficheront ici une fois le système finalisé).")

    db.close()
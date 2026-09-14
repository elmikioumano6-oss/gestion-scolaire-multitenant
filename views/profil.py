import streamlit as st
import bcrypt
from database.db_config import SessionLocal
from database.models import User
from database.audit import log_action_erp

def afficher_profil():
    st.subheader("👤 Mon Profil Utilisateur")
    st.markdown("Gestion et mise à jour de vos informations personnelles et de vos paramètres de sécurité.")
    st.markdown("---")

    username = st.session_state.get("username")
    if not username:
        st.warning("⚠️ Veuillez vous connecter pour accéder à cette section.")
        return

    db = SessionLocal()
    try:
        utilisateur = db.query(User).filter(User.username == username).first()

        if not utilisateur:
            st.error("Établissement ou profil utilisateur introuvable en base de données.")
            return

        st.markdown("### Informations du compte")

        col1, col2 = st.columns(2)
        col1.text_input("Nom d'utilisateur", value=utilisateur.username, disabled=True)
        col2.text_input("Rôle", value=getattr(utilisateur, 'role', 'Utilisateur'), disabled=True)

        with st.form("form_update_profil"):
            nom_complet_actuel = getattr(utilisateur, 'nom_complet', '') or ''
            nom_complet = st.text_input("Nom complet / Libellé", value=nom_complet_actuel)
            nouveau_mdp = st.text_input("Nouveau mot de passe (laisser vide pour ne pas changer)", type="password")
            confirmer_mdp = st.text_input("Confirmer le nouveau mot de passe", type="password")

            submit = st.form_submit_button("Mettre à jour le profil", type="primary")

            if submit:
                if nouveau_mdp.strip():
                    if len(nouveau_mdp.strip()) < 6:
                        st.error("⚠️ Le nouveau mot de passe doit contenir au moins 6 caractères.")
                    elif nouveau_mdp.strip() != confirmer_mdp.strip():
                        st.error("⚠️ Les mots de passe saisis ne correspondent pas.")
                    else:
                        try:
                            if hasattr(utilisateur, 'nom_complet'):
                                utilisateur.nom_complet = nom_complet.strip()
                            
                            hashed = bcrypt.hashpw(nouveau_mdp.strip().encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
                            if hasattr(utilisateur, 'password'):
                                utilisateur.password = hashed
                            elif hasattr(utilisateur, 'password_hash'):
                                utilisateur.password_hash = hashed

                            db.commit()

                            log_action_erp(
                                school_id=getattr(utilisateur, 'school_id', 1),
                                module="Mon Profil",
                                action=f"Mise à jour du profil et du mot de passe pour {utilisateur.username}",
                                statut="Succès",
                                valeur_avant="Anciennes informations de profil",
                                valeur_apres="Profil mis à jour"
                            )

                            st.success("✅ Profil mis à jour avec succès !")
                            st.rerun()
                        except Exception as e:
                            db.rollback()
                            st.error(f"Erreur lors de la mise à jour : {e}")
                else:
                    try:
                        if hasattr(utilisateur, 'nom_complet'):
                            utilisateur.nom_complet = nom_complet.strip()
                        db.commit()

                        log_action_erp(
                            school_id=getattr(utilisateur, 'school_id', 1),
                            module="Mon Profil",
                            action=f"Mise à jour des informations de profil pour {utilisateur.username}",
                            statut="Succès",
                            valeur_avant="Ancien nom",
                            valeur_apres=nom_complet.strip()
                        )

                        st.success("✅ Informations de profil mises à jour avec succès !")
                        st.rerun()
                    except Exception as e:
                        db.rollback()
                        st.error(f"Erreur lors de la mise à jour : {e}")

    finally:
        db.close()

# Alias de compatibilité exhaustive pour le routeur
afficher_profil = afficher_profil
afficher_mon_profil = afficher_profil
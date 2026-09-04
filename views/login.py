import streamlit as st
import bcrypt
from database.db_config import SessionLocal
from database.models import User, School

def afficher_login():
    # Style épuré pour la page de connexion
    st.markdown(
        """
        <style>
            [data-testid="stSidebar"] { display: none !important; }
            .login-container {
                max-width: 450px;
                margin: 0 auto;
                padding: 2rem;
                background-color: #ffffff;
                border-radius: 10px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><h1 style='text-align: center; color: #C5A059;'>🏫 Gestion Scolaire Pro</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #6c757d; margin-bottom: 2rem;'>Plateforme Multi-Tenant de Gestion Scolaire</p>", unsafe_allow_html=True)

        # --- ÉTAPE 1 : INTERCEPTION DU CHANGEMENT DE MOT DE PASSE OBLIGATOIRE ---
        if st.session_state.get("pending_password_change", False):
            st.warning("🔒 Sécurité Obligatoire de Première Connexion")
            st.markdown("Vous êtes connecté avec un mot de passe provisoire. Veuillez définir votre nouveau mot de passe personnel.")
            
            with st.form("form_change_mdp_provisoire"):
                nouveau_p = st.text_input("Nouveau mot de passe (6 caractères min.)", type="password")
                confirme_p = st.text_input("Confirmer le nouveau mot de passe", type="password")
                submit_chg = st.form_submit_button("Enregistrer mon nouveau mot de passe", use_container_width=True)
                
                if submit_chg:
                    if len(nouveau_p) < 6:
                        st.error("⚠️ Le mot de passe doit contenir au moins 6 caractères.")
                    elif nouveau_p != confirme_p:
                        st.error("⚠️ Les mots de passe ne correspondent pas.")
                    else:
                        db = SessionLocal()
                        try:
                            username_cible = st.session_state.get("pending_username")
                            user_obj = db.query(User).filter(User.username == username_cible).first()
                            if user_obj:
                                salt = bcrypt.gensalt()
                                user_obj.password = bcrypt.hashpw(nouveau_p.encode('utf-8'), salt).decode('utf-8')
                                user_obj.changer_mdp_requis = False
                                db.commit()
                                
                                # Nettoyage de l'état temporaire et connexion définitive
                                st.session_state["authenticated"] = True
                                st.session_state["username"] = user_obj.username
                                role_db = str(user_obj.role or "").strip().lower()
                                st.session_state["role"] = role_db
                                st.session_state["school_id"] = user_obj.school_id
                                st.session_state["is_super_admin"] = (role_db == "super_admin")
                                
                                if user_obj.school_id:
                                    ecole = db.query(School).filter(School.id == user_obj.school_id).first()
                                    st.session_state["school_name"] = ecole.nom if ecole else "Gestion Scolaire Pro"
                                else:
                                    st.session_state["school_name"] = "Plateforme Globale"
                                
                                del st.session_state["pending_password_change"]
                                del st.session_state["pending_username"]
                                
                                st.success("✅ Mot de passe mis à jour avec succès ! Accès à la plateforme...")
                                st.rerun()
                        except Exception as e:
                            db.rollback()
                            st.error(f"Erreur lors de la mise à jour : {e}")
                        finally:
                            db.close()
            return

        # --- ÉTAPE 2 : FORMULAIRE DE CONNEXION CLASSIQUE ---
        with st.form("form_connexion_pro"):
            st.markdown("### Connexion à votre espace")
            username_input = st.text_input("Identifiant")
            password_input = st.text_input("Mot de passe", type="password")
            
            submitted = st.form_submit_button("Se connecter", use_container_width=True)
            
            if submitted:
                if not username_input.strip() or not password_input.strip():
                    st.error("⚠️ Veuillez renseigner l'identifiant et le mot de passe.")
                else:
                    db = SessionLocal()
                    try:
                        user = db.query(User).filter(User.username == username_input.strip()).first()
                        
                        password_valid = False
                        if user and user.password:
                            try:
                                # Vérification standard bcrypt sécurisée
                                password_valid = bcrypt.checkpw(password_input.encode('utf-8'), user.password.encode('utf-8'))
                            except ValueError:
                                # Fallback de secours si l'ancien hachage en base était corrompu ou en clair
                                if user.password == password_input:
                                    salt = bcrypt.gensalt()
                                    user.password = bcrypt.hashpw(password_input.encode('utf-8'), salt).decode('utf-8')
                                    db.commit()
                                    password_valid = True

                        if user and password_valid:
                            # Vérification du statut actif de l'école (sauf pour super_admin)
                            role_db = str(user.role or "").strip().lower()
                            is_super = (role_db == "super_admin")
                            
                            if user.school_id and not is_super:
                                ecole = db.query(School).filter(School.id == user.school_id).first()
                                if ecole and not getattr(ecole, 'actif', True):
                                    st.error(f"⛔ L'établissement '{ecole.nom}' a été suspendu.")
                                    db.close()
                                    return

                            # 🔒 INTERCEPTION ICI SI LE CHANGEMENT EST REQUIS
                            if getattr(user, 'changer_mdp_requis', False):
                                st.session_state["pending_password_change"] = True
                                st.session_state["pending_username"] = user.username
                                db.close()
                                st.rerun()

                            # Connexion normale
                            st.session_state["authenticated"] = True
                            st.session_state["username"] = user.username
                            st.session_state["role"] = role_db
                            st.session_state["school_id"] = user.school_id
                            st.session_state["is_super_admin"] = is_super
                            
                            if user.school_id:
                                ecole = db.query(School).filter(School.id == user.school_id).first()
                                st.session_state["school_name"] = ecole.nom if ecole else "Gestion Scolaire Pro"
                            else:
                                st.session_state["school_name"] = "Plateforme Globale"

                            st.success("✅ Connexion réussie ! Chargement...")
                            st.rerun()
                        else:
                            st.error("⛔ Identifiant ou mot de passe incorrect.")
                    finally:
                        db.close()
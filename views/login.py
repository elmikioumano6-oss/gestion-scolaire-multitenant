import streamlit as st
from database.db_config import SessionLocal
from database.models import User, School, ActivityLog
from datetime import datetime
import bcrypt

def afficher_login():
    st.markdown("<h2 style='text-align: center; color: #C5A059;'>🔐 Connexion à la Plateforme Scolaire</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Veuillez vous identifier ou modifier votre mot de passe provisoire.</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        # Création de deux onglets sur la page de connexion
        tab_connexion, tab_changement = st.tabs(["🔐 Connexion", "🔑 Modifier mon mot de passe (1ère connexion)"])
        
        with tab_connexion:
            with st.form("form_login"):
                username = st.text_input("Identifiant ou Nom d'utilisateur")
                password = st.text_input("Mot de passe", type="password")
                submitted = st.form_submit_button("Se connecter", use_container_width=True)
                
                if submitted:
                    if not username or not password:
                        st.error("⚠️ Veuillez remplir tous les champs.")
                    else:
                        db = SessionLocal()
                        try:
                            user = db.query(User).filter(User.username == username.strip()).first()
                            if user:
                                pwd_match = False
                                try:
                                    pwd_match = bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8'))
                                except Exception:
                                    pwd_match = (user.password == password)
                                    
                                if pwd_match:
                                    # Enregistrement du log de connexion
                                    try:
                                        nouveau_log = ActivityLog(
                                            school_id=user.school_id,
                                            timestamp=datetime.utcnow(),
                                            username=user.username,
                                            action="Connexion à la plateforme",
                                            module="Authentification",
                                            statut="Succès"
                                        )
                                        db.add(nouveau_log)
                                        db.commit()
                                    except Exception:
                                        db.rollback()

                                    st.session_state["authenticated"] = True
                                    st.session_state["username"] = user.username
                                    st.session_state["role"] = str(user.role).strip().lower()
                                    st.session_state["school_id"] = user.school_id
                                    st.session_state["is_super_admin"] = (str(user.role).strip().lower() == "super_admin")
                                    
                                    if user.school_id:
                                        ecole = db.query(School).filter(School.id == user.school_id).first()
                                        st.session_state["school_name"] = ecole.nom if ecole else "Établissement"
                                    else:
                                        st.session_state["school_name"] = "Plateforme Globale"
                                        
                                    st.success("✅ Connexion réussie ! Redirection...")
                                    st.rerun()
                                else:
                                    st.error("❌ Mot de passe incorrect.")
                            else:
                                st.error("❌ Aucun utilisateur trouvé avec cet identifiant.")
                        finally:
                            db.close()

        with tab_changement:
            st.markdown("#### 🔑 Changement du mot de passe provisoire")
            st.markdown("Entrez votre identifiant et votre mot de passe actuel (provisoire), puis définissez votre nouveau mot de passe personnel de manière sécurisée.")
            
            with st.form("form_change_pwd_login"):
                c_username = st.text_input("Identifiant", key="c_user")
                c_old_pwd = st.text_input("Mot de passe actuel (ou provisoire)", type="password", key="c_old")
                c_new_pwd = st.text_input("Nouveau mot de passe (6 caractères min.)", type="password", key="c_new")
                c_conf_pwd = st.text_input("Confirmer le nouveau mot de passe", type="password", key="c_conf")
                c_submitted = st.form_submit_button("Modifier mon mot de passe", use_container_width=True)
                
                if c_submitted:
                    if not c_username or not c_old_pwd or not c_new_pwd or not c_conf_pwd:
                        st.error("⚠️ Veuillez remplir tous les champs.")
                    elif len(c_new_pwd) < 6:
                        st.error("⚠️ Le nouveau mot de passe doit contenir au moins 6 caractères.")
                    elif c_new_pwd != c_conf_pwd:
                        st.error("⚠️ Les mots de passe ne correspondent pas.")
                    else:
                        db = SessionLocal()
                        try:
                            user_to_mod = db.query(User).filter(User.username == c_username.strip()).first()
                            if user_to_mod:
                                old_match = False
                                try:
                                    old_match = bcrypt.checkpw(c_old_pwd.encode('utf-8'), user_to_mod.password.encode('utf-8'))
                                except Exception:
                                    old_match = (user_to_mod.password == c_old_pwd)
                                    
                                if old_match:
                                    user_to_mod.password = bcrypt.hashpw(c_new_pwd.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                                    user_to_mod.changer_mdp_requis = False
                                    db.commit()
                                    st.success("✅ Mot de passe modifié avec succès ! Vous pouvez maintenant basculer sur l'onglet 'Connexion' pour vous connecter.")
                                else:
                                    st.error("❌ Le mot de passe actuel est incorrect.")
                            else:
                                st.error("❌ Identifiant introuvable.")
                        except Exception as ex:
                            db.rollback()
                            st.error(f"Erreur lors de la modification : {ex}")
                        finally:
                            db.close()
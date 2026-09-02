import streamlit as st
from database.db_config import SessionLocal
from database.models import User, School
import bcrypt

def afficher_login():
    st.markdown("<h2 style='text-align: center; color: #C5A059;'>🔐 Connexion à la Plateforme Scolaire</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Veuillez vous identifier pour accéder à votre espace sécurisé.</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
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
                        user = db.query(User).filter(User.username == username).first()
                        if user:
                            # Vérification du mot de passe (haché bcrypt ou correspondance directe de secours)
                            pwd_match = False
                            try:
                                pwd_match = bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8'))
                            except Exception:
                                pwd_match = (user.password == password)
                                
                            if pwd_match:
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
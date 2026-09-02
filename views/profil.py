import streamlit as st
from database.db_config import SessionLocal
from database.models import Utilisateur

def afficher_profil():
    st.subheader("👤 Mon Profil Utilisateur")
    
    db = SessionLocal()
    
    # Pour l'instant, on récupère par défaut le premier utilisateur ou un profil générique si non connecté dynamiquement
    utilisateur = db.query(Utilisateur).first()
    
    if not utilisateur:
        st.warning("Aucun utilisateur trouvé dans la base de données. Veuillez en créer un dans Administration > Utilisateurs.")
        db.close()
        return

    st.markdown("### Informations du compte")
    
    col1, col2 = st.columns(2)
    col1.text_input("Nom d'utilisateur", value=utilisateur.username, disabled=True)
    col2.text_input("Rôle", value=utilisateur.role, disabled=True)
    
    with st.form("form_update_profil"):
        nom_complet = st.text_input("Nom complet", value=utilisateur.nom_complet)
        nouveau_mdp = st.text_input("Nouveau mot de passe (laisser vide pour ne pas changer)", type="password")
        
        submit = st.form_submit_button("Mettre à jour le profil")
        
        if submit:
            try:
                utilisateur.nom_complet = nom_complet.strip()
                if nouveau_mdp.strip():
                    utilisateur.password_hash = nouveau_mdp.strip()
                db.commit()
                st.success("Profil mis à jour avec succès !")
                st.rerun()
            except Exception as e:
                db.rollback()
                st.error(f"Erreur lors de la mise à jour : {e}")
                
    db.close()
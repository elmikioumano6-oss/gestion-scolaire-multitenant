import streamlit as st
import pandas as pd
from database.db_config import SessionLocal
from database.models import User, School

def afficher_gestion_utilisateurs():
    st.subheader("👥 Gestion des Comptes Utilisateurs & Rôles")
    st.markdown("Administration des accès et des rôles du personnel avec isolation multi-tenant stricte.")
    st.markdown("---")

    school_id = st.session_state.get("school_id")
    is_super_admin = st.session_state.get("is_super_admin", False)
    
    # Récupération dynamique du nom de l'école active
    db = SessionLocal()
    try:
        if school_id:
            ecole_courante = db.query(School).filter(School.id == school_id).first()
            school_name = ecole_courante.nom if ecole_courante else st.session_state.get("school_name", "Établissement")
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
        tab1, tab2 = st.tabs(["📋 Liste des Utilisateurs", "➕ Nouvel Utilisateur"])

        with tab1:
            st.markdown(f"### Utilisateurs Actifs — **{school_name} ({cycle_en_cours})**")
            query = db.query(User)
            if not is_super_admin and school_id:
                query = query.filter(User.school_id == school_id)
            users = query.all()

            if not users:
                st.info("Aucun compte utilisateur enregistré pour le moment dans cet établissement.")
            else:
                data_users = []
                for u in users:
                    data_users.append({
                        "Nom d'utilisateur": getattr(u, 'username', 'Utilisateur'),
                        "Rôle / Fonction": getattr(u, 'role', 'Personnel'),
                        "Dernière activité": str(getattr(u, 'derniere_activite', '—'))
                    })
                df_users = pd.DataFrame(data_users)
                st.dataframe(df_users, use_container_width=True)

        with tab2:
            st.markdown(f"### Création d'un Compte Local — **{school_name} ({cycle_en_cours})**")
            with st.form("form_add_compte"):
                col1, col2 = st.columns(2)
                with col1:
                    username = st.text_input("Nom d'utilisateur (Login)")
                    password = st.text_input("Mot de passe initial", type="password")
                with col2:
                    role = st.selectbox("Rôle / Fonction", ["proviseur", "censeur", "surveillant", "comptable", "enseignant"])

                submitted = st.form_submit_button("Créer le compte utilisateur")
                if submitted:
                    if not username or not password:
                        st.error("⚠️ Veuillez remplir le nom d'utilisateur et le mot de passe.")
                    else:
                        target_school_id = school_id
                        if is_super_admin and not target_school_id:
                            ecole_defaut = db.query(School).first()
                            target_school_id = ecole_defaut.id if ecole_defaut else 1

                        nouveau_compte = User(
                            school_id=target_school_id,
                            username=username.strip(),
                            password=password,
                            role=role
                        )
                        db.add(nouveau_compte)
                        db.commit()
                        st.success(f"✅ Le compte de '{username}' a été créé avec succès pour **{school_name}** !")
                        st.rerun()

    finally:
        db.close()

# Alias de compatibilité complète pour le routeur
afficher_gestion_comptes = afficher_gestion_utilisateurs
afficher_gestion_des_comptes = afficher_gestion_utilisateurs
afficher_comptes = afficher_gestion_utilisateurs
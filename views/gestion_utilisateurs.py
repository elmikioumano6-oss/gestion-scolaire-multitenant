from datetime import datetime, timedelta
import urllib.parse
import random
import string
import bcrypt
from database.audit import log_action_erp
from database.db_config import SessionLocal
from database.models import Enseignant, Eleve, School, User
import pandas as pd
import streamlit as st


def afficher_gestion_utilisateurs():
    st.subheader("👥 Gestion des Comptes Utilisateurs & Rôles")
    st.markdown(
        "Administration sécurisée des accès, des comptes et des rôles du"
        " personnel avec isolation multi-tenant stricte et suivi des statuts en"
        " temps réel."
    )
    st.markdown("---")

    school_id = st.session_state.get("school_id")
    is_super_admin = st.session_state.get("is_super_admin", False)
    username_connecte = st.session_state.get("username", "")

    db = SessionLocal()
    try:
        # --- MISE À JOUR AUTOMATIQUE DE LA DERNIÈRE ACTIVITÉ ---
        if username_connecte:
            user_actif_session = db.query(User).filter(User.username == username_connecte).first()
            if user_actif_session and hasattr(user_actif_session, "derniere_activite"):
                user_actif_session.derniere_activite = datetime.now()
                db.commit()

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
        user_obj_connecte = db.query(User).filter(User.username == username_connecte).first()
        user_role_connecte = getattr(user_obj_connecte, "role", "").lower() if user_obj_connecte else ""
        
        is_school_admin = user_role_connecte in [
            "admin",
            "directeur",
            "fondateur",
            "proviseur",
        ] or "admin" in username_connecte.lower()

        tab_liste, tab_ajout = st.tabs([
            "📋 Liste des Utilisateurs",
            "➕ Nouvel Utilisateur",
        ])

        with tab_liste:
            st.markdown(
                f"### Utilisateurs Actifs — **{school_name} ({cycle_en_cours})**"
            )

            users_query = db.query(User)
            if is_super_admin:
                pass
            elif school_id:
                users_query = users_query.filter(
                    User.school_id == school_id,
                    User.role != "super_admin"
                )

            utilisateurs_db = users_query.all()
            if not utilisateurs_db:
                st.info("Aucun utilisateur enregistré dans cet établissement.")
            else:
                data_u = []
                noms_vus = set()
                maintenant = datetime.now()

                for u in utilisateurs_db:
                    if u.username not in noms_vus:
                        noms_vus.add(u.username)

                        statut_connexion = "🔴 Hors ligne"
                        if hasattr(u, "derniere_activite") and u.derniere_activite:
                            diff = maintenant - u.derniere_activite
                            if diff < timedelta(minutes=5):
                                statut_connexion = "🟢 En ligne"

                        data_u.append({
                            "Nom d'utilisateur": u.username,
                            "Rôle / Fonction": getattr(u, "role", "N/D"),
                            "Statut Actuel": statut_connexion,
                            "Mot de passe à changer": (
                                "Oui" if getattr(u, "changer_mdp_requis", False) else "Non"
                            ),
                        })

                df_users = pd.DataFrame(data_u)
                st.dataframe(df_users, use_container_width=True)

                # --- SECTION DE SUPPRESSION MULTI-TENANT SÉCURISÉE ---
                if is_school_admin or is_super_admin:
                    st.markdown("---")
                    st.markdown("### 🗑 Supprimer un utilisateur")
                    
                    usernames_disponibles = [u.username for u in utilisateurs_db if u.username != username_connecte]
                    
                    if usernames_disponibles:
                        user_a_supprimer = st.selectbox("Sélectionner l'utilisateur à supprimer", usernames_disponibles, key="select_suppr_user_multitenant")
                        if st.button("❌ Supprimer définitivement", type="primary"):
                            user_obj_del = db.query(User).filter(User.username == user_a_supprimer).first()
                            if user_obj_del:
                                db.query(Eleve).filter(Eleve.parent_id == user_obj_del.id).update({Eleve.parent_id: None})
                                db.delete(user_obj_del)
                                db.commit()
                                st.success(f"L'utilisateur {user_a_supprimer} a été supprimé avec succès !")
                                st.rerun()
                    else:
                        st.info("Aucun autre utilisateur disponible à la suppression.")

        with tab_ajout:
            st.markdown(
                f"### Création d'un Nouveau Compte Utilisateur — **{school_name}**"
            )

            if "temp_gen_pwd" not in st.session_state:
                st.session_state["temp_gen_pwd"] = ""

            col_g1, col_g2 = st.columns([3, 1])
            with col_g2:
                if st.button("🎲 Générer un MDP sécurisé"):
                    chars = string.ascii_letters + string.digits + "@#$%&!"
                    st.session_state["temp_gen_pwd"] = "".join(
                        random.choice(chars) for _ in range(8)
                    )
                    st.rerun()

            # Utilisation d'un formulaire explicite st.form et st.form_submit_button
            with st.form("form_creation_utilisateur_admin"):
                col1, col2 = st.columns(2)
                with col1:
                    nouveau_user = st.text_input("Nom d'utilisateur (Identifiant)")
                    mot_de_passe = st.text_input(
                        "Mot de passe provisoire",
                        value=st.session_state["temp_gen_pwd"],
                        type="password",
                    )
                with col2:
                    role_options = {
                        "fondateur": "Fondateur / Propriétaire",
                        "directeur": "Directeur / Administrateur",
                        "proviseur": "Proviseur / Direction Secondaire",
                        "censeur": "Censeur des Études",
                        "enseignant": "Enseignant / Professeur",
                        "econome": "Économe / Finances",
                        "surveillant": "Surveillant Général",
                        "inspecteur": "Inspecteur",
                        "parent": "Parent d'élève",
                    }
                    role_attribue = st.selectbox(
                        "Rôle / Fonction", options=list(role_options.keys())
                    )
                    cycle_associe = st.selectbox(
                        "Cycle d'affectation",
                        ["Collège", "Lycée", "Tous les cycles"],
                        index=0 if cycle_en_cours == "Collège" else (1 if cycle_en_cours == "Lycée" else 2)
                    )

                role_descriptions = {
                    "fondateur": "Supervision stratégique globale, accès illimité à l'administration et aux finances de l'établissement.",
                    "directeur": "Accès complet à la gestion administrative, financière et aux paramètres de l'école.",
                    "proviseur": "Supervision globale du cycle secondaire, pilotage pédagogique et validation des décisions.",
                    "censeur": "Gestion des emplois du temps, des notes, des cahiers de textes et de la discipline.",
                    "enseignant": "Saisie des notes, émargement du cahier de texte et suivi de classe.",
                    "econome": "Gestion de la trésorerie, encaissements de scolarité et suivi des dépenses.",
                    "surveillant": "Gestion des absences, retours de discipline et cahier de correspondance.",
                    "inspecteur": "Supervision pédagogique, apposition de visas et audit des notes.",
                    "parent": "Accès restreint au portail famille pour le suivi exclusif de l'enfant.",
                }
                st.markdown(
                    f"<div style='background-color: rgba(217, 119, 6, 0.1); padding: 8px 12px; border-radius: 6px; border-left: 3px solid #D97706; font-size: 0.85rem; color: #E2E8F0; margin-bottom: 10px;'>ℹ <b>Permission :</b> {role_descriptions.get(role_attribue, 'Accès standard')}</div>",
                    unsafe_allow_html=True,
                )

                # --- ASSOCIATION SI RÔLE == PARENT ---
                eleves_associes_ids = []
                if role_attribue == "parent":
                    st.markdown("#### 🔗 Association des enfants")
                    
                    eleves_query = db.query(Eleve).filter(
                        Eleve.school_id == (school_id or 1),
                        Eleve.deleted_at.is_(None)
                    )
                    if cycle_associe != "Tous les cycles":
                        eleves_query = eleves_query.filter(Eleve.cycle == cycle_associe)
                    
                    tous_les_eleves = eleves_query.all()
                    
                    options_eleves_form = {f"{e.nom} {e.prenom} (Matricule: {e.matricule})": e.id for e in tous_les_eleves}
                    if options_eleves_form:
                        choix_eleves_form = st.multiselect("Sélectionner le ou les enfants concernés *", list(options_eleves_form.keys()))
                        eleves_associes_ids = [options_eleves_form[nom] for nom in choix_eleves_form]

                submitted_user = st.form_submit_button("💾 Enregistrer le compte", type="primary")

                if submitted_user:
                    if not nouveau_user.strip() or not mot_de_passe.strip():
                        st.error("⚠️ Le nom d'utilisateur et le mot de passe sont obligatoires.")
                    else:
                        existing_user = db.query(User).filter(User.username == nouveau_user.strip()).first()
                        if existing_user:
                            st.error(f"⚠️ Un utilisateur avec le nom '{nouveau_user.strip()}' existe déjà.")
                        else:
                            try:
                                hashed_pwd = bcrypt.hashpw(mot_de_passe.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                                nouvel_u = User(
                                    username=nouveau_user.strip(),
                                    password=hashed_pwd,
                                    role=role_attribue,
                                    school_id=school_id or 1,
                                    changer_mdp_requis=True
                                )
                                db.add(nouvel_u)
                                db.commit()

                                log_action_erp(
                                    module="Gestion Comptes",
                                    action=f"Création du compte {nouveau_user.strip()} ({role_attribue})",
                                    statut="Succès",
                                    valeur_avant="Inexistant",
                                    valeur_apres=f"Rôle: {role_attribue}",
                                )

                                st.success(f"✅ Le compte de **{nouveau_user.strip()}** a été créé avec succès !")
                                if "temp_gen_pwd" in st.session_state:
                                    st.session_state["temp_gen_pwd"] = ""
                            except Exception as ex:
                                db.rollback()
                                st.error(f"Erreur lors de la création du compte : {ex}")

    except Exception as e:
        db.rollback()
        st.error(f"Une erreur est survenue lors du chargement de la gestion des utilisateurs : {e}")
    finally:
        db.close()
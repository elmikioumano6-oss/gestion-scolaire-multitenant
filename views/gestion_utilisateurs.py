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

    db = SessionLocal()
    try:
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
                f"<div style='background-color: rgba(217, 119, 6, 0.1); padding: 8px 12px; border-radius: 6px; border-left: 3px solid #D97706; font-size: 0.85rem; color: #E2E8F0; margin-bottom: 10px;'>ℹ️ <b>Permission :</b> {role_descriptions.get(role_attribue, 'Accès standard')}</div>",
                unsafe_allow_html=True,
            )

            # --- ASSOCIATION SI RÔLE == PARENT ---
            eleves_associes_ids = []
            if role_attribue == "parent":
                st.markdown("#### 🔗 Association des enfants")
                
                # Filtrage dynamique des élèves selon le cycle sélectionné
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
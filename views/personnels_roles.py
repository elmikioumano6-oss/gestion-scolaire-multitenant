from datetime import datetime
from database.audit import log_action_erp
from database.db_config import SessionLocal
from database.models import ActivityLog, Eleve, School, User
import pandas as pd
import streamlit as st


def afficher_personnels():
    st.subheader("👥 Gestion du Personnel & RH")
    st.markdown(
        "Annuaire, suivi administratif et gestion des éléments salariaux du personnel."
    )
    st.markdown("---")

    school_id = st.session_state.get("school_id")
    is_super_admin = st.session_state.get("is_super_admin", False)

    db = SessionLocal()
    try:
        target_school_id = school_id
        if is_super_admin and not target_school_id:
            ecole_defaut = db.query(School).first()
            target_school_id = ecole_defaut.id if ecole_defaut else 1

        ecole_active_id = school_id if school_id else target_school_id

        ecole_courante = (
            db.query(School).filter(School.id == ecole_active_id).first()
        )
        school_name = (
            ecole_courante.nom
            if ecole_courante
            else st.session_state.get("school_name", "Établissement")
        )
    finally:
        db.close()

    cycle_en_cours = st.session_state.get("cycle_actif", "Collège")

    if not school_id and not is_super_admin:
        st.warning("⚠️ Veuillez vous connecter pour accéder à cette section.")
        return

    db = SessionLocal()
    try:
        tab_annuaire, tab_ajout = st.tabs([
            "📋 Annuaire & Paie du Personnel",
            "➕ Enregistrer un Agent",
        ])

        with tab_annuaire:
            st.markdown(
                f"### Liste du personnel — **{school_name} ({cycle_en_cours})**"
            )

            # Filtrage strict : Exclusion des enseignants pour les séparer du module Enseignants
            users_query = db.query(User).filter(
                User.school_id == ecole_active_id,
                User.role != "super_admin",
                User.role != "enseignant",
                User.enseignant_id.is_(None)
            )
            if hasattr(User, "deleted_at"):
                users_query = users_query.filter(User.deleted_at.is_(None))
            personnel_list = users_query.all()

            if not personnel_list:
                st.info("Aucun membre du personnel administratif enregistré pour cet établissement.")
            else:
                cols = st.columns([2, 1.5, 2, 2, 1.2])
                cols[0].markdown("**Nom / Agent**")
                cols[1].markdown("**Poste**")
                cols[2].markdown("**Salaire de Base (FCFA)**")
                cols[3].markdown("**Primes Fixes (FCFA)**")
                cols[4].markdown("**Actions**")
                st.markdown("---")

                for p in personnel_list:
                    c = st.columns([2, 1.5, 2, 2, 1.2])
                    c[0].write(f"👤 **{getattr(p, 'username', 'N/A')}**")
                    c[1].markdown(f"`{getattr(p, 'role', 'agent')}`")
                    
                    with c[2]:
                        nouveau_salaire = st.number_input(
                            "Salaire",
                            min_value=0.0,
                            value=float(getattr(p, "salaire_base", 0.0) or 0.0),
                            step=5000.0,
                            key=f"sal_{p.id}",
                            label_visibility="collapsed"
                        )
                    with c[3]:
                        nouvelles_primes = st.number_input(
                            "Primes",
                            min_value=0.0,
                            value=float(getattr(p, "primes_fixes", 0.0) or 0.0),
                            step=1000.0,
                            key=f"prime_{p.id}",
                            label_visibility="collapsed"
                        )

                    with c[4]:
                        col_btn1, col_btn2 = st.columns(2)
                        with col_btn1:
                            if st.button("💾", key=f"btn_save_rh_{p.id}", help="Enregistrer les modifications"):
                                p.salaire_base = nouveau_salaire
                                p.primes_fixes = nouvelles_primes
                                db.commit()
                                st.success(f"Mis à jour !")
                                st.rerun()
                        with col_btn2:
                            if st.button("🗑️", key=f"btn_del_{p.id}", help="Supprimer cet agent"):
                                try:
                                    eleves_lies = db.query(Eleve).filter(Eleve.parent_id == p.id).all()
                                    for eleve in eleves_lies:
                                        eleve.parent_id = None
                                    
                                    db.delete(p)
                                    db.commit()
                                    st.success(f"Supprimé !")
                                    st.rerun()
                                except Exception as e:
                                    db.rollback()
                                    st.error(f"Erreur de suppression : {e}")

                    st.markdown("<hr style='margin: 0.2rem 0; border-color: rgba(255,255,255,0.05);'>", unsafe_allow_html=True)

        with tab_ajout:
            st.markdown(f"### Enregistrement d'un nouvel agent — **{school_name}**")
            with st.form("form_ajout_agent_rh"):
                col_r1, col_r2 = st.columns(2)
                with col_r1:
                    nom_agent = st.text_input("Nom complet / Identifiant de l'agent *")
                    poste_agent = st.selectbox(
                        "Fonction / Poste",
                        [
                            "directeur", "proviseur", "censeur",
                            "comptable", "econome", "surveillant", "secretaire",
                            "planton", "jardinier", "gardien"
                        ]
                    )
                with col_r2:
                    salaire_init = st.number_input("Salaire de base (FCFA)", min_value=0.0, step=5000.0)
                    primes_init = st.number_input("Primes fixes (FCFA)", min_value=0.0, step=1000.0)

                submitted_agent = st.form_submit_button("➕ Ajouter l'agent au personnel", type="primary")
                if submitted_agent:
                    if not nom_agent.strip():
                        st.error("⚠️ Le nom ou l'identifiant de l'agent est obligatoire.")
                    else:
                        doublon = db.query(User).filter(
                            User.username == nom_agent.strip(),
                            User.school_id == ecole_active_id
                        ).first()
                        if doublon:
                            st.error(f"⚠️ Un agent nommé **{nom_agent.strip()}** existe déjà.")
                        else:
                            nouvel_agent = User(
                                school_id=ecole_active_id,
                                username=nom_agent.strip(),
                                password="",
                                role=poste_agent,
                                salaire_base=salaire_init,
                                primes_fixes=primes_init
                            )
                            db.add(nouvel_agent)
                            db.commit()
                            st.success(f"✅ Agent **{nom_agent.strip()}** ajouté avec succès !")
                            st.rerun()

    finally:
        db.close()

# Alias de compatibilité
afficher_personnels_et_roles = afficher_personnels
afficher_personnels_roles = afficher_personnels
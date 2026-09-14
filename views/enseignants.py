from datetime import datetime
from database.audit import log_action_erp
from database.db_config import SessionLocal
from database.models import Classe, Enseignant, Matiere, School
from database.queries import get_classes_cached, get_matieres_cached
import pandas as pd
import streamlit as st


def afficher_enseignants():
    st.subheader("👥 Gestion du Corps Professoral & Enseignants")
    st.markdown(
        "Suivi, administration et affectations pédagogiques des enseignants"
        " rattachés à l'établissement avec traçabilité ERP et archivage (Soft"
        " Delete)."
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
        # Récupération sécurisée des classes et matières de l'école active
        classes_query = db.query(Classe).filter(
            Classe.cycle == cycle_en_cours, Classe.school_id == ecole_active_id
        )
        if hasattr(Classe, "deleted_at"):
            classes_query = classes_query.filter(Classe.deleted_at.is_(None))
        classes_cycle = classes_query.all()

        matieres_query = db.query(Matiere).filter(
            Matiere.cycle == cycle_en_cours, Matiere.school_id == ecole_active_id
        )
        if hasattr(Matiere, "deleted_at"):
            matieres_query = matieres_query.filter(Matiere.deleted_at.is_(None))
        matieres_cycle = matieres_query.all()

        tab_liste, tab_ajout = st.tabs([
            "📋 Liste des Enseignants",
            "➕ Enregistrer un Enseignant",
        ])

        with tab_liste:
            st.markdown(f"### Enseignants Actifs — **{school_name} ({cycle_en_cours})**")

            ens_query = db.query(Enseignant).filter(
                Enseignant.school_id == ecole_active_id
            )
            if hasattr(Enseignant, "deleted_at"):
                ens_query = ens_query.filter(Enseignant.deleted_at.is_(None))
            enseignants = ens_query.all()

            if not enseignants:
                st.info(
                    "Aucun enseignant actif enregistré pour le moment dans cet"
                    " établissement."
                )
            else:
                cols = st.columns([1.5, 1.5, 2, 2, 2])
                cols[0].markdown("**Nom & Prénom**")
                cols[1].markdown("**Contact**")
                cols[2].markdown("**Classes**")
                cols[3].markdown("**Matières**")
                cols[4].markdown("**Actions**")
                st.markdown("---")

                for prof in enseignants:
                    c = st.columns([1.5, 1.5, 2, 2, 2])
                    c[0].write(f"**{prof.nom}** {prof.prenom}")
                    c[1].write(
                        f"📞 {prof.telephone or 'N/D'}\n📧"
                        f" {getattr(prof, 'email', 'N/D')}"
                    )
                    c[2].write(
                        getattr(
                            prof,
                            "classes_attribuees",
                            getattr(prof, "classes", "Aucune"),
                        )
                    )
                    c[3].write(
                        getattr(
                            prof,
                            "matieres_attribuees",
                            getattr(prof, "matieres", "Aucune"),
                        )
                    )

                    btn_col1, btn_col2 = c[4].columns(2)
                    with btn_col1:
                        if st.button("✏️", key=f"edit_prof_{prof.id}", help="Modifier"):
                            st.session_state[f"editing_prof_{prof.id}"] = True
                    with btn_col2:
                        if st.button(
                            "🗑️", key=f"del_prof_{prof.id}", help="Archiver / Supprimer"
                        ):
                            st.session_state[f"deleting_prof_{prof.id}"] = True

                    # --- GESTION DE LA SUPPRESSION / ARCHIVAGE ---
                    if st.session_state.get(f"deleting_prof_{prof.id}", False):
                        st.warning(
                            f"Voulez-vous vraiment archiver **{prof.nom} {prof.prenom}** ?"
                        )
                        col_conf1, col_conf2 = st.columns(2)
                        with col_conf1:
                            if st.button(
                                "Confirmer", key=f"confirm_del_prof_{prof.id}", type="primary"
                            ):
                                if hasattr(prof, "deleted_at"):
                                    prof.deleted_at = datetime.now()
                                    db.commit()
                                else:
                                    db.delete(prof)
                                    db.commit()

                                log_action_erp(
                                    module="Enseignants",
                                    action=(
                                        "Suppression/Archivage du professeur"
                                        f" {prof.nom} {prof.prenom}"
                                    ),
                                    statut="Critique",
                                    valeur_avant="Actif",
                                    valeur_apres="Inactif",
                                )

                                st.success("Enseignant traité avec succès !")
                                st.session_state[f"deleting_prof_{prof.id}"] = False
                                st.rerun()
                        with col_conf2:
                            if st.button("Annuler", key=f"cancel_del_prof_{prof.id}"):
                                st.session_state[f"deleting_prof_{prof.id}"] = False
                                st.rerun()

                    # --- GESTION DE LA MODIFICATION ---
                    if st.session_state.get(f"editing_prof_{prof.id}", False):
                        with st.form(key=f"form_edit_prof_{prof.id}"):
                            st.markdown(
                                f"**Modification de l'enseignant : {prof.nom} {prof.prenom}**"
                            )
                            new_nom = st.text_input("Nom", value=prof.nom)
                            new_prenom = st.text_input("Prénom", value=prof.prenom)
                            new_tel = st.text_input(
                                "Téléphone", value=prof.telephone or ""
                            )
                            new_email = st.text_input(
                                "Adresse Email", value=getattr(prof, "email", "") or ""
                            )

                            classes_str_actuelle = (
                                getattr(
                                    prof,
                                    "classes_attribuees",
                                    getattr(prof, "classes", ""),
                                )
                                or ""
                            )
                            matieres_str_actuelle = (
                                getattr(
                                    prof,
                                    "matieres_attribuees",
                                    getattr(prof, "matieres", ""),
                                )
                                or ""
                            )

                            new_classes = st.text_area(
                                "Classes (séparées par virgule)", value=classes_str_actuelle
                            )
                            new_matieres = st.text_area(
                                "Matières (séparées par virgule)",
                                value=matieres_str_actuelle,
                            )

                            submit_edit = st.form_submit_button(
                                "Enregistrer les modifications", type="primary"
                            )
                            cancel_edit = st.form_submit_button("Annuler")

                            if submit_edit:
                                ancienne_val = (
                                    f"Classes: {classes_str_actuelle} | Matières:"
                                    f" {matieres_str_actuelle}"
                                )
                                nouvelle_val = (
                                    f"Classes: {new_classes} | Matières: {new_matieres}"
                                )

                                prof.nom = new_nom.upper()
                                prof.prenom = new_prenom
                                prof.telephone = new_tel
                                if hasattr(prof, "email"):
                                    prof.email = new_email

                                if hasattr(prof, "classes_attribuees"):
                                    prof.classes_attribuees = new_classes
                                if hasattr(prof, "classes"):
                                    prof.classes = new_classes
                                if hasattr(prof, "matieres_attribuees"):
                                    prof.matieres_attribuees = new_matieres
                                if hasattr(prof, "matieres"):
                                    prof.matieres = new_matieres

                                db.commit()

                                log_action_erp(
                                    module="Enseignants",
                                    action=(
                                        "Modification des affectations de"
                                        f" {new_nom.upper()} {new_prenom}"
                                    ),
                                    statut="Critique",
                                    valeur_avant=ancienne_val,
                                    valeur_apres=nouvelle_val,
                                )

                                st.success(
                                    "Profil enseignant mis à jour et tracé avec succès !"
                                )
                                st.session_state[f"editing_prof_{prof.id}"] = False
                                st.rerun()
                            if cancel_edit:
                                st.session_state[f"editing_prof_{prof.id}"] = False
                                st.rerun()
                    st.markdown(
                        "<hr style='margin: 0.2rem 0; border-color:"
                        " rgba(255,255,255,0.05);'>",
                        unsafe_allow_html=True,
                    )

        with tab_ajout:
            st.markdown(
                f"### Enregistrement d'un Nouvel Enseignant — **{school_name}**"
            )

            if not classes_cycle or not matieres_cycle:
                st.warning(
                    "⚠️ Veuillez d'abord configurer des classes et des matières dans"
                    " les modules correspondants."
                )
            else:
                noms_classes = [c.libelle for c in classes_cycle]
                noms_matieres = [m.libelle if hasattr(m, 'libelle') else getattr(m, 'nom', '') for m in matieres_cycle]

                with st.form("form_enregistrement_enseignant"):
                    col1, col2 = st.columns(2)
                    with col1:
                        nom_prof = st.text_input("Nom de l'enseignant *")
                        email_prof = st.text_input("Adresse Email")
                    with col2:
                        prenom_prof = st.text_input("Prénom de l'enseignant *")
                        tel_prof = st.text_input("Numéro de Téléphone")

                    st.markdown("#### Affectations Pédagogiques")
                    classes_attribuees = st.multiselect(
                        "Classes tenues par l'enseignant", noms_classes
                    )
                    matieres_attribuees = st.multiselect(
                        "Matières dispensées", noms_matieres
                    )

                    submitted_prof = st.form_submit_button(
                        "💾 Enregistrer l'enseignant", type="primary"
                    )
                    if submitted_prof:
                        if not nom_prof.strip() or not prenom_prof.strip():
                            st.error(
                                "⚠️ Le nom et le prénom de l'enseignant sont obligatoires."
                            )
                        else:
                            # Vérification anti-doublon par nom et prénom au sein de l'établissement
                            doublon_existant = (
                                db.query(Enseignant)
                                .filter(
                                    Enseignant.school_id == ecole_active_id,
                                    Enseignant.nom == nom_prof.strip().upper(),
                                    Enseignant.prenom == prenom_prof.strip(),
                                )
                                .first()
                            )
                            if doublon_existant:
                                st.error(
                                    f"⚠️ Un enseignant nommé **{nom_prof.upper()}"
                                    f" {prenom_prof}** est déjà enregistré dans cet"
                                    " établissement."
                                )
                            else:
                                str_classes = (
                                    ", ".join(classes_attribuees)
                                    if classes_attribuees
                                    else "Aucune"
                                )
                                str_matieres = (
                                    ", ".join(matieres_attribuees)
                                    if matieres_attribuees
                                    else "Aucune"
                                )

                                nouvel_enseignant = Enseignant(
                                    school_id=ecole_active_id,
                                    nom=nom_prof.strip().upper(),
                                    prenom=prenom_prof.strip(),
                                    telephone=tel_prof.strip() if tel_prof else None,
                                )

                                if hasattr(nouvel_enseignant, "email"):
                                    nouvel_enseignant.email = (
                                        email_prof.strip() if email_prof else None
                                    )
                                if hasattr(nouvel_enseignant, "classes_attribuees"):
                                    nouvel_enseignant.classes_attribuees = str_classes
                                if hasattr(nouvel_enseignant, "classes"):
                                    nouvel_enseignant.classes = str_classes
                                if hasattr(nouvel_enseignant, "matieres_attribuees"):
                                    nouvel_enseignant.matieres_attribuees = str_matieres
                                if hasattr(nouvel_enseignant, "matieres"):
                                    nouvel_enseignant.matieres = str_matieres

                                db.add(nouvel_enseignant)
                                db.commit()

                                log_action_erp(
                                    module="Enseignants",
                                    action=(
                                        "Enregistrement de l'enseignant :"
                                        f" {nom_prof.strip().upper()}"
                                        f" {prenom_prof.strip()}"
                                    ),
                                    statut="Succès",
                                    valeur_avant="Inexistant",
                                    valeur_apres=(
                                        f"Affecté à {len(classes_attribuees)} classe(s)"
                                    ),
                                )

                                st.success(
                                    f"✅ L'enseignant **{nom_prof.strip().upper()}"
                                    f" {prenom_prof.strip()}** a été enregistré et ses accès"
                                    " tracés !"
                                )
                                st.rerun()

    finally:
        db.close()


# Alias de compatibilité exhaustive
afficher_gestion_enseignants = afficher_enseignants
afficher_enseignants = afficher_enseignants
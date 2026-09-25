from datetime import datetime
import unicodedata
from database.audit import log_action_erp
from database.db_config import SessionLocal
from database.models import Classe, Enseignant, Matiere, School
import pandas as pd
import streamlit as st


# --- Dictionnaire et fonction de normalisation (Logique Espace Enseignant) ---
SYNONYMES_MATIERES = {
    "sciences physiques": "physique chimie",
    "physique chimie": "physique chimie",
    "svt": "science de la vie et de la terre",
    "science de la vie et de la terre": "science de la vie et de la terre",
    "eps": "eps",
    "education physique": "eps",
    "education physique et sportive": "eps",
    "economie familiale": "economie familiale et sociale",
    "economie familiale et sociale": "economie familiale et sociale",
    "economie familiale sociale": "economie familiale et sociale",
    "histoire geographie": "histoire geographie",
    "histoire-geographie": "histoire geographie",
    "education civique": "education civique et morale",
    "education civique et morale": "education civique et morale",
    "education civique morale": "education civique et morale",
    "conduite": "conduite",
}

def normaliser_chaine(texte):
    if not texte or pd.isna(texte):
        return ""
    nfkd = unicodedata.normalize("NFKD", str(texte))
    sans_accent = "".join([c for c in nfkd if not unicodedata.combining(c)])
    nettoye = " ".join(sans_accent.lower().replace("-", " ").replace("_", " ").replace("è", "e").replace("é", " e").split())
    return SYNONYMES_MATIERES.get(nettoye, nettoye)

def get_matieres_dynamiques(selected_classes_labels, classes_cycle, ecole_active_id, cycle_en_cours, db):
    """Récupère, filtre et déduplique les matières selon les classes sélectionnées."""
    m_brutes = []
    
    # 1. Si des classes sont sélectionnées, on filtre par classe_id
    if selected_classes_labels:
        sel_ids = [c.id for c in classes_cycle if c.libelle in selected_classes_labels]
        mat_q = db.query(Matiere).filter(
            Matiere.school_id == ecole_active_id, 
            Matiere.classe_id.in_(sel_ids)
        )
        if hasattr(Matiere, "deleted_at"):
            mat_q = mat_q.filter(Matiere.deleted_at.is_(None))
        m_brutes = mat_q.all()
    else:
        # 2. Logique Espace Enseignant : Si aucune classe sélectionnée, on affiche TOUTES les matières de l'école
        mat_q = db.query(Matiere).filter(Matiere.school_id == ecole_active_id)
        if hasattr(Matiere, "deleted_at"):
            mat_q = mat_q.filter(Matiere.deleted_at.is_(None))
        m_brutes = mat_q.all()
        
    # 3. Fallback sécurité
    if not m_brutes:
        mat_q_cycle = db.query(Matiere).filter(
            Matiere.school_id == ecole_active_id, 
            Matiere.cycle == cycle_en_cours
        )
        if hasattr(Matiere, "deleted_at"):
            mat_q_cycle = mat_q_cycle.filter(Matiere.deleted_at.is_(None))
        m_brutes = mat_q_cycle.all()

    # Déduplication par nom normalisé
    m_dict = {}
    for m in m_brutes:
        n_brut = m.libelle if hasattr(m, "libelle") and m.libelle else getattr(m, "nom", "Matière")
        n_key = normaliser_chaine(n_brut)
        if n_key and n_key not in m_dict:
            m_dict[n_key] = m
            
    return sorted([(m.libelle if hasattr(m, 'libelle') and m.libelle else getattr(m, 'nom', 'Matière')).title() for m in m_dict.values()])
# -------------------------------------------------------------------------


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
        # Récupération sécurisée des classes
        classes_query = db.query(Classe).filter(
            Classe.cycle == cycle_en_cours, Classe.school_id == ecole_active_id
        )
        if hasattr(Classe, "deleted_at"):
            classes_query = classes_query.filter(Classe.deleted_at.is_(None))
        classes_cycle = classes_query.all()

        noms_classes = sorted(list(set([c.libelle.strip() for c in classes_cycle if c.libelle])))

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
            tous_enseignants = ens_query.all()

            # Filtrage par cycle
            noms_classes_cycle = {c.libelle for c in classes_cycle}
            enseignants = []
            for prof in tous_enseignants:
                classes_str = getattr(prof, "classes_attribuees", "") or getattr(prof, "classes", "") or ""
                classes_prof = [c.strip() for c in classes_str.split(",") if c.strip()]
                
                if not classes_prof or any(cls in noms_classes_cycle for cls in classes_prof):
                    enseignants.append(prof)

            if not enseignants:
                st.info(
                    f"Aucun enseignant actif enregistré pour le moment sous le cycle **{cycle_en_cours}** dans cet établissement."
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
                        st.markdown(f"**Modification de l'enseignant : {prof.nom} {prof.prenom}**")
                        
                        col_edit1, col_edit2 = st.columns(2)
                        with col_edit1:
                            new_nom = st.text_input("Nom", value=prof.nom, key=f"edit_nom_{prof.id}")
                            new_email = st.text_input("Adresse Email", value=getattr(prof, "email", "") or "", key=f"edit_email_{prof.id}")
                        with col_edit2:
                            new_prenom = st.text_input("Prénom", value=prof.prenom, key=f"edit_prenom_{prof.id}")
                            new_tel = st.text_input("Téléphone", value=prof.telephone or "", key=f"edit_tel_{prof.id}")

                        classes_str_actuelle = getattr(prof, "classes_attribuees", getattr(prof, "classes", "")) or ""
                        matieres_str_actuelle = getattr(prof, "matieres_attribuees", getattr(prof, "matieres", "")) or ""

                        current_classes = [c.strip() for c in classes_str_actuelle.split(",") if c.strip()]
                        current_matieres = [m.strip().title() for m in matieres_str_actuelle.split(",") if m.strip()]
                        
                        opt_classes = sorted(list(set(noms_classes + current_classes)))
                        
                        new_classes = st.multiselect(
                            "Classes tenues", options=opt_classes, default=[c for c in current_classes if c in opt_classes], key=f"edit_cls_{prof.id}"
                        )
                        
                        # --- MATIÈRES DYNAMIQUES POUR L'ÉDITION ---
                        dyn_mats = get_matieres_dynamiques(new_classes, classes_cycle, ecole_active_id, cycle_en_cours, db)
                        opt_matieres = sorted(list(set(dyn_mats + current_matieres)))

                        new_matieres = st.multiselect(
                            "Matières dispensées", options=opt_matieres, default=[m for m in current_matieres if m in opt_matieres], key=f"edit_mats_{prof.id}"
                        )

                        st.markdown("**Informations Salariales**")
                        col_edit_sal1, col_edit_sal2 = st.columns(2)
                        with col_edit_sal1:
                            current_taux = float(getattr(prof, "taux_horaire", 1500.0) or 1500.0)
                            new_taux_horaire = st.number_input("Taux Horaire (FCFA)", value=current_taux, step=500.0, key=f"edit_taux_{prof.id}")
                        with col_edit_sal2:
                            current_salaire = float(getattr(prof, "salaire_base", 0.0) or 0.0)
                            new_salaire_base = st.number_input("Salaire de base (FCFA)", value=current_salaire, step=1000.0, key=f"edit_sal_{prof.id}")

                        col_btn1, col_btn2 = st.columns(2)
                        with col_btn1:
                            submit_edit = st.button("💾 Enregistrer les modifications", type="primary", key=f"save_edit_{prof.id}")
                        with col_btn2:
                            cancel_edit = st.button("Annuler", key=f"cancel_edit_{prof.id}")

                        if submit_edit:
                            ancienne_val = f"Classes: {classes_str_actuelle} | Matières: {matieres_str_actuelle}"
                            
                            str_classes_new = ", ".join(new_classes) if new_classes else "Aucune"
                            str_matieres_new = ", ".join(new_matieres) if new_matieres else "Aucune"
                            nouvelle_val = f"Classes: {str_classes_new} | Matières: {str_matieres_new}"

                            prof.nom = new_nom.upper()
                            prof.prenom = new_prenom
                            prof.telephone = new_tel
                            if hasattr(prof, "email"):
                                prof.email = new_email
                            
                            if hasattr(prof, "taux_horaire"):
                                prof.taux_horaire = new_taux_horaire
                            if hasattr(prof, "salaire_base"):
                                prof.salaire_base = new_salaire_base

                            if hasattr(prof, "classes_attribuees"):
                                prof.classes_attribuees = str_classes_new
                            if hasattr(prof, "classes"):
                                prof.classes = str_classes_new
                            if hasattr(prof, "matieres_attribuees"):
                                prof.matieres_attribuees = str_matieres_new
                            if hasattr(prof, "matieres"):
                                prof.matieres = str_matieres_new

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

                            st.success("Profil enseignant mis à jour et tracé avec succès !")
                            st.session_state[f"editing_prof_{prof.id}"] = False
                            st.rerun()
                            
                        if cancel_edit:
                            st.session_state[f"editing_prof_{prof.id}"] = False
                            st.rerun()
                        
                    st.markdown("<hr style='margin: 0.2rem 0; border-color: rgba(255,255,255,0.05);'>", unsafe_allow_html=True)

        with tab_ajout:
            st.markdown(f"### Enregistrement d'un Nouvel Enseignant — **{school_name} ({cycle_en_cours})**")

            if not classes_cycle:
                st.warning(f"⚠️ Veuillez d'abord configurer des classes pour le cycle **{cycle_en_cours}**.")
            else:
                # --- Suppression de st.form() pour permettre le rafraîchissement dynamique ---
                col_a1, col_a2 = st.columns(2)
                with col_a1:
                    nom_prof = st.text_input("Nom de l'enseignant *", key="add_nom")
                    email_prof = st.text_input("Adresse Email", key="add_email")
                with col_a2:
                    prenom_prof = st.text_input("Prénom de l'enseignant *", key="add_prenom")
                    tel_prof = st.text_input("Numéro de Téléphone", key="add_tel")

                st.markdown("#### Affectations Pédagogiques")
                classes_attribuees = st.multiselect(
                    "Classes tenues par l'enseignant", noms_classes, key="add_classes"
                )
                
                # --- MATIÈRES DYNAMIQUES POUR L'AJOUT ---
                dyn_mats_add = get_matieres_dynamiques(classes_attribuees, classes_cycle, ecole_active_id, cycle_en_cours, db)

                matieres_attribuees = st.multiselect(
                    "Matières dispensées", dyn_mats_add, key="add_matieres"
                )

                st.markdown("#### Informations Salariales")
                col_sal1, col_sal2 = st.columns(2)
                with col_sal1:
                    taux_horaire = st.number_input("Taux Horaire (FCFA / heure)", min_value=0.0, step=500.0, value=1500.0, key="add_taux")
                with col_sal2:
                    salaire_base = st.number_input("Salaire de base (si permanent) (FCFA)", min_value=0.0, step=1000.0, key="add_sal")

                submitted_prof = st.button("💾 Enregistrer l'enseignant", type="primary", key="btn_add_prof")
                
                if submitted_prof:
                    if not nom_prof.strip() or not prenom_prof.strip():
                        st.error("⚠️ Le nom et le prénom de l'enseignant sont obligatoires.")
                    else:
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
                                f"⚠️ Un enseignant nommé **{nom_prof.upper()} {prenom_prof}** est déjà enregistré dans cet établissement."
                            )
                        else:
                            str_classes = ", ".join(classes_attribuees) if classes_attribuees else "Aucune"
                            str_matieres = ", ".join(matieres_attribuees) if matieres_attribuees else "Aucune"

                            nouvel_enseignant = Enseignant(
                                school_id=ecole_active_id,
                                nom=nom_prof.strip().upper(),
                                prenom=prenom_prof.strip(),
                                telephone=tel_prof.strip() if tel_prof else None,
                                taux_horaire=taux_horaire,
                                salaire_base=salaire_base
                            )

                            if hasattr(nouvel_enseignant, "email"):
                                nouvel_enseignant.email = email_prof.strip() if email_prof else None
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
                                action=f"Enregistrement de l'enseignant : {nom_prof.strip().upper()} {prenom_prof.strip()}",
                                statut="Succès",
                                valeur_avant="Inexistant",
                                valeur_apres=f"Affecté à {len(classes_attribuees)} classe(s)",
                            )

                            st.success(
                                f"✅ L'enseignant **{nom_prof.strip().upper()} {prenom_prof.strip()}** a été enregistré avec succès !"
                            )
                            
                            # Réinitialisation forcée après enregistrement pour vider les champs
                            st.rerun()

    finally:
        db.close()


# Alias de compatibilité exhaustive
afficher_gestion_enseignants = afficher_enseignants
afficher_enseignants = afficher_enseignants
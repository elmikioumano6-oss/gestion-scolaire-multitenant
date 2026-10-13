from datetime import datetime
import unicodedata
import pandas as pd
import streamlit as st
from database.audit import log_action_erp
from database.db_config import SessionLocal
from database.models import Classe, Enseignant, Matiere, School, User


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
    m_brutes = []
    try:
        ids_classes_cycle = [c.id for c in classes_cycle if c.id]
        if not ids_classes_cycle:
            return []

        if selected_classes_labels:
            ids_cibles = [c.id for c in classes_cycle if c.libelle and c.libelle.strip() in selected_classes_labels]
        else:
            ids_cibles = ids_classes_cycle

        if ids_cibles and hasattr(Matiere, "classe_id"):
            mat_q = db.query(Matiere).filter(Matiere.classe_id.in_(ids_cibles))
            if hasattr(Matiere, "deleted_at"):
                mat_q = mat_q.filter(Matiere.deleted_at.is_(None))
            m_brutes = mat_q.all()
    except Exception:
        m_brutes = []

    if not m_brutes:
        try:
            mat_q_all = db.query(Matiere).filter(Matiere.school_id == ecole_active_id)
            if hasattr(Matiere, "deleted_at"):
                mat_q_all = mat_q_all.filter(Matiere.deleted_at.is_(None))
            m_brutes = mat_q_all.all()
        except Exception:
            m_brutes = []

    m_dict = {}
    cycle_actuel_lower = str(cycle_en_cours).lower()
    
    for m in m_brutes:
        n_brut = m.libelle if hasattr(m, "libelle") and m.libelle else getattr(m, "nom", "Matière")
        n_key = normaliser_chaine(n_brut)
        
        if "collège" in cycle_actuel_lower or "college" in cycle_actuel_lower:
            if "philosophie" in n_key or "philo" in n_key:
                continue

        if n_key and n_key not in m_dict:
            m_dict[n_key] = m
            
    return sorted([(m.libelle if hasattr(m, 'libelle') and m.libelle else getattr(m, 'nom', 'Matière')).title() for m in m_dict.values()])

def afficher_enseignants():
    st.subheader("👥 Gestion du Corps Professoral & Enseignants")
    st.markdown("Suivi, administration et affectations pédagogiques des enseignants.")
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
        ecole_courante = db.query(School).filter(School.id == ecole_active_id).first()
        school_name = ecole_courante.nom if ecole_courante else st.session_state.get("school_name", "Établissement")
    finally:
        db.close()

    cycle_en_cours = st.session_state.get("cycle_actif", "Collège")

    if not school_id and not is_super_admin:
        st.warning("⚠️ Veuillez vous connecter pour accéder à cette section.")
        return

    db = SessionLocal()
    try:
        classes_query = db.query(Classe).filter(Classe.school_id == ecole_active_id)
        if hasattr(Classe, "deleted_at"):
            classes_query = classes_query.filter(Classe.deleted_at.is_(None))
        classes_cycle = classes_query.all()
        noms_classes = sorted(list(set([c.libelle.strip() for c in classes_cycle if c.libelle])))

        tab_liste, tab_ajout = st.tabs(["📋 Liste des Enseignants", "➕ Enregistrer un Enseignant"])

        with tab_liste:
            st.markdown(f"### Enseignants Actifs — **{school_name}**")
            ens_query = db.query(Enseignant).filter(Enseignant.school_id == ecole_active_id)
            if hasattr(Enseignant, "deleted_at"):
                ens_query = ens_query.filter(Enseignant.deleted_at.is_(None))
            enseignants = ens_query.all()

            if not enseignants:
                st.info("Aucun enseignant actif enregistré pour cet établissement.")
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
                    c[1].write(f"📞 {prof.telephone or 'N/D'}\n📧 {getattr(prof, 'email', 'N/D')}")
                    c[2].write(getattr(prof, "classes_attribuees", getattr(prof, "classes", "Aucune")))
                    c[3].write(getattr(prof, "matieres_attribuees", getattr(prof, "matieres", "Aucune")))

                    btn_col1, btn_col2 = c[4].columns(2)
                    with btn_col1:
                        if st.button("✏️", key=f"edit_prof_{prof.id}", help="Modifier"):
                            st.session_state[f"editing_prof_{prof.id}"] = True
                    with btn_col2:
                        if st.button("🗑️", key=f"del_prof_{prof.id}", help="Supprimer"):
                            st.session_state[f"deleting_prof_{prof.id}"] = True

                    if st.session_state.get(f"deleting_prof_{prof.id}", False):
                        st.warning(f"Voulez-vous vraiment archiver ou supprimer **{prof.nom} {prof.prenom}** ?")
                        col_conf1, col_conf2 = st.columns(2)
                        with col_conf1:
                            if st.button("Confirmer", key=f"confirm_del_prof_{prof.id}", type="primary"):
                                try:
                                    compte_lie = db.query(User).filter(User.enseignant_id == prof.id).first()
                                    if compte_lie:
                                        db.delete(compte_lie)

                                    if hasattr(prof, "deleted_at"):
                                        prof.deleted_at = datetime.now()
                                    else:
                                        db.delete(prof)
                                    db.commit()
                                    st.success("Enseignant et son compte associé traités avec succès !")
                                    st.session_state[f"deleting_prof_{prof.id}"] = False
                                    st.rerun()
                                except Exception as err:
                                    db.rollback()
                                    st.error(f"Erreur lors de la suppression : {err}")
                        with col_conf2:
                            if st.button("Annuler", key=f"cancel_del_prof_{prof.id}"):
                                st.session_state[f"deleting_prof_{prof.id}"] = False
                                st.rerun()

                    if st.session_state.get(f"editing_prof_{prof.id}", False):
                        st.markdown(f"**Modification : {prof.nom} {prof.prenom}**")
                        col_edit1, col_edit2 = st.columns(2)
                        with col_edit1:
                            new_nom = st.text_input("Nom", value=prof.nom, key=f"edit_nom_{prof.id}")
                            new_email = st.text_input("Email", value=getattr(prof, "email", "") or "", key=f"edit_email_{prof.id}")
                        with col_edit2:
                            new_prenom = st.text_input("Prénom", value=prof.prenom, key=f"edit_prenom_{prof.id}")
                            new_tel = st.text_input("Téléphone", value=prof.telephone or "", key=f"edit_tel_{prof.id}")

                        classes_str_actuelle = getattr(prof, "classes_attribuees", getattr(prof, "classes", "")) or ""
                        matieres_str_actuelle = getattr(prof, "matieres_attribuees", getattr(prof, "matieres", "")) or ""
                        current_classes = [c.strip() for c in classes_str_actuelle.split(",") if c.strip()]
                        current_matieres = [m.strip().title() for m in matieres_str_actuelle.split(",") if m.strip()]

                        opt_classes = sorted(list(set(noms_classes + current_classes)))
                        new_classes = st.multiselect("Classes tenues", options=opt_classes, default=[c for c in current_classes if c in opt_classes], key=f"edit_cls_{prof.id}")

                        dyn_mats = get_matieres_dynamiques(new_classes, classes_cycle, ecole_active_id, cycle_en_cours, db)
                        opt_matieres = sorted(list(set(dyn_mats + current_matieres)))
                        new_matieres = st.multiselect("Matières dispensées", options=opt_matieres, default=[m for m in current_matieres if m in opt_matieres], key=f"edit_mats_{prof.id}")

                        col_btn1, col_btn2 = st.columns(2)
                        with col_btn1:
                            submit_edit = st.button("💾 Enregistrer", type="primary", key=f"save_edit_{prof.id}")
                        with col_btn2:
                            cancel_edit = st.button("Annuler", key=f"cancel_edit_{prof.id}")

                        if submit_edit:
                            prof.nom = new_nom.upper()
                            prof.prenom = new_prenom
                            prof.telephone = new_tel
                            if hasattr(prof, "email"):
                                prof.email = new_email
                            str_classes_new = ", ".join(new_classes) if new_classes else "Aucune"
                            str_matieres_new = ", ".join(new_matieres) if new_matieres else "Aucune"
                            if hasattr(prof, "classes_attribuees"):
                                prof.classes_attribuees = str_classes_new
                            if hasattr(prof, "classes"):
                                prof.classes = str_classes_new
                            if hasattr(prof, "matieres_attribuees"):
                                prof.matieres_attribuees = str_matieres_new
                            if hasattr(prof, "matieres"):
                                prof.matieres = str_matieres_new
                            db.commit()
                            st.success("Mis à jour avec succès !")
                            st.session_state[f"editing_prof_{prof.id}"] = False
                            st.rerun()

                        if cancel_edit:
                            st.session_state[f"editing_prof_{prof.id}"] = False
                            st.rerun()

        with tab_ajout:
            st.markdown(f"### Enregistrement — **{school_name}**")
            if not classes_cycle:
                st.warning("⚠️ Veuillez configurer des classes pour l'établissement.")
            else:
                with st.form("form_ajout_enseignant", clear_on_submit=False):
                    col_a1, col_a2 = st.columns(2)
                    with col_a1:
                        nom_prof = st.text_input("Nom *", key="add_nom")
                        email_prof = st.text_input("Email", key="add_email")
                    with col_a2:
                        prenom_prof = st.text_input("Prénom *", key="add_prenom")
                        tel_prof = st.text_input("Téléphone (WhatsApp)", key="add_tel")

                    classes_attribuees = st.multiselect("Classes", noms_classes, key="add_classes")
                    dyn_mats_add = get_matieres_dynamiques(classes_attribuees, classes_cycle, ecole_active_id, cycle_en_cours, db)
                    matieres_attribuees = st.multiselect("Matières", dyn_mats_add, key="add_matieres")

                    submitted_prof = st.form_submit_button("💾 Enregistrer", type="primary")
                    if submitted_prof:
                        if not nom_prof.strip() or not prenom_prof.strip():
                            st.error("⚠️ Nom et prénom obligatoires.")
                        else:
                            try:
                                nouvel_enseignant = Enseignant(
                                    school_id=ecole_active_id,
                                    nom=nom_prof.strip().upper(),
                                    prenom=prenom_prof.strip(),
                                    telephone=tel_prof.strip() if tel_prof else None
                                )
                                if hasattr(nouvel_enseignant, "email"):
                                    nouvel_enseignant.email = email_prof.strip() if email_prof else None

                                str_classes = ", ".join(classes_attribuees) if classes_attribuees else "Aucune"
                                str_matieres = ", ".join(matieres_attribuees) if matieres_attribuees else "Aucune"
                                
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
                                st.success("✅ Enseignant enregistré avec succès ! Vous pouvez maintenant lui créer un accès sécurisé depuis le module 'Gestion Comptes'.")
                            except Exception as e:
                                db.rollback()
                                st.error(f"Erreur : {e}")
    finally:
        db.close()

afficher_gestion_enseignants = afficher_enseignants
afficher_enseignants = afficher_enseignants
afficher_espace_enseignant = afficher_enseignants
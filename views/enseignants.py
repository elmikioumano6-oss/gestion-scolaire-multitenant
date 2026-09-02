import streamlit as st
import pandas as pd
from datetime import datetime
from database.db_config import SessionLocal
from database.models import Classe, Matiere, School, ActivityLog

def afficher_enseignants():
    st.subheader("👥 Gestion du Corps Professoral & Enseignants")
    st.markdown("Suivi et administration des enseignants rattachés à l'établissement avec isolation multi-tenant stricte.")
    st.markdown("---")

    school_id = st.session_state.get("school_id")
    is_super_admin = st.session_state.get("is_super_admin", False)
    
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
        classes_query = db.query(Classe).filter(Classe.cycle == cycle_en_cours)
        if not is_super_admin and school_id:
            classes_query = classes_query.filter(Classe.school_id == school_id)
        classes_cycle = classes_query.all()

        matieres_query = db.query(Matiere).filter(Matiere.cycle == cycle_en_cours)
        if not is_super_admin and school_id:
            matieres_query = matieres_query.filter(Matiere.school_id == school_id)
        matieres_cycle = matieres_query.all()

        tab_liste, tab_ajout = st.tabs(["📋 Liste des Enseignants", "➕ Enregistrer un Enseignant"])

        if "enseignants_data" not in st.session_state:
            st.session_state["enseignants_data"] = {}
        if "teacher_assignments" not in st.session_state:
            st.session_state["teacher_assignments"] = {}

        key_ens_store = f"{school_id}_{cycle_en_cours}"
        liste_professeurs = st.session_state["enseignants_data"].get(key_ens_store, [])

        with tab_liste:
            st.markdown(f"### Enseignants Actifs — **{school_name} ({cycle_en_cours})**")

            if not liste_professeurs:
                st.info("Aucun enseignant enregistré pour le moment dans cet établissement pour ce cycle.")
            else:
                df_profs = pd.DataFrame(liste_professeurs)
                st.dataframe(df_profs, use_container_width=True)

        with tab_ajout:
            st.markdown(f"### Enregistrement d'un Nouvel Enseignant — **{school_name}**")

            if not classes_cycle or not matieres_cycle:
                st.warning("⚠️ Veuillez d'abord configurer des classes et des matières dans les modules correspondants.")
            else:
                noms_classes = [c.libelle for c in classes_cycle]
                noms_matieres = [m.libelle for m in matieres_cycle]

                with st.form("form_enregistrement_enseignant"):
                    col1, col2 = st.columns(2)
                    with col1:
                        nom_prof = st.text_input("Nom de l'enseignant")
                        email_prof = st.text_input("Adresse Email")
                    with col2:
                        prenom_prof = st.text_input("Prénom de l'enseignant")
                        tel_prof = st.text_input("Numéro de Téléphone")

                    st.markdown("#### Affectations Pédagogiques")
                    classes_attribuees = st.multiselect("Classes tenues par l'enseignant", noms_classes)
                    matieres_attribuees = st.multiselect("Matières dispensées", noms_matieres)

                    submitted_prof = st.form_submit_button("💾 Enregistrer l'enseignant")
                    if submitted_prof:
                        if not nom_prof or not prenom_prof:
                            st.error("⚠️ Le nom et le prénom de l'enseignant sont obligatoires.")
                        else:
                            username_key = f"{nom_prof.lower()}_{prenom_prof.lower()}".replace(" ", "_")
                            
                            nouveau_prof = {
                                "Nom & Prénom": f"{nom_prof} {prenom_prof}",
                                "Email": email_prof or "—",
                                "Téléphone": tel_prof or "—",
                                "Classes": ", ".join(classes_attribuees) if classes_attribuees else "Aucune",
                                "Matières": ", ".join(matieres_attribuees) if matieres_attribuees else "Aucune"
                            }

                            if key_ens_store not in st.session_state["enseignants_data"]:
                                st.session_state["enseignants_data"][key_ens_store] = []
                            
                            st.session_state["enseignants_data"][key_ens_store].append(nouveau_prof)

                            st.session_state["teacher_assignments"][username_key] = {
                                "classes": classes_attribuees,
                                "matieres": matieres_attribuees
                            }

                            target_school_id = school_id or 1
                            db.add(ActivityLog(
                                school_id=target_school_id,
                                timestamp=datetime.utcnow(),
                                username=st.session_state.get("username", "admin"),
                                action=f"Enregistrement enseignant : {nom_prof} {prenom_prof}",
                                module="Enseignants",
                                statut="Succès"
                            ))
                            db.commit()

                            st.success(f"✅ L'enseignant **{nom_prof} {prenom_prof}** a été enregistré avec succès et ses accès ont été restreints à ses classes !")

    finally:
        db.close()

afficher_enseignants = afficher_enseignants
afficher_gestion_enseignants = afficher_enseignants
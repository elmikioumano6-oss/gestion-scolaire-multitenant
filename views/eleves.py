import streamlit as st
import pandas as pd
from database.db_config import SessionLocal
from database.models import Eleve, Classe, School

def afficher_eleves():
    st.subheader("🎓 Gestion et Inscription des Élèves")
    st.markdown("Enregistrement et suivi des effectifs scolaires avec isolation multi-tenant stricte.")
    st.markdown("---")

    school_id = st.session_state.get("school_id")
    is_super_admin = st.session_state.get("is_super_admin", False)
    school_name = st.session_state.get("school_name", "Établissement")
    cycle_en_cours = st.session_state.get("cycle_actif", "Collège")

    if not school_id and not is_super_admin:
        st.warning("⚠️ Veuillez vous connecter pour accéder à cette section.")
        return

    db = SessionLocal()
    try:
        tab1, tab2 = st.tabs(["📋 Liste des Élèves", "➕ Inscrire un Élève"])

        classes_query = db.query(Classe).filter(Classe.cycle == cycle_en_cours)
        if not is_super_admin and school_id:
            classes_query = classes_query.filter(Classe.school_id == school_id)
        classes_cycle = classes_query.all()
        classes_ids = [c.id for c in classes_cycle]

        with tab1:
            st.markdown(f"### Effectifs Inscrits — **{school_name} ({cycle_en_cours})**")

            if not classes_ids:
                st.info(f"Aucune classe disponible pour le cycle **{cycle_en_cours}** dans cet établissement.")
            else:
                eleves_query = db.query(Eleve).filter(Eleve.classe_id.in_(classes_ids))
                if not is_super_admin and school_id:
                    eleves_query = eleves_query.filter(Eleve.school_id == school_id)
                eleves = eleves_query.all()

                if not eleves:
                    st.info("Aucun élève enregistré pour le moment dans ce cycle.")
                else:
                    data = []
                    classes_dict = {c.id: c.libelle for c in classes_cycle}
                    for e in eleves:
                        data.append({
                            "Nom": getattr(e, 'nom', ''),
                            "Prénom": getattr(e, 'prenom', ''),
                            "Matricule": getattr(e, 'matricule', 'N/D'),
                            "Classe": classes_dict.get(e.classe_id, 'N/D'),
                            "Montant Payé (FCFA)": getattr(e, 'montant_paye', 0.0) or 0.0
                        })
                    df = pd.DataFrame(data)
                    st.dataframe(df, use_container_width=True)

        with tab2:
            st.markdown(f"### Formulaire d'Inscription — **{school_name} ({cycle_en_cours})**")

            if not classes_cycle:
                st.warning(f"⚠️ Veuillez d'abord créer des classes pour le cycle **{cycle_en_cours}** dans le menu 'Classes & Tarifs'.")
            else:
                noms_classes = {c.libelle: c.id for c in classes_cycle}

                with st.form("form_inscription_eleve"):
                    col1, col2 = st.columns(2)
                    with col1:
                        nom = st.text_input("Nom de l'élève")
                        prenom = st.text_input("Prénom de l'élève")
                        matricule = st.text_input("Matricule (optionnel)")
                    with col2:
                        classe_choisie = st.selectbox("Sélectionner la classe", list(noms_classes.keys()))
                        montant_paye_init = st.number_input("Versement initial (FCFA)", min_value=0.0, step=5000.0)

                    submitted = st.form_submit_button("Valider l'inscription")
                    if submitted:
                        if not nom or not prenom:
                            st.error("⚠️ Le nom et le prénom de l'élève sont obligatoires.")
                        else:
                            target_school_id = school_id
                            if is_super_admin and not target_school_id:
                                ecole_defaut = db.query(School).first()
                                target_school_id = ecole_defaut.id if ecole_defaut else 1

                            nouvel_eleve = Eleve(
                                school_id=target_school_id,
                                classe_id=noms_classes[classe_choisie],
                                nom=nom.strip().upper(),
                                prenom=prenom.strip(),
                                matricule=matricule.strip() if matricule else None,
                                montant_paye=montant_paye_init
                            )
                            db.add(nouvel_eleve)
                            db.commit()
                            st.success(f"✅ L'élève {nom} {prenom} a été inscrit avec succès !")
                            st.rerun()

    finally:
        db.close()
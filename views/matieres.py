import streamlit as st
import pandas as pd
from datetime import datetime
from database.db_config import SessionLocal
from database.models import Matiere, School, ActivityLog

def afficher_matieres():
    st.subheader("📚 Gestion des Matières & Coefficients")
    st.markdown("Configuration du programme d'enseignement et des coefficients avec isolation multi-tenant stricte.")
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
        tab1, tab2 = st.tabs(["📋 Liste des Matières", "➕ Ajouter une Matière"])

        with tab1:
            st.markdown(f"### Programme Enregistré — **{school_name} ({cycle_en_cours})**")
            
            # Isolation stricte multi-écoles et multi-cycles
            query = db.query(Matiere).filter(Matiere.cycle == cycle_en_cours)
            if not is_super_admin and school_id:
                query = query.filter(Matiere.school_id == school_id)
            matieres = query.all()

            if not matieres:
                st.info(f"Aucune matière enregistrée pour le cycle **{cycle_en_cours}** dans cet établissement.")
            else:
                data = []
                for m in matieres:
                    data.append({
                        "Code": getattr(m, 'code', 'N/D'),
                        "Intitulé (Matière)": getattr(m, 'libelle', ''),
                        "Coefficient": getattr(m, 'coefficient', 1.0),
                        "Cycle": getattr(m, 'cycle', cycle_en_cours)
                    })
                df = pd.DataFrame(data)
                st.dataframe(df, use_container_width=True)

        with tab2:
            st.markdown(f"### Ajout d'une Nouvelle Matière — **{school_name} ({cycle_en_cours})**")
            with st.form("form_add_matiere"):
                col1, col2 = st.columns(2)
                with col1:
                    code_matiere = st.text_input("Code de la matière (ex: MATHS)")
                    libelle_matiere = st.text_input("Intitulé de la matière")
                with col2:
                    coefficient = st.number_input("Coefficient", min_value=1.0, max_value=10.0, value=2.0, step=1.0)

                submitted = st.form_submit_button("Enregistrer la matière")
                if submitted:
                    if not libelle_matiere:
                        st.error("⚠️ L'intitulé de la matière est obligatoire.")
                    else:
                        target_school_id = school_id
                        if is_super_admin and not target_school_id:
                            ecole_defaut = db.query(School).first()
                            target_school_id = ecole_defaut.id if ecole_defaut else 1

                        nouvelle_matiere = Matiere(
                            school_id=target_school_id,
                            code=code_matiere.strip().upper(),
                            libelle=libelle_matiere.strip(),
                            coefficient=coefficient,
                            cycle=cycle_en_cours
                        )
                        db.add(nouvelle_matiere)

                        # Traçabilité automatique dans le journal d'activité
                        nouveau_log = ActivityLog(
                            school_id=target_school_id,
                            timestamp=datetime.utcnow(),
                            username=st.session_state.get("username", "admin"),
                            action=f"Ajout de la matière {libelle_matiere} (Coeff: {coefficient})",
                            module="Matières & Coeffs",
                            statut="Succès"
                        )
                        db.add(nouveau_log)

                        db.commit()
                        st.success(f"✅ La matière '{libelle_matiere}' a été ajoutée avec succès au cycle {cycle_en_cours} !")
                        st.rerun()

    finally:
        db.close()
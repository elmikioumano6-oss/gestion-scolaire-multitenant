import streamlit as st
import pandas as pd
from datetime import datetime
from database.db_config import SessionLocal
from database.models import Classe, School, ActivityLog

def afficher_classes():
    st.subheader("🏫 Gestion des Classes & Tarifs")
    st.markdown("Configuration des classes, capacités et grille tarifaire complète par cycle et par établissement.")
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
        tab1, tab2 = st.tabs(["📋 Liste des Classes", "➕ Ajouter une Classe"])

        with tab1:
            st.markdown(f"### Classes et Grilles Tarifs — **{school_name} ({cycle_en_cours})**")
            
            query = db.query(Classe).filter(Classe.cycle == cycle_en_cours)
            if not is_super_admin and school_id:
                query = query.filter(Classe.school_id == school_id)
            classes = query.all()

            if not classes:
                st.info(f"Aucune classe enregistrée pour le cycle **{cycle_en_cours}** dans cet établissement.")
            else:
                data = []
                for c in classes:
                    data.append({
                        "Libellé": getattr(c, 'libelle', ''),
                        "Niveau": getattr(c, 'niveau', ''),
                        "Frais Scolarité (FCFA)": getattr(c, 'frais_scolarite', 0.0) or 0.0,
                        "Frais Inscription (FCFA)": getattr(c, 'frais_inscription', 0.0) or 0.0,
                        "COGES (FCFA)": getattr(c, 'coges', 0.0) or 0.0,
                        "Transport (FCFA)": getattr(c, 'transport', 0.0) or 0.0,
                        "Cantine (FCFA)": getattr(c, 'cantine', 0.0) or 0.0,
                        "Cycle": getattr(c, 'cycle', cycle_en_cours)
                    })
                df = pd.DataFrame(data)
                st.dataframe(df, use_container_width=True)

        with tab2:
            st.markdown(f"### Ajout d'une Nouvelle Classe — **{school_name} ({cycle_en_cours})**")
            with st.form("form_add_classe"):
                col1, col2 = st.columns(2)
                with col1:
                    libelle = st.text_input("Libellé de la classe (ex: 6ème A)")
                    niveau = st.text_input("Niveau (ex: 6ème)")
                    frais_scol = st.number_input("Frais de Scolarité (FCFA)", min_value=0.0, step=5000.0)
                    frais_inscr = st.number_input("Frais d'Inscription (FCFA)", min_value=0.0, step=1000.0)
                with col2:
                    coges = st.number_input("Cotisation COGES (FCFA)", min_value=0.0, step=1000.0)
                    transport = st.number_input("Frais de Transport (FCFA)", min_value=0.0, step=1000.0)
                    cantine = st.number_input("Frais de Cantine (FCFA)", min_value=0.0, step=1000.0)

                submitted = st.form_submit_button("Enregistrer la classe")
                if submitted:
                    if not libelle:
                        st.error("⚠️ Le libellé de la classe est obligatoire.")
                    else:
                        target_school_id = school_id
                        if is_super_admin and not target_school_id:
                            ecole_defaut = db.query(School).first()
                            target_school_id = ecole_defaut.id if ecole_defaut else 1

                        nouvelle_classe = Classe(
                            school_id=target_school_id,
                            libelle=libelle.strip(),
                            niveau=niveau.strip(),
                            frais_scolarite=frais_scol,
                            frais_inscription=frais_inscr,
                            coges=coges,
                            transport=transport,
                            cantine=cantine,
                            cycle=cycle_en_cours
                        )
                        db.add(nouvelle_classe)

                        # Traçabilité automatique dans le journal d'activité
                        nouveau_log = ActivityLog(
                            school_id=target_school_id,
                            timestamp=datetime.utcnow(),
                            username=st.session_state.get("username", "admin"),
                            action=f"Création de la classe {libelle} ({cycle_en_cours})",
                            module="Classes & Tarifs",
                            statut="Succès"
                        )
                        db.add(nouveau_log)

                        db.commit()
                        st.success(f"✅ La classe '{libelle}' a été créée avec succès pour le cycle {cycle_en_cours} !")
                        st.rerun()

    finally:
        db.close()
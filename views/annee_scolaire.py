import streamlit as st
import pandas as pd
from database.db_config import SessionLocal
from database.models import AnneeScolaire, School, ActivityLog
from datetime import datetime

def afficher_annee_scolaire():
    st.subheader("📅 Gestion des Années Scolaires")
    st.markdown("Configuration et activation des exercices académiques avec isolation multi-tenant stricte.")
    st.markdown("---")

    school_id = st.session_state.get("school_id")
    is_super_admin = st.session_state.get("is_super_admin", False)

    if not school_id and not is_super_admin:
        st.warning("⚠️ Veuillez vous connecter pour accéder à cette section.")
        return

    db = SessionLocal()
    try:
        tab1, tab2 = st.tabs(["📋 Liste des Années", "➕ Nouvelle Année Scolaire"])

        with tab1:
            st.markdown("### Exercices Académiques")
            query_annees = db.query(AnneeScolaire)
            if not is_super_admin and school_id:
                query_annees = query_annees.filter(AnneeScolaire.school_id == school_id)
            annees = query_annees.all()

            if not annees:
                st.info("Aucune année scolaire enregistrée.")
            else:
                data = []
                for a in annees:
                    data.append({
                        "Libellé": a.libelle,
                        "Statut Actif": "✅ Actif" if getattr(a, 'active', False) else "❌ Inactif",
                        "Date Début": str(getattr(a, 'date_debut', 'N/D')),
                        "Date Fin": str(getattr(a, 'date_fin', 'N/D'))
                    })
                df_annees = pd.DataFrame(data)
                st.dataframe(df_annees, use_container_width=True)

        with tab2:
            st.markdown("### Enregistrer une Année Scolaire")
            with st.form("form_add_annee"):
                col_a1, col_a2 = st.columns(2)
                with col_a1:
                    libelle = st.text_input("Libellé (ex: 2026-2027)")
                    active = st.checkbox("Définir comme année active", value=True)
                with col_a2:
                    date_debut = st.date_input("Date de début")
                    date_fin = st.date_input("Date de fin")

                submitted = st.form_submit_button("Enregistrer l'exercice")
                if submitted:
                    if not libelle:
                        st.error("⚠️ Le libellé de l'année scolaire est obligatoire.")
                    else:
                        target_school_id = school_id
                        if is_super_admin and not target_school_id:
                            ecole_defaut = db.query(School).first()
                            target_school_id = ecole_defaut.id if ecole_defaut else 1

                        if active:
                            db.query(AnneeScolaire).filter(AnneeScolaire.school_id == target_school_id).update({"active": False})

                        nouvelle_annee = AnneeScolaire(
                            school_id=target_school_id,
                            libelle=libelle.strip(),
                            active=active,
                            date_debut=date_debut,
                            date_fin=date_fin
                        )
                        db.add(nouvelle_annee)

                        # Traçabilité automatique dans le journal d'activité
                        nouveau_log = ActivityLog(
                            school_id=target_school_id,
                            timestamp=datetime.utcnow(),
                            username=st.session_state.get("username", "admin"),
                            action=f"Création de l'année scolaire {libelle}",
                            module="Année Scolaire",
                            statut="Succès"
                        )
                        db.add(nouveau_log)

                        db.commit()
                        st.success(f"✅ L'année scolaire '{libelle}' a été configurée avec succès !")
                        st.rerun()

    finally:
        db.close()

# Alias de compatibilité
afficher_annee_scolaire = afficher_annee_scolaire
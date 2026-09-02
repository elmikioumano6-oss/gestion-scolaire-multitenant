import streamlit as st
import pandas as pd
from database.db_config import SessionLocal
from database.models import School

def afficher_depenses():
    st.subheader("📉 Gestion des Dépenses")
    st.markdown("Suivi des charges opérationnelles et budgétaires par établissement et par cycle.")
    st.markdown("---")

    school_id = st.session_state.get("school_id")
    is_super_admin = st.session_state.get("is_super_admin", False)
    school_name = st.session_state.get("school_name", "Établissement")
    
    # Récupération automatique du cycle actif depuis le menu latéral gauche
    cycle_en_cours = st.session_state.get("cycle_actif", "Collège")

    if not school_id and not is_super_admin:
        st.warning("⚠️ Veuillez vous connecter pour accéder à cette section.")
        return

    db = SessionLocal()
    try:
        st.markdown(f"### Enregistrement des Dépenses — **{school_name} ({cycle_en_cours})**")

        with st.form("form_add_depense"):
            col1, col2 = st.columns(2)
            with col1:
                libelle_depense = st.text_input("Libellé / Motif de la dépense")
                montant = st.number_input("Montant (FCFA)", min_value=0.0, step=1000.0)
            with col2:
                categorie = st.selectbox("Catégorie", ["Fournitures scolaires", "Maintenance & Réparations", "Charges administratives", "Énergie & Eau", "Divers"])
                date_depense = st.date_input("Date de la dépense")

            submitted = st.form_submit_button("Enregistrer la dépense")
            if submitted:
                if not libelle_depense or montant <= 0:
                    st.error("⚠️ Veuillez renseigner un libellé et un montant valide.")
                else:
                    st.success(f"✅ Dépense de {montant:,.0f} FCFA ('{libelle_depense}') enregistrée avec succès pour le cycle {cycle_en_cours} !")
                    st.rerun()

        st.markdown("---")
        st.markdown(f"### Historique des Dépenses — **{cycle_en_cours}**")
        st.info("Aucune dépense enregistrée pour le moment dans cet établissement.")

    finally:
        db.close()
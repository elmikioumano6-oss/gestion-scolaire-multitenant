import streamlit as st
import pandas as pd
from datetime import datetime
from database.db_config import SessionLocal
from database.models import School, Depense
from database.audit import log_action_erp

def afficher_depenses():
    st.subheader("📉 Gestion des Dépenses")
    st.markdown("Suivi des charges opérationnelles et budgétaires par établissement et par cycle avec traçabilité ERP.")
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
        st.markdown(f"### Enregistrement des Dépenses — **{school_name} ({cycle_en_cours})**")

        with st.form("form_add_depense"):
            col1, col2 = st.columns(2)
            with col1:
                libelle_depense = st.text_input("Libellé / Motif de la dépense")
                montant = st.number_input("Montant (FCFA)", min_value=0.0, step=1000.0, value=0.0)
            with col2:
                categorie = st.selectbox("Catégorie", [
                    "Fournitures scolaires",
                    "Maintenance & Réparations",
                    "Charges administratives",
                    "Énergie & Eau",
                    "Divers"
                ])
                date_depense = st.date_input("Date de la dépense", value=datetime.now())

            submitted = st.form_submit_button("💾 Enregistrer la dépense", type="primary")
            if submitted:
                if not libelle_depense.strip() or montant <= 0:
                    st.error("⚠️ Veuillez renseigner un libellé valide et un montant supérieur à zéro.")
                else:
                    target_school_id = school_id or 1
                    
                    # Enregistrement en base de données
                    nouvelle_depense = Depense(
                        school_id=target_school_id,
                        cycle=cycle_en_cours,
                        libelle=libelle_depense.strip(),
                        montant=montant,
                        categorie=categorie,
                        date_depense=datetime.combine(date_depense, datetime.now().time()),
                        auteur=st.session_state.get("username", "admin")
                    )
                    db.add(nouvelle_depense)
                    
                    # Traçabilité médico-légale centralisée (Normes ERP - SOC 2 / ISO 27001)
                    log_action_erp(
                        module="Gestion des Dépenses",
                        action=f"Enregistrement dépense [{categorie}] : {libelle_depense.strip()} ({montant:,.0f} FCFA)",
                        statut="Critique",
                        valeur_avant="0 FCFA",
                        valeur_apres=f"{montant:,.0f} FCFA"
                    )
                    
                    db.commit()
                    st.success(f"✅ Dépense de {montant:,.0f} FCFA ('{libelle_depense}') enregistrée et tracée avec succès pour le cycle {cycle_en_cours} !")
                    st.rerun()

        st.markdown("---")
        st.markdown(f"### Historique des Dépenses — **{school_name} ({cycle_en_cours})**")

        # Récupération des dépenses filtrées par école et par cycle actif
        query_depenses = db.query(Depense).filter(Depense.cycle == cycle_en_cours)
        if not is_super_admin and school_id:
            query_depenses = query_depenses.filter(Depense.school_id == school_id)
        
        depenses_list = query_depenses.order_by(Depense.date_depense.desc()).all()

        if not depenses_list:
            st.info(f"📌 Aucune dépense enregistrée pour le cycle **{cycle_en_cours}** dans cet établissement.")
        else:
            total_depenses = sum(d.montant for d in depenses_list)
            st.metric("💵 Total des Dépenses du Cycle", f"{total_depenses:,.0f} FCFA")

            data = []
            for d in depenses_list:
                data.append({
                    "Date": d.date_depense.strftime("%d/%m/%Y") if d.date_depense else "N/D",
                    "Libellé": d.libelle,
                    "Catégorie": d.categorie,
                    "Montant (FCFA)": f"{d.montant:,.0f}",
                    "Auteur": d.auteur or "N/D"
                })
            
            df_dep = pd.DataFrame(data)
            st.dataframe(df_dep, use_container_width=True)

    finally:
        db.close()

# Alias de compatibilité exhaustive pour le routeur app.py
afficher_depenses = afficher_depenses
afficher_gestion_depenses = afficher_depenses
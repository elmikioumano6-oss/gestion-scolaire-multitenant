import streamlit as st
import pandas as pd
from database.db_config import SessionLocal
from database.models import Classe, Eleve, School

def afficher_rapports():
    st.subheader("📑 Rapports & Bilan Financier Consolidé")
    st.markdown("Synthèse macroscopique des flux de trésorerie, suivi consolidé par établissement et par cycle.")
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
        # Isolation stricte multi-écoles et multi-cycles
        classes_query = db.query(Classe).filter(Classe.cycle == cycle_en_cours)
        if not is_super_admin and school_id:
            classes_query = classes_query.filter(Classe.school_id == school_id)
        
        classes_cycle = classes_query.all()

        if not classes_cycle:
            st.info(f"📌 **{school_name}** — Aucune classe enregistrée pour le cycle **{cycle_en_cours}** dans cet établissement.")
            return

        classes_dict = {c.id: c for c in classes_cycle}
        classes_ids = list(classes_dict.keys())

        eleves_query = db.query(Eleve).filter(Eleve.classe_id.in_(classes_ids))
        if not is_super_admin and school_id:
            eleves_query = eleves_query.filter(Eleve.school_id == school_id)
        eleves = eleves_query.all()

        total_recettes = sum([getattr(e, 'montant_paye', 0.0) or 0.0 for e in eleves])
        total_depenses = 0.0  # Ajustable si une table de dépenses liée au school_id existe
        resultat_net = total_recettes - total_depenses

        st.markdown(f"### Bilan Financier — **{school_name} ({cycle_en_cours})**")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Recettes Encaissées", f"{total_recettes:,.0f} FCFA")
        with col2:
            st.metric("Total Dépenses Sorties", f"{total_depenses:,.0f} FCFA")
        with col3:
            st.metric(
                "Résultat Net de Trésorerie", 
                f"{resultat_net:,.0f} FCFA", 
                delta="Bénéficiaire" if resultat_net >= 0 else "Déficitaire",
                delta_normal="normal" if resultat_net >= 0 else "inverse"
            )

        st.markdown("---")
        st.markdown(f"### Bilan Consolidé par Classe — **{school_name} ({cycle_en_cours})**")

        rapport_data = []
        for classe in classes_cycle:
            eleves_classe = [e for e in eleves if e.classe_id == classe.id]
            recettes_classe = sum([getattr(e, 'montant_paye', 0.0) or 0.0 for e in eleves_classe])
            
            rapport_data.append({
                "Classe": classe.libelle,
                "Effectif": len(eleves_classe),
                "Recettes (FCFA)": recettes_classe
            })

        if not rapport_data:
            st.info("Aucune donnée à consolider pour le moment.")
        else:
            df_rapport = pd.DataFrame(rapport_data)
            st.dataframe(df_rapport, use_container_width=True)

    finally:
        db.close()
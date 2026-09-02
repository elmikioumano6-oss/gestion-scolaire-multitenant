import streamlit as st
import pandas as pd
from database.db_config import SessionLocal
from database.models import Classe, Eleve, School, Paiement, Depense

def afficher_rapports():
    st.subheader("📑 Rapports & Bilan Financier Consolidé")
    st.markdown("Synthèse macroscopique des flux de trésorerie, suivi consolidé par établissement et par cycle.")
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
        # Récupération optionnelle des classes du cycle
        classes_query = db.query(Classe).filter(Classe.cycle == cycle_en_cours)
        if not is_super_admin and school_id:
            classes_query = classes_query.filter(Classe.school_id == school_id)
        classes_cycle = classes_query.all()

        classes_dict = {c.id: c for c in classes_cycle}
        classes_ids = list(classes_dict.keys())

        # Récupération des élèves (filtrés par classes du cycle si elles existent, sinon tous les élèves de l'école)
        eleves_query = db.query(Eleve)
        if not is_super_admin and school_id:
            eleves_query = eleves_query.filter(Eleve.school_id == school_id)
        
        if classes_ids:
            eleves_query = eleves_query.filter(Eleve.classe_id.in_(classes_ids))
        
        eleves = eleves_query.all()
        eleves_ids = [e.id for e in eleves]

        # Calcul des recettes réelles depuis la table Paiement
        total_recettes = 0.0
        if eleves_ids:
            paiements_eleves = db.query(Paiement).filter(Paiement.eleve_id.in_(eleves_ids)).all()
            total_recettes = sum(p.montant for p in paiements_eleves) if paiements_eleves else 0.0

        # Calcul des dépenses réelles depuis la table Depense
        depenses_query = db.query(Depense).filter(Depense.cycle == cycle_en_cours)
        if not is_super_admin and school_id:
            depenses_query = depenses_query.filter(Depense.school_id == school_id)
        depenses_list = depenses_query.all()
        total_depenses = sum(d.montant for d in depenses_list) if depenses_list else 0.0

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
                delta_color="normal" if resultat_net >= 0 else "inverse"
            )

        st.markdown("---")
        st.markdown(f"### Bilan Consolidé par Classe — **{school_name} ({cycle_en_cours})**")

        if not classes_cycle:
            st.info(f"📌 Aucune classe configurée pour le cycle **{cycle_en_cours}**. Veuillez en créer pour afficher la ventilation détaillée.")
        else:
            rapport_data = []
            for classe in classes_cycle:
                eleves_classe = [e for e in eleves if e.classe_id == classe.id]
                eleves_classe_ids = [e.id for e in eleves_classe]
                
                recettes_classe = 0.0
                if eleves_classe_ids:
                    p_classe = db.query(Paiement).filter(Paiement.eleve_id.in_(eleves_classe_ids)).all()
                    recettes_classe = sum(p.montant for p in p_classe) if p_classe else 0.0
                
                rapport_data.append({
                    "Classe": classe.libelle,
                    "Niveau": getattr(classe, 'niveau', 'N/D'),
                    "Effectif": len(eleves_classe),
                    "Recettes (FCFA)": recettes_classe
                })

            df_rapport = pd.DataFrame(rapport_data)
            st.dataframe(df_rapport, use_container_width=True)

    finally:
        db.close()

# Alias de compatibilité exhaustive pour le routeur app.py
afficher_rapports = afficher_rapports
import streamlit as st
import pandas as pd
from database.db_config import SessionLocal
from database.models import Classe, Eleve, School, Paiement, Depense

def afficher_rapports():
    st.subheader("📑 Rapports & Bilan Financier Consolidé")
    st.markdown("Synthèse macroscopique des flux de trésorerie, suivi consolidé par établissement, par cycle et par poste de recette.")
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
        # Récupération des classes du cycle
        classes_query = db.query(Classe).filter(Classe.cycle == cycle_en_cours)
        if hasattr(Classe, 'deleted_at'):
            classes_query = classes_query.filter(Classe.deleted_at.is_(None))
        if not is_super_admin and school_id:
            classes_query = classes_query.filter(Classe.school_id == school_id)
        classes_cycle = classes_query.all()

        classes_dict = {c.id: c for c in classes_cycle}
        classes_ids = list(classes_dict.keys())

        # Récupération des élèves
        eleves_query = db.query(Eleve)
        if hasattr(Eleve, 'deleted_at'):
            eleves_query = eleves_query.filter(Eleve.deleted_at.is_(None))
        if not is_super_admin and school_id:
            eleves_query = eleves_query.filter(Eleve.school_id == school_id)
        if classes_ids:
            eleves_query = eleves_query.filter(Eleve.classe_id.in_(classes_ids))
        
        eleves = eleves_query.all()
        eleves_ids = [e.id for e in eleves]

        # Calcul des recettes réelles
        total_recettes = 0.0
        if eleves_ids:
            paiements_eleves = db.query(Paiement).filter(Paiement.eleve_id.in_(eleves_ids)).all()
            total_recettes = sum(p.montant for p in paiements_eleves) if paiements_eleves else 0.0

        # Calcul des dépenses réelles
        depenses_query = db.query(Depense).filter(Depense.cycle == cycle_en_cours)
        if not is_super_admin and school_id:
            depenses_query = depenses_query.filter(Depense.school_id == school_id)
        depenses_list = depenses_query.all()
        total_depenses = sum(d.montant for d in depenses_list) if depenses_list else 0.0

        resultat_net = total_recettes - total_depenses

        # Organisation en onglets pour une ergonomie professionnelle
        tab_bilan, tab_postes, tab_reductions = st.tabs([
            "📊 Bilan & Trésorerie", 
            "🏷️ Ventilation par Poste (Scolarité, COGES, etc.)", 
            "📉 Registre des Réductions"
        ])

        with tab_bilan:
            st.markdown(f"### Bilan Financier Global — **{school_name} ({cycle_en_cours})**")

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
                st.info(f"📌 Aucune classe configurée pour le cycle **{cycle_en_cours}**.")
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

        with tab_postes:
            st.markdown(f"### Ventilation Théorique par Poste de Recette — **{cycle_en_cours}**")
            st.markdown("Analyse des redevances attendues ventilées par poste (Scolarité, Inscription, COGES, Cantine, Transport).")

            total_scolarite = 0.0
            total_inscription = 0.0
            total_coges = 0.0
            total_cantine = 0.0
            total_transport = 0.0

            for classe in classes_cycle:
                eleves_classe_count = len([e for e in eleves if e.classe_id == classe.id])
                total_scolarite += float(getattr(classe, 'frais_scolarite', 0.0) or 0.0) * eleves_classe_count
                total_inscription += float(getattr(classe, 'frais_inscription', 0.0) or 0.0) * eleves_classe_count
                total_coges += float(getattr(classe, 'frais_coges', 0.0) or 0.0) * eleves_classe_count
                total_cantine += float(getattr(classe, 'frais_cantine', 0.0) or 0.0) * eleves_classe_count
                total_transport += float(getattr(classe, 'frais_transport', 0.0) or 0.0) * eleves_classe_count

            data_postes = [
                {"Poste de Recette": "Frais de Scolarité", "Montant Total Attendu (FCFA)": total_scolarite},
                {"Poste de Recette": "Frais d'Inscription", "Montant Total Attendu (FCFA)": total_inscription},
                {"Poste de Recette": "Redevance COGES", "Montant Total Attendu (FCFA)": total_coges},
                {"Poste de Recette": "Frais de Cantine", "Montant Total Attendu (FCFA)": total_cantine},
                {"Poste de Recette": "Frais de Transport", "Montant Total Attendu (FCFA)": total_transport},
            ]

            df_postes = pd.DataFrame(data_postes)
            st.dataframe(df_postes, use_container_width=True)

        with tab_reductions:
            st.markdown(f"### Registre Nominatif des Réductions & Exonérations — **{cycle_en_cours}**")
            st.markdown("Suivi détaillé de tous les élèves bénéficiant d'une remise sur leur scolarité.")

            eleves_avec_reduction = [e for e in eleves if float(getattr(e, 'montant_reduction', 0.0) or 0.0) > 0]

            if not eleves_avec_reduction:
                st.info("📌 Aucune réduction ou exonération n'a été enregistrée pour les élèves de ce cycle.")
            else:
                data_red = []
                total_remises = 0.0
                for e in eleves_avec_reduction:
                    classe = classes_dict.get(e.classe_id) if e.classe_id else None
                    montant_red = float(e.montant_reduction or 0.0)
                    total_remises += montant_red
                    
                    data_red.append({
                        "Matricule": getattr(e, 'matricule', 'N/A'),
                        "Élève": f"{e.nom} {e.prenom}",
                        "Classe": classe.libelle if classe else "Non assignée",
                        "Type / Motif de Réduction": getattr(e, 'type_reduction', 'Standard') or 'Standard',
                        "Montant Réduction (FCFA)": montant_red
                    })

                df_red = pd.DataFrame(data_red)
                st.dataframe(df_red, use_container_width=True)
                st.metric("Total Cumulé des Remises Accordées", f"{total_remises:,.0f} FCFA")

    finally:
        db.close()

# Alias de compatibilité exhaustive pour le routeur app.py
afficher_rapports = afficher_rapports
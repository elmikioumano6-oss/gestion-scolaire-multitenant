import streamlit as st
import pandas as pd
from database.db_config import SessionLocal
from database.models import Classe, Eleve, School, Paiement

def afficher_tableau_finances():
    st.subheader("📈 Tableau de Bord Financier Global")
    st.markdown("Vue macroscopique incluant la ventilation des cotisations par classe, cycle et établissement.")
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

        total_classes = len(classes_cycle)
        total_eleves = len(eleves)
        
        budget_attendu = 0.0
        total_encaisse = 0.0

        for eleve in eleves:
            classe = classes_dict.get(eleve.classe_id) if eleve.classe_id else None
            frais_scol = getattr(classe, 'frais_scolarite', 65000.0) or 65000.0
            frais_inscr = getattr(classe, 'frais_inscription', 0.0) or 0.0
            budget_attendu += (frais_scol + frais_inscr)
            
            # Somme réelle des paiements de l'élève
            paiements_eleve = db.query(Paiement).filter(Paiement.eleve_id == eleve.id).all()
            total_encaisse += sum(p.montant for p in paiements_eleve) if paiements_eleve else 0.0

        taux = (total_encaisse / budget_attendu * 100) if budget_attendu > 0 else 0.0

        st.markdown(f"### Tableau Financier — **{school_name} ({cycle_en_cours})**")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Classes Actives", total_classes)
        with col2:
            st.metric("Élèves Inscrits", total_eleves)
        with col3:
            st.metric("Budget Attendu", f"{budget_attendu:,.0f} FCFA")
        with col4:
            st.metric("Total Encaissé", f"{total_encaisse:,.0f} FCFA", delta=f"{taux:.1f}%")

        st.markdown("---")
        st.markdown(f"### Répartition Financière par Classe — **{cycle_en_cours}**")

        if not classes_cycle:
            st.info(f"📌 Aucune classe configurée pour le cycle **{cycle_en_cours}**. Veuillez en créer pour afficher la ventilation détaillée.")
        else:
            repartition_data = []
            for classe in classes_cycle:
                eleves_classe = [e for e in eleves if e.classe_id == classe.id]
                nb_eleves = len(eleves_classe)
                frais = (getattr(classe, 'frais_scolarite', 65000.0) or 65000.0) + (getattr(classe, 'frais_inscription', 0.0) or 0.0)
                attendu_classe = nb_eleves * frais
                
                encaisse_classe = 0.0
                for e in eleves_classe:
                    p_eleve = db.query(Paiement).filter(Paiement.eleve_id == e.id).all()
                    encaisse_classe += sum(p.montant for p in p_eleve) if p_eleve else 0.0

                repartition_data.append({
                    "Classe": classe.libelle,
                    "Niveau": getattr(classe, 'niveau', 'N/D'),
                    "Effectif": nb_eleves,
                    "Attendu (FCFA)": attendu_classe,
                    "Encaissé (FCFA)": encaisse_classe,
                    "Reste (FCFA)": max(0.0, attendu_classe - encaisse_classe)
                })

            df_rep = pd.DataFrame(repartition_data)
            st.dataframe(df_rep, use_container_width=True)

    finally:
        db.close()

# Alias de compatibilité exhaustive pour le routeur app.py
afficher_tableau_finances = afficher_tableau_finances
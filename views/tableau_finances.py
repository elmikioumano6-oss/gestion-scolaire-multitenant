import streamlit as st
import pandas as pd
from database.db_config import SessionLocal
from database.models import Classe, Eleve, School

def afficher_tableau_finances():
    st.subheader("📈 Tableau de Bord Financier Global")
    st.markdown("Vue macroscopique incluant la ventilation des cotisations par classe, cycle et établissement.")
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
            st.info(f"📌 **{school_name}** — Aucune classe disponible pour le cycle **{cycle_en_cours}**.")
            return

        classes_dict = {c.id: c for c in classes_cycle}
        classes_ids = list(classes_dict.keys())

        eleves_query = db.query(Eleve).filter(Eleve.classe_id.in_(classes_ids))
        if not is_super_admin and school_id:
            eleves_query = eleves_query.filter(Eleve.school_id == school_id)
        eleves = eleves_query.all()

        total_classes = len(classes_cycle)
        total_eleves = len(eleves)
        
        budget_attendu = 0.0
        total_encaisse = 0.0

        for eleve in eleves:
            classe = classes_dict.get(eleve.classe_id)
            frais_scol = getattr(classe, 'frais_scolarite', 0.0) or 0.0
            frais_inscr = getattr(classe, 'frais_inscription', 0.0) or 0.0
            budget_attendu += (frais_scol + frais_inscr)
            total_encaisse += (getattr(eleve, 'montant_paye', 0.0) or 0.0)

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

        repartition_data = []
        for classe in classes_cycle:
            eleves_classe = [e for e in eleves if e.classe_id == classe.id]
            nb_eleves = len(eleves_classe)
            frais = (getattr(classe, 'frais_scolarite', 0.0) or 0.0) + (getattr(classe, 'frais_inscription', 0.0) or 0.0)
            attendu_classe = nb_eleves * frais
            encaisse_classe = sum([getattr(e, 'montant_paye', 0.0) or 0.0 for e in eleves_classe])

            repartition_data.append({
                "Classe": classe.libelle,
                "Niveau": classe.niveau,
                "Effectif": nb_eleves,
                "Attendu (FCFA)": attendu_classe,
                "Encaissé (FCFA)": encaisse_classe,
                "Reste (FCFA)": attendu_classe - encaisse_classe
            })

        if not repartition_data:
            st.info("Aucune donnée financière à ventiler pour le moment.")
        else:
            df_rep = pd.DataFrame(repartition_data)
            st.dataframe(df_rep, use_container_width=True)

    finally:
        db.close()
import streamlit as st
import pandas as pd
from database.db_config import SessionLocal
from database.models import Classe, Eleve, User, Paiement
from sqlalchemy import func

def afficher_tableau_de_bord():
    st.subheader("📊 Tableau de Bord Exécutif & Pilotage")
    st.markdown("Vue d'ensemble de la performance administrative, financière et pédagogique de l'établissement.")
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
        # Isolation stricte multi-écoles et multi-cycles pour les classes
        classes_query = db.query(Classe).filter(Classe.cycle == cycle_en_cours)
        if not is_super_admin and school_id:
            classes_query = classes_query.filter(Classe.school_id == school_id)
        classes_cycle = classes_query.all()

        classes_ids = [c.id for c in classes_cycle]

        # Isolation stricte multi-écoles pour les élèves
        eleves_query = db.query(Eleve)
        if classes_ids:
            eleves_query = eleves_query.filter(Eleve.classe_id.in_(classes_ids))
        if not is_super_admin and school_id:
            eleves_query = eleves_query.filter(Eleve.school_id == school_id)
        eleves = eleves_query.all()

        eleves_ids = [e.id for e in eleves]

        # Isolation stricte multi-écoles pour les enseignants / utilisateurs
        users_query = db.query(User)
        if not is_super_admin and school_id:
            users_query = users_query.filter(User.school_id == school_id)
        users = users_query.all()

        total_eleves = len(eleves)
        total_classes = len(classes_cycle)
        total_enseignants = len([u for u in users if str(u.role).lower() in ["prof", "enseignant"]])

        # Calcul sécurisé des recettes réelles basées sur la table Paiement pour ces élèves
        total_recettes = 0.0
        if eleves_ids:
            recettes_query = db.query(func.sum(Paiement.montant)).filter(Paiement.eleve_id.in_(eleves_ids))
            if not is_super_admin and school_id:
                recettes_query = recettes_query.filter(Paiement.school_id == school_id)
            res_recettes = recettes_query.scalar()
            if res_recettes:
                total_recettes = float(res_recettes)

        total_attendu = 0.0
        for eleve in eleves:
            classe = next((c for c in classes_cycle if c.id == eleve.classe_id), None)
            if classe:
                frais_scol = getattr(classe, 'frais_scolarite', 0.0) or 0.0
                frais_inscr = getattr(classe, 'frais_inscription', 0.0) or 0.0
                total_attendu += (frais_scol + frais_inscr)

        reste_a_recouvrer = total_attendu - total_recettes
        taux = (total_recettes / total_attendu * 100) if total_attendu > 0 else 0.0

        st.markdown(f"### Tableau de Bord — **{school_name} ({cycle_en_cours})**")

        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("Total Élèves", total_eleves, delta="Actifs")
        with col2:
            st.metric("Classes", total_classes, delta="Actives")
        with col3:
            st.metric("Enseignants", total_enseignants, delta="Corps professoral")
        with col4:
            st.metric("Recettes Globales", f"{total_recettes:,.0f} FCFA", delta="Trésorerie")
        with col5:
            st.metric("Reste à Recouvrer", f"{reste_a_recouvrer:,.0f} FCFA", delta=f"Taux: {taux:.1f}%")

        st.markdown("---")
        st.markdown("### Répartition des Effectifs par Classe")

        if not classes_cycle:
            st.info(f"Aucune classe disponible pour le cycle **{cycle_en_cours}** dans cet établissement.")
        else:
            data_effectifs = []
            for classe in classes_cycle:
                nb_eleves_classe = len([e for e in eleves if e.classe_id == classe.id])
                data_effectifs.append({
                    "Classe": classe.libelle,
                    "Niveau": classe.niveau,
                    "Effectif": nb_eleves_classe
                })
            df_eff = pd.DataFrame(data_effectifs)
            st.dataframe(df_eff, use_container_width=True)

    finally:
        db.close()
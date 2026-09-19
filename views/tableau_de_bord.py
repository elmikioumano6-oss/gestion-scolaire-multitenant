import streamlit as st
import pandas as pd
from database.db_config import SessionLocal
from database.models import Classe, Eleve, User, Paiement, School, EmploiDuTemps
from database.queries import get_classes_cached, get_matieres_cached
from sqlalchemy import func

def afficher_tableau_de_bord():
    st.subheader("📊 Tableau de Bord Exécutif & Pilotage")
    st.markdown("Vue d'ensemble de la performance administrative, financière et pédagogique de l'établissement avec isolation multi-tenant stricte.")
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
        target_school_id = school_id
        if is_super_admin and not target_school_id:
            ecole_defaut = db.query(School).first()
            target_school_id = ecole_defaut.id if ecole_defaut else 1

        ecole_active_id = school_id if school_id else target_school_id

        # Isolation stricte multi-écoles et multi-cycles pour les classes
        classes_query = db.query(Classe).filter(Classe.cycle == cycle_en_cours)
        if hasattr(Classe, "deleted_at"):
            classes_query = classes_query.filter(Classe.deleted_at.is_(None))
        if not is_super_admin and school_id:
            classes_query = classes_query.filter(Classe.school_id == school_id)
        else:
            classes_query = classes_query.filter(Classe.school_id == ecole_active_id)
        classes_cycle = classes_query.all()

        classes_ids = [c.id for c in classes_cycle]

        # Isolation stricte multi-écoles et multi-cycles pour les élèves
        eleves_query = db.query(Eleve)
        if hasattr(Eleve, "deleted_at"):
            eleves_query = eleves_query.filter(Eleve.deleted_at.is_(None))

        if classes_ids:
            eleves_query = eleves_query.filter(Eleve.classe_id.in_(classes_ids))
        else:
            eleves_query = eleves_query.filter(Eleve.classe_id == -1)

        if not is_super_admin and school_id:
            eleves_query = eleves_query.filter(Eleve.school_id == school_id)
        else:
            eleves_query = eleves_query.filter(Eleve.school_id == ecole_active_id)
        eleves = eleves_query.all()

        eleves_ids = [e.id for e in eleves]

        # Calcul strict des enseignants rattachés aux classes de ce cycle (via l'emploi du temps ou la table des profs)
        total_enseignants = 0
        if classes_ids:
            # Récupérer les enseignants uniques enseignant dans les classes de ce cycle
            profs_edt = db.query(EmploiDuTemps.enseignant).filter(
                EmploiDuTemps.classe_id.in_(classes_ids),
                EmploiDuTemps.enseignant.isnot(None),
                EmploiDuTemps.enseignant != ""
            ).distinct().all()
            total_enseignants = len(profs_edt)
            
            # Fallback si l'emploi du temps n'est pas rempli mais qu'il y a des profs dans l'école
            if total_enseignants == 0:
                users_query = db.query(User)
                if not is_super_admin and school_id:
                    users_query = users_query.filter(User.school_id == school_id)
                else:
                    users_query = users_query.filter(User.school_id == ecole_active_id)
                users = users_query.all()
                total_enseignants = len([u for u in users if str(getattr(u, 'role', '')).lower() in ["prof", "enseignant"]])

        total_eleves = len(eleves)
        total_classes = len(classes_cycle)

        # Calcul sécurisé des recettes réelles basées sur la table Paiement pour ces élèves
        total_recettes = 0.0
        if eleves_ids:
            recettes_query = db.query(func.sum(Paiement.montant)).filter(Paiement.eleve_id.in_(eleves_ids))
            if not is_super_admin and school_id:
                recettes_query = recettes_query.filter(Paiement.school_id == school_id)
            else:
                recettes_query = recettes_query.filter(Paiement.school_id == ecole_active_id)
            res_recettes = recettes_query.scalar()
            if res_recettes:
                total_recettes = float(res_recettes)

        total_attendu = 0.0
        for eleve in eleves:
            classe = next((c for c in classes_cycle if c.id == eleve.classe_id), None)
            if classe:
                frais_scol = getattr(classe, 'frais_scolarite', 0.0) or 0.0
                frais_inscr = getattr(classe, 'frais_inscription', 0.0) or 0.0
                total_attendu += (float(frais_scol) + float(frais_inscr))

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
        st.markdown(f"### Répartition des Effectifs par Classe — **{cycle_en_cours}**")

        if not classes_cycle:
            st.info(f"Aucune classe disponible pour le cycle **{cycle_en_cours}** dans cet établissement.")
        else:
            data_effectifs = []
            for classe in classes_cycle:
                nb_eleves_classe = len([e for e in eleves if e.classe_id == classe.id])
                classe_lib = classe.libelle if hasattr(classe, 'libelle') and classe.libelle else getattr(classe, 'nom', f"Classe {classe.id}")
                classe_niv = getattr(classe, 'niveau', 'N/D')
                data_effectifs.append({
                    "Classe": classe_lib,
                    "Niveau": classe_niv,
                    "Effectif": nb_eleves_classe
                })
            df_eff = pd.DataFrame(data_effectifs)
            st.dataframe(df_eff, use_container_width=True, hide_index=True)

    finally:
        db.close()

# Alias de compatibilité
afficher_tableau_de_bord = afficher_tableau_de_bord
afficher_tableau_bord = afficher_tableau_de_bord
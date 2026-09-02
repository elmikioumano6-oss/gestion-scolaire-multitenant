import streamlit as st
import pandas as pd
from database.db_config import SessionLocal
from database.models import Classe, Eleve, School

def afficher_stats_encaissements():
    st.subheader("📊 Statistiques des Encaissements")
    st.markdown("Analyse des encaissements, flux de trésorerie et taux de recouvrement par cycle et par établissement.")
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
        # Isolation multi-écoles et multi-cycles
        classes_query = db.query(Classe).filter(Classe.cycle == cycle_en_cours)
        if not is_super_admin and school_id:
            classes_query = classes_query.filter(Classe.school_id == school_id)
        
        classes_cycle = classes_query.all()

        if not classes_cycle:
            st.info(f"📌 **{school_name}** — Aucune classe active pour le cycle **{cycle_en_cours}**.")
            return

        classes_dict = {c.id: c for c in classes_cycle}
        classes_ids = list(classes_dict.keys())

        # Récupération des élèves inscrits dans ces classes
        eleves_query = db.query(Eleve).filter(Eleve.classe_id.in_(classes_ids))
        if not is_super_admin and school_id:
            eleves_query = eleves_query.filter(Eleve.school_id == school_id)
        eleves = eleves_query.all()

        total_attendu = 0.0
        total_recouvre = 0.0
        data = []

        for eleve in eleves:
            classe = classes_dict.get(eleve.classe_id)
            frais_scol = getattr(classe, 'frais_scolarite', 0.0) or 0.0
            frais_inscr = getattr(classe, 'frais_inscription', 0.0) or 0.0
            total_du = frais_scol + frais_inscr
            
            montant_paye = getattr(eleve, 'montant_paye', 0.0) or 0.0
            
            total_attendu += total_du
            total_recouvre += montant_paye

            data.append({
                "Élève": f"{getattr(eleve, 'nom', '')} {getattr(eleve, 'prenom', '')}".strip() or "Élève",
                "Classe": classe.libelle if classe else "N/D",
                "Montant Dû (FCFA)": total_du,
                "Montant Payé (FCFA)": montant_paye,
                "Solde Restant (FCFA)": total_du - montant_paye
            })

        reste_a_recouvrer = total_attendu - total_recouvre
        taux = (total_recouvre / total_attendu * 100) if total_attendu > 0 else 0.0

        st.markdown(f"### Tableau de Bord Financier — **{school_name} ({cycle_en_cours})**")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Chiffre d'Affaires Attendu (Net)", f"{total_attendu:,.0f} FCFA")
        with col2:
            st.metric("Total Global Recouvré", f"{total_recouvre:,.0f} FCFA", delta=f"{taux:.1f}% de réalisation")
        with col3:
            st.metric("Créances (Reste à Recouvrer)", f"{reste_a_recouvrer:,.0f} FCFA")

        st.markdown("---")
        st.markdown(f"### Visualisation : Attendu vs Recouvré — **{cycle_en_cours}**")

        if not data:
            st.info("Aucun élève enregistré pour ce cycle dans cet établissement.")
        else:
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True)

    finally:
        db.close()
import streamlit as st
import pandas as pd
from database.db_config import SessionLocal
from database.models import Classe, Eleve, School, Paiement

def afficher_stats_encaissements():
    st.subheader("📊 Statistiques des Encaissements")
    st.markdown("Analyse des encaissements, flux de trésorerie et taux de recouvrement par cycle et par établissement.")
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
        # Récupération des classes du cycle pour information/filtrage
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

        total_attendu = 0.0
        total_recouvre = 0.0
        data = []

        for eleve in eleves:
            classe = classes_dict.get(eleve.classe_id) if eleve.classe_id else None
            
            # Récupération des frais de la classe
            frais_scol = float(getattr(classe, 'frais_scolarite', 0.0) or 0.0)
            frais_inscr = float(getattr(classe, 'frais_inscription', 0.0) or 0.0)
            frais_coges = float(getattr(classe, 'frais_coges', 0.0) or 0.0)
            
            # S'il n'y a pas de frais configurés sur la classe, on prend une base de secours, sinon la somme brute
            frais_brut_total = frais_scolarite_base = (frais_scol + frais_inscr + frais_coges) if (frais_scol + frais_inscr + frais_coges) > 0 else 65000.0
            
            # Prise en compte de la réduction personnelle de l'élève
            reduction = float(getattr(eleve, 'montant_reduction', 0.0) or 0.0)
            total_du_net = max(0.0, frais_brut_total - reduction)
            
            # Somme des paiements réels de l'élève
            paiements_eleve = db.query(Paiement).filter(Paiement.eleve_id == eleve.id).all()
            montant_paye = sum(float(p.montant) for p in paiements_eleve) if paiements_eleve else 0.0
            
            total_attendu += total_du_net
            total_recouvre += montant_paye

            solde_restant = total_du_net - montant_paye

            data.append({
                "Élève": f"{getattr(eleve, 'nom', '')} {getattr(eleve, 'prenom', '')}".strip() or "Élève",
                "Classe": classe.libelle if classe else "Non assignée",
                "Montant Dû (Net)": total_du_net,
                "Montant Payé": montant_paye,
                "Solde Restant": solde_restant
            })

        reste_a_recouvrer = max(0.0, total_attendu - total_recouvre)
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
            st.info(f"📌 Aucune donnée financière ou élève enregistré pour le cycle **{cycle_en_cours}** dans l'établissement **{school_name}**.")
        else:
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True)

    finally:
        db.close()

# Alias de compatibilité
afficher_stats_encaissements = afficher_stats_encaissements
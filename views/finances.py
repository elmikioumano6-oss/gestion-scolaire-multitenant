import streamlit as st
import pandas as pd
from datetime import datetime
from database.db_config import SessionLocal
from database.models import Paiement, Eleve, School

def afficher_finances():
    st.subheader("💰 Gestion Financière & Suivi de Trésorerie")
    st.markdown("Tableau de bord des encaissements et suivi budgétaire avec isolation multi-tenant stricte.")
    st.markdown("---")

    school_id = st.session_state.get("school_id")
    is_super_admin = st.session_state.get("is_super_admin", False)

    if not school_id and not is_super_admin:
        st.warning("⚠️ Veuillez vous connecter pour accéder à cette section.")
        return

    db = SessionLocal()
    try:
        # Filtrage des paiements par établissement
        query_paiements = db.query(Paiement)
        if not is_super_admin and school_id:
            query_paiements = query_paiements.filter(Paiement.school_id == school_id)
        paiements = query_paiements.all()

        total_recettes = sum(p.montant for p in paiements) if paiements else 0.0

        # Calcul du nombre d'élèves de l'école pour estimer le prévisionnel
        query_eleves = db.query(Eleve)
        if not is_super_admin and school_id:
            query_eleves = query_eleves.filter(Eleve.school_id == school_id)
        total_eleves = query_eleves.count()

        total_attendu = total_eleves * 65000  # Base forfaitaire annuelle par élève
        solde_restant = max(0.0, total_attendu - total_recettes)
        taux_recouvrement = (total_recettes / total_attendu * 100) if total_attendu > 0 else 0.0

        # --- KPIs FINANCIERS ---
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("💵 Total Encaissé", f"{total_recettes:,.0f} FCFA", delta="Recettes")
        with col2:
            st.metric("📊 Objectif Prévisionnel", f"{total_attendu:,.0f} FCFA", delta="Attendu")
        with col3:
            st.metric("📉 Reste à Recouvrer", f"{solde_restant:,.0f} FCFA", delta=f"{taux_recouvrement:.1f}% recouvré")

        st.markdown("---")
        st.markdown("### 📋 Historique Détaillé des Encaissements")

        if not paiements:
            st.info("Aucun encaissement enregistré pour le moment.")
        else:
            data = []
            for p in paiements:
                eleve = db.query(Eleve).filter(Eleve.id == p.eleve_id).first()
                nom_eleve = f"{eleve.nom} {eleve.prenom}" if eleve else "Élève inconnu"
                matricule = eleve.matricule if eleve else "N/D"
                
                data.append({
                    "Référence": p.reference_recu,
                    "Date": p.date_paiement.strftime("%d/%m/%Y %H:%M") if p.date_paiement else "N/D",
                    "Matricule": matricule,
                    "Élève": nom_eleve,
                    "Montant (FCFA)": f"{p.montant:,.0f}",
                    "Motif": p.motif,
                    "Mode": p.mode_reglement,
                    "Caissier(e)": p.agent_caisse or "N/D"
                })
            df_finances = pd.DataFrame(data)
            st.dataframe(df_finances, use_container_width=True)

    finally:
        db.close()
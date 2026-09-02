import streamlit as st
import pandas as pd
from database.db_config import SessionLocal
from database.models import Eleve, Classe, School

def afficher_espace_parent():
    st.subheader("👨‍👩‍👧 Espace Famille & Suivi Élève")
    st.markdown("Consultation sécurisée des notes, du comportement et de la scolarité par établissement.")
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
        st.markdown(f"### Portail Parents — **{school_name} ({cycle_en_cours})**")

        # Isolation stricte multi-écoles pour récupérer les élèves de l'établissement
        eleves_query = db.query(Eleve)
        if not is_super_admin and school_id:
            eleves_query = eleves_query.filter(Eleve.school_id == school_id)
        
        eleves = eleves_query.all()

        if not eleves:
            st.info("Aucun élève enregistré dans cet établissement pour le moment.")
        else:
            noms_eleves = [f"{e.nom} {e.prenom}" for e in eleves]
            eleve_choisi = st.selectbox("Sélectionner l'enfant à consulter", noms_eleves)

            eleve_obj = next((e for e in eleves if f"{e.nom} {e.prenom}" == eleve_choisi), None)

            if eleve_obj:
                classe = db.query(Classe).filter(Classe.id == eleve_obj.classe_id).first()
                classe_nom = classe.libelle if classe else "Non assignée"

                st.success(f"📌 Suivi de l'élève : **{eleve_obj.nom} {eleve_obj.prenom}** | Classe : **{classe_nom}**")

                tab1, tab2, tab3 = st.tabs(["📚 Notes & Évaluations", "📋 Assiduité & Absences", "💳 Situation Financière"])

                with tab1:
                    st.markdown("#### Bulletins et Notes Récentes")
                    st.info("Aucune note enregistrée pour le moment.")

                with tab2:
                    st.markdown("#### Suivi des Absences et Retards")
                    st.info("Aucune absence signalée.")

                with tab3:
                    st.markdown("#### Situation des Paiements")
                    montant_du = (getattr(classe, 'frais_scolarite', 0.0) or 0.0) if classe else 0.0
                    montant_paye = getattr(eleve_obj, 'montant_paye', 0.0) or 0.0
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Montant Total Dû", f"{montant_du:,.0f} FCFA")
                    with col2:
                        st.metric("Montant Versé", f"{montant_paye:,.0f} FCFA")
                    with col3:
                        st.metric("Solde Restant", f"{montant_du - montant_paye:,.0f} FCFA")

    finally:
        db.close()
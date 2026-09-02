import streamlit as st
import pandas as pd
from database.db_config import SessionLocal
from database.models import Classe, Eleve, School, Paiement

def afficher_soldes_impayes():
    st.subheader("⚠️ Suivi des Soldes & Impayés")
    st.markdown("Tableau de contrôle des créances, identification des retards de paiement et édition des avis de relance.")
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

        # Récupération des élèves de l'établissement (filtrés par classes du cycle si elles existent)
        eleves_query = db.query(Eleve)
        if not is_super_admin and school_id:
            eleves_query = eleves_query.filter(Eleve.school_id == school_id)
        
        if classes_ids:
            eleves_query = eleves_query.filter(Eleve.classe_id.in_(classes_ids))
        
        eleves = eleves_query.all()

        impayes_data = []
        for eleve in eleves:
            classe = classes_dict.get(eleve.classe_id) if eleve.classe_id else None
            frais_scol = getattr(classe, 'frais_scolarite', 65000.0) or 65000.0
            frais_inscr = getattr(classe, 'frais_inscription', 0.0) or 0.0
            total_du = frais_scol + frais_inscr
            
            # Utilisation de la table Paiement comme source de vérité unique
            paiements_eleve = db.query(Paiement).filter(Paiement.eleve_id == eleve.id).all()
            montant_paye = sum(p.montant for p in paiements_eleve) if paiements_eleve else 0.0
            
            solde_restant = total_du - montant_paye

            if solde_restant > 0:
                impayes_data.append({
                    "Élève": f"{getattr(eleve, 'nom', '')} {getattr(eleve, 'prenom', '')}".strip() or "Élève",
                    "Classe": classe.libelle if classe else "Non assignée",
                    "Total Dû (FCFA)": total_du,
                    "Déjà Payé (FCFA)": montant_paye,
                    "Reste à Payer (FCFA)": solde_restant
                })

        st.markdown(f"### Liste des Impayés — **{school_name} ({cycle_en_cours})**")

        if not eleves:
            st.info(f"📌 Aucun élève enregistré pour le cycle **{cycle_en_cours}** dans l'établissement **{school_name}**.")
        elif not impayes_data:
            st.success(f"🎉 Excellent ! Aucun impayé enregistré pour le cycle **{cycle_en_cours}** dans cet établissement.")
        else:
            df_impayes = pd.DataFrame(impayes_data)
            st.dataframe(df_impayes, use_container_width=True)

    finally:
        db.close()

# Alias de compatibilité exhaustive pour le routeur app.py
afficher_soldes_impayes = afficher_soldes_impayes
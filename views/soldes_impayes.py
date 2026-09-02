import streamlit as st
import pandas as pd
from database.db_config import SessionLocal
from database.models import Classe, Eleve, School

def afficher_soldes_impayes():
    st.subheader("⚠️ Suivi des Soldes & Impayés")
    st.markdown("Tableau de contrôle des créances, identification des retards de paiement et édition des avis de relance.")
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
            st.info(f"📌 **{school_name}** — Aucune classe disponible pour le cycle **{cycle_en_cours}**. Veuillez d'abord en créer dans le menu 'Classes & Tarifs'.")
            return

        classes_dict = {c.id: c for c in classes_cycle}
        classes_ids = list(classes_dict.keys())

        eleves_query = db.query(Eleve).filter(Eleve.classe_id.in_(classes_ids))
        if not is_super_admin and school_id:
            eleves_query = eleves_query.filter(Eleve.school_id == school_id)
        eleves = eleves_query.all()

        impayes_data = []
        for eleve in eleves:
            classe = classes_dict.get(eleve.classe_id)
            frais_scol = getattr(classe, 'frais_scolarite', 0.0) or 0.0
            frais_inscr = getattr(classe, 'frais_inscription', 0.0) or 0.0
            total_du = frais_scol + frais_inscr
            montant_paye = getattr(eleve, 'montant_paye', 0.0) or 0.0
            solde_restant = total_du - montant_paye

            if solde_restant > 0:
                impayes_data.append({
                    "Élève": f"{getattr(eleve, 'nom', '')} {getattr(eleve, 'prenom', '')}".strip() or "Élève",
                    "Classe": classe.libelle if classe else "N/D",
                    "Total Dû (FCFA)": total_du,
                    "Déjà Payé (FCFA)": montant_paye,
                    "Reste à Payer (FCFA)": solde_restant
                })

        st.markdown(f"### Liste des Impayés — **{school_name} ({cycle_en_cours})**")

        if not impayes_data:
            st.success(f"🎉 Excellent ! Aucun impayé enregistré pour le cycle {cycle_en_cours} dans cet établissement.")
        else:
            df_impayes = pd.DataFrame(impayes_data)
            st.dataframe(df_impayes, use_container_width=True)

    finally:
        db.close()
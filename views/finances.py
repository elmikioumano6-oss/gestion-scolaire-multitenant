from database.db_config import SessionLocal
from database.models import Classe, Eleve, Paiement, School
import pandas as pd
import streamlit as st

def afficher_tableau_finances():
    st.subheader("📊 Répartition Financière par Classe")
    st.markdown("Suivi consolidé de l'attendu, des encaissements et du reste à recouvrer par classe.")
    st.markdown("---")

    school_id = st.session_state.get("school_id")
    is_super_admin = st.session_state.get("is_super_admin", False)
    cycle_en_cours = st.session_state.get("cycle_actif", "Collège")
    school_name = st.session_state.get("school_name", "Établissement")

    if not school_id and not is_super_admin:
        st.warning("⚠️ Veuillez vous connecter pour accéder à cette section.")
        return

    db = SessionLocal()
    try:
        # Récupération des classes de l'établissement
        query_classes = db.query(Classe).filter(Classe.school_id == school_id)
        if hasattr(Classe, "deleted_at"):
            query_classes = query_classes.filter(Classe.deleted_at.is_(None))
        
        # Filtrage optionnel par cycle si la colonne existe
        classes = query_classes.all()

        data_tableau = []
        for c in classes:
            # Récupérer tous les élèves de cette classe
            query_eleves = db.query(Eleve).filter(Eleve.classe_id == c.id)
            if hasattr(Eleve, "deleted_at"):
                query_eleves = query_eleves.filter(Eleve.deleted_at.is_(None))
            eleves_classe = query_eleves.all()
            
            effectif = len(eleves_classe)
            
            # Calcul rigoureux de l'attendu net pour cette classe (basé sur chaque élève + frais + réductions)
            attendu_classe = 0.0
            eleves_ids = []
            for e in eleves_classe:
                eleves_ids.append(e.id)
                frais_scol = float(getattr(c, "frais_scolarite", 0.0) or 0.0)
                frais_inscr = float(getattr(c, "frais_inscription", 0.0) or 0.0)
                frais_coges = float(getattr(c, "frais_coges", 0.0) or 0.0)
                frais_cantine = float(getattr(e, "frais_cantine", getattr(c, "frais_cantine", 0.0)) or 0.0)
                frais_transport = float(getattr(e, "frais_transport", getattr(c, "frais_transport", 0.0)) or 0.0)
                frais_autres = float(getattr(e, "frais_autres", getattr(c, "frais_autres", 0.0)) or 0.0)
                
                frais_brut = frais_scol + frais_inscr + frais_coges + frais_cantine + frais_transport + frais_autres
                reduction = float(getattr(e, "montant_reduction", 0.0) or 0.0)
                attendu_classe += max(0.0, frais_brut - reduction)

            # Calcul de l'encaissé réel pour les élèves de cette classe
            encaissé_classe = 0.0
            if eleves_ids:
                paiements_classe = db.query(Paiement).filter(Paiement.eleve_id.in_(eleves_ids)).all()
                encaissé_classe = sum(p.montant for p in paiements_classe)

            # Reste à recouvrer mathématiquement exact
            reste_a_recouvrer = max(0.0, attendu_classe - encaissé_classe)

            data_tableau.append({
                "Classe": getattr(c, "libelle", "N/A"),
                "Niveau": getattr(c, "niveau", "N/A"),
                "Effectif": effectif,
                "Attendu (Net)": attendu_classe,
                "Encaissé": encaissé_classe,
                "Reste à Recouvrer": reste_a_recouvrer
            })

        if not data_tableau:
            st.info("Aucune classe enregistrée.")
        else:
            df_repartition = pd.DataFrame(data_tableau)
            
            # Affichage formaté proprement pour l'utilisateur
            df_display = df_repartition.copy()
            df_display["Attendu (Net)"] = df_display["Attendu (Net)"].apply(lambda x: f"{x:,.0f}")
            df_display["Encaissé"] = df_display["Encaissé"].apply(lambda x: f"{x:,.0f}")
            df_display["Reste à Recouvrer"] = df_display["Reste à Recouvrer"].apply(lambda x: f"{x:,.0f}")

            st.dataframe(df_display, use_container_width=True)

    finally:
        db.close()

# Alias de compatibilité
tableau_finances = afficher_tableau_finances
afficher_tableau_finances = afficher_tableau_finances
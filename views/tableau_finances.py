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
        query_classes = db.query(Classe).filter(Classe.school_id == school_id)
        if hasattr(Classe, "deleted_at"):
            query_classes = query_classes.filter(Classe.deleted_at.is_(None))
        
        if hasattr(Classe, "cycle") and cycle_en_cours:
            query_classes = query_classes.filter(Classe.cycle == cycle_en_cours)

        classes = query_classes.all()

        data_tableau = []
        total_attendu_global = 0.0
        total_encaisse_global = 0.0

        for c in classes:
            query_eleves = db.query(Eleve).filter(Eleve.classe_id == c.id)
            if hasattr(Eleve, "deleted_at"):
                query_eleves = query_eleves.filter(Eleve.deleted_at.is_(None))
            eleves_classe = query_eleves.all()
            
            effectif = len(eleves_classe)
            
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

            encaissé_classe = 0.0
            if eleves_ids:
                paiements_classe = db.query(Paiement).filter(Paiement.eleve_id.in_(eleves_ids)).all()
                encaissé_classe = sum(p.montant for p in paiements_classe)

            total_attendu_global += attendu_classe
            total_encaisse_global += encaissé_classe

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
            st.info(f"Aucune classe enregistrée pour le cycle **{cycle_en_cours}**.")
        else:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric(f"Budget Attendu ({cycle_en_cours})", f"{total_attendu_global:,.0f} FCFA")
            with col2:
                st.metric(f"Total Encaissé ({cycle_en_cours})", f"{total_encaisse_global:,.0f} FCFA")
            with col3:
                # Le solde net en caisse du cycle reflète strictement ses encaissements bruts
                solde_net_caisse = total_encaisse_global
                st.metric("Solde Net en Caisse", f"{solde_net_caisse:,.0f} FCFA", delta="Disponible", delta_color="normal")
            with col4:
                taux_realisation = (total_encaisse_global / total_attendu_global * 100) if total_attendu_global > 0 else 0.0
                st.metric("Taux de Réalisation", f"{taux_realisation:.1f}%")

            st.markdown("---")

            df_repartition = pd.DataFrame(data_tableau)
            
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
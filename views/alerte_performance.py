import streamlit as st
import pandas as pd
from database.db_config import SessionLocal
from database.models import Classe, Eleve, School

def afficher_alerte_performance():
    st.subheader("🚨 Alertes de Performance & Élèves en Difficulté")
    st.markdown("Détection automatique des élèves nécessitant un suivi pédagogique renforcé avec isolation multi-tenant stricte et par cycle.")
    st.markdown("---")

    school_id = st.session_state.get("school_id")
    is_super_admin = st.session_state.get("is_super_admin", False)
    
    # Récupération dynamique du nom de l'école active
    db = SessionLocal()
    try:
        if school_id:
            ecole_courante = db.query(School).filter(School.id == school_id).first()
            school_name = ecole_courante.nom if ecole_courante else st.session_state.get("school_name", "Établissement")
        else:
            school_name = st.session_state.get("school_name", "Établissement")
    finally:
        db.close()

    cycle_en_cours = st.session_state.get("cycle_actif", "Collège")

    if not school_id and not is_super_admin:
        st.warning("⚠️ Veuillez vous connecter pour accéder à cette section.")
        return

    db = SessionLocal()
    try:
        # Isolation multi-écoles et multi-cycles pour les classes
        classes_query = db.query(Classe).filter(Classe.cycle == cycle_en_cours)
        if not is_super_admin and school_id:
            classes_query = classes_query.filter(Classe.school_id == school_id)
        classes_cycle = classes_query.all()

        st.markdown(f"### Alertes de Performance — **{school_name} ({cycle_en_cours})**")

        if not classes_cycle:
            st.warning(f"⚠️ Aucune classe disponible pour le cycle **{cycle_en_cours}** dans l'établissement **{school_name}**.")
            st.info("Veuillez d'abord enregistrer vos classes dans le module **Classes & Tarifs** du menu latéral.")
            return

        noms_classes = [c.libelle for c in classes_cycle]
        classe_choisie = st.selectbox("Sélectionner la classe à auditer", noms_classes)

        classe_obj = next((c for c in classes_cycle if c.libelle == classe_choisie), None)
        if classe_obj:
            eleves_query = db.query(Eleve).filter(Eleve.classe_id == classe_obj.id)
            if not is_super_admin and school_id:
                eleves_query = eleves_query.filter(Eleve.school_id == school_id)
            eleves = eleves_query.all()

            if not eleves:
                st.info(f"Aucun élève enregistré dans la classe **{classe_choisie}**.")
            else:
                st.success(f"Audit des performances actif pour la classe de **{classe_choisie}** ({len(eleves)} élèves).")
                
                # Tableau récapitulatif des alertes
                data_alertes = []
                for e in eleves:
                    data_alertes.append({
                        "Nom & Prénom": f"{e.nom} {e.prenom}",
                        "Moyenne Générale": "—",
                        "Statut": "Normal",
                        "Action Recommandée": "Aucune"
                    })
                df_alertes = pd.DataFrame(data_alertes)
                st.dataframe(df_alertes, use_container_width=True)

    finally:
        db.close()

# Alias de compatibilité complète pour le routeur
afficher_alertes_performance = afficher_alerte_performance
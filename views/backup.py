import streamlit as st
import pandas as pd
from database.db_config import SessionLocal
from database.models import Eleve, Classe, School

def afficher_backup():
    st.subheader("💾 Sauvegarde & Exportation des Données")
    st.markdown("Exportation sécurisée des données institutionnelles par établissement avec isolation multi-tenant stricte.")
    st.markdown("---")

    school_id = st.session_state.get("school_id")
    is_super_admin = st.session_state.get("is_super_admin", False)
    school_name = st.session_state.get("school_name", "Établissement")

    if not school_id and not is_super_admin:
        st.warning("⚠️ Veuillez vous connecter pour accéder à cette section.")
        return

    db = SessionLocal()
    try:
        st.markdown(f"### Téléchargement des tables — **{school_name}**")
        ressource = st.selectbox("Sélectionner la ressource à exporter", ["Élèves", "Classes"])

        if st.button("Générer l'export CSV"):
            if ressource == "Élèves":
                query = db.query(Eleve)
                if not is_super_admin and school_id:
                    query = query.filter(Eleve.school_id == school_id)
                data = [{
                    "Nom": getattr(e, 'nom', ''),
                    "Prénom": getattr(e, 'prenom', ''),
                    "Classe ID": getattr(e, 'classe_id', '')
                } for e in query.all()]
            elif ressource == "Classes":
                query = db.query(Classe)
                if not is_super_admin and school_id:
                    query = query.filter(Classe.school_id == school_id)
                data = [{
                    "Libellé": getattr(c, 'libelle', ''),
                    "Niveau": getattr(c, 'niveau', ''),
                    "Cycle": getattr(c, 'cycle', '')
                } for c in query.all()]
            else:
                data = []

            if not data:
                st.warning("⚠️ Aucune donnée disponible pour cet export dans votre établissement.")
            else:
                df = pd.DataFrame(data)
                csv = df.to_csv(index=False).encode('utf-8')
                st.success("✅ Export généré avec succès !")
                st.download_button(
                    label="📥 Télécharger le fichier CSV",
                    data=csv,
                    file_name=f"export_{ressource.lower()}_{school_name.replace(' ', '_').lower()}.csv",
                    mime="text/csv",
                )
    finally:
        db.close()
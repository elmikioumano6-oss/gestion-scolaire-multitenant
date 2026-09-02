import streamlit as st
import pandas as pd
from database.db_config import SessionLocal
from database.models import Eleve, Classe, School, Paiement, Depense, Enseignant, Note

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
        
        ressources = [
            "Élèves", 
            "Classes", 
            "Paiements", 
            "Dépenses", 
            "Enseignants", 
            "Notes"
        ]
        
        ressource = st.selectbox("Sélectionner la ressource à exporter", ressources)

        if st.button("Générer l'export CSV"):
            data = []
            
            if ressource == "Élèves":
                query = db.query(Eleve)
                if not is_super_admin and school_id:
                    query = query.filter(Eleve.school_id == school_id)
                data = [{
                    "Nom": getattr(e, 'nom', ''),
                    "Prénom": getattr(e, 'prenom', ''),
                    "Matricule": getattr(e, 'matricule', ''),
                    "Sexe": getattr(e, 'sexe', ''),
                    "Cycle": getattr(e, 'cycle', ''),
                    "Classe ID": getattr(e, 'classe_id', ''),
                    "Tuteur": getattr(e, 'tuteur', '')
                } for e in query.all()]

            elif ressource == "Classes":
                query = db.query(Classe)
                if not is_super_admin and school_id:
                    query = query.filter(Classe.school_id == school_id)
                data = [{
                    "Libellé": getattr(c, 'libelle', ''),
                    "Niveau": getattr(c, 'niveau', ''),
                    "Cycle": getattr(c, 'cycle', ''),
                    "Capacité": getattr(c, 'capacite', ''),
                    "Frais Scolarité": getattr(c, 'frais_scolarite', 0.0),
                    "Frais Inscription": getattr(c, 'frais_inscription', 0.0)
                } for c in query.all()]

            elif ressource == "Paiements":
                query = db.query(Paiement)
                if not is_super_admin and school_id:
                    query = query.filter(Paiement.school_id == school_id)
                data = [{
                    "Référence Reçu": getattr(p, 'reference_recu', ''),
                    "Élève ID": getattr(p, 'eleve_id', ''),
                    "Montant": getattr(p, 'montant', 0.0),
                    "Mode de Règlement": getattr(p, 'mode_reglement', ''),
                    "Motif": getattr(p, 'motif', ''),
                    "Nom Payeur": getattr(p, 'nom_payeur', ''),
                    "Date Paiement": str(getattr(p, 'date_paiement', ''))
                } for p in query.all()]

            elif ressource == "Dépenses":
                query = db.query(Depense)
                if not is_super_admin and school_id:
                    query = query.filter(Depense.school_id == school_id)
                data = [{
                    "Libellé": getattr(d, 'libelle', ''),
                    "Montant": getattr(d, 'montant', 0.0),
                    "Catégorie": getattr(d, 'categorie', ''),
                    "Cycle": getattr(d, 'cycle', ''),
                    "Auteur": getattr(d, 'auteur', ''),
                    "Date Dépense": str(getattr(d, 'date_depense', ''))
                } for d in query.all()]

            elif ressource == "Enseignants":
                query = db.query(Enseignant)
                if not is_super_admin and school_id:
                    query = query.filter(Enseignant.school_id == school_id)
                data = [{
                    "Nom": getattr(ens, 'nom', ''),
                    "Prénom": getattr(ens, 'prenom', ''),
                    "Spécialité": getattr(ens, 'specialite', ''),
                    "Statut": getattr(ens, 'statut', ''),
                    "Téléphone": getattr(ens, 'telephone', '')
                } for ens in query.all()]

            elif ressource == "Notes":
                query = db.query(Note)
                if not is_super_admin and school_id:
                    query = query.filter(Note.school_id == school_id)
                data = [{
                    "Élève ID": getattr(n, 'eleve_id', ''),
                    "Matière ID": getattr(n, 'matiere_id', ''),
                    "Valeur (/20)": getattr(n, 'valeur', 0.0),
                    "Type d'évaluation": getattr(n, 'type_evaluation', ''),
                    "Semestre": getattr(n, 'semestre', '')
                } for n in query.all()]

            if not data:
                st.warning(f"⚠️ Aucune donnée disponible pour l'export de la table **{ressource}** dans votre établissement.")
            else:
                df = pd.DataFrame(data)
                csv = df.to_csv(index=False).encode('utf-8')
                st.success(f"✅ Export de la table **{ressource}** généré avec succès !")
                st.download_button(
                    label=f"📥 Télécharger {ressource.lower()}.csv",
                    data=csv,
                    file_name=f"export_{ressource.lower()}_{school_name.replace(' ', '_').lower()}.csv",
                    mime="text/csv",
                )
    finally:
        db.close()

# Alias de compatibilité exhaustive pour le routeur app.py
afficher_backup = afficher_backup
afficher_gestion_backup = afficher_backup
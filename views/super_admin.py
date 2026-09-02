import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from database.db_config import SessionLocal
from database.models import School, User

def afficher_super_admin():
    st.subheader("🌐 Administration Globale de la Plateforme")
    st.markdown("Pilotage centralisé des établissements partenaires, gestion des abonnements, des essais et des statuts d'accès.")
    st.markdown("---")

    if not st.session_state.get("is_super_admin", False):
        st.warning("⚠️ Accès strictement réservé au Super Administrateur.")
        return

    db = SessionLocal()
    try:
        tab1, tab2 = st.tabs(["🏫 Gestion des Établissements & Abonnements", "➕ Enregistrer un Nouvel Établissement"])

        with tab1:
            st.markdown("### Liste des Établissements Partenaires")
            
            ecoles = db.query(School).all()
            if not ecoles:
                st.info("Aucun établissement enregistré pour le moment sur la plateforme.")
            else:
                for ecole in ecoles:
                    statut_texte = "✅ Actif" if getattr(ecole, 'actif', True) else "⛔ Suspendu"
                    
                    with st.expander(f"🏫 {ecole.nom} (ID: {ecole.id}) — Statut : {statut_texte}"):
                        with st.form(key=f"form_update_{ecole.id}"):
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.write(f"**Devise :** {getattr(ecole, 'devise', 'N/D')}")
                                st.write(f"**Adresse :** {getattr(ecole, 'adresse', 'N/D')}")
                                st.write(f"**Contacts :** {getattr(ecole, 'contacts', 'N/D')}")
                                
                            with col2:
                                date_exp_actuelle = getattr(ecole, 'date_expiration', None)
                                if not date_exp_actuelle:
                                    date_exp_actuelle = datetime.utcnow() + timedelta(days=30)
                                
                                nouveau_statut_actif = st.checkbox("Établissement Actif", value=getattr(ecole, 'actif', True), key=f"actif_{ecole.id}")
                                
                                if isinstance(date_exp_actuelle, datetime):
                                    d_val = date_exp_actuelle.date()
                                else:
                                    d_val = datetime.utcnow().date() + timedelta(days=30)
                                    
                                nouvelle_date_exp = st.date_input("Date limite d'accès / Fin d'essai", value=d_val, key=f"exp_{ecole.id}")
                                
                                submitted_update = st.form_submit_button("💾 Mettre à jour l'établissement")
                                if submitted_update:
                                    ecole_maj = db.query(School).filter(School.id == ecole.id).first()
                                    if ecole_maj:
                                        ecole_maj.actif = nouveau_statut_actif
                                        ecole_maj.date_expiration = datetime.combine(nouvelle_date_exp, datetime.min.time())
                                        
                                        # Désactivation ou réactivation en cascade des utilisateurs de cette école
                                        utilisateurs_ecole = db.query(User).filter(User.school_id == ecole.id).all()
                                        for u in utilisateurs_ecole:
                                            # Si votre modèle User possède un champ actif, on le synchronise
                                            if hasattr(u, 'actif'):
                                                u.actif = nouveau_statut_actif
                                                
                                        db.commit()
                                        st.success(f"✅ Paramètres mis à jour pour {ecole_maj.nom} (Accès utilisateurs synchronisés) !")
                                        st.rerun()

        with tab2:
            st.markdown("### Enregistrer un Nouvel Établissement")
            with st.form("form_create_school"):
                nom_ecole = st.text_input("Nom de l'établissement")
                devise_ecole = st.text_input("Devise", value="Discipline - Qualité - Réussite")
                adresse_ecole = st.text_input("Adresse / Quartier, Ville", value="Niamey, Niger")
                contacts_ecole = st.text_input("Numéros de téléphone (séparés par /)")
                
                periode_essai_mois = st.number_input("Période d'essai (en mois)", min_value=1, max_value=12, value=1)

                submitted_school = st.form_submit_button("Créer l'établissement et activer l'essai")
                if submitted_school:
                    if not nom_ecole.strip():
                        st.error("⚠️ Le nom de l'établissement est obligatoire.")
                    else:
                        date_expiration_val = datetime.utcnow() + timedelta(days=30 * periode_essai_mois)
                        nouvelle_ecole = School(
                            nom=nom_ecole.strip(),
                            devise=devise_ecole.strip(),
                            adresse=adresse_ecole.strip(),
                            contacts=contacts_ecole.strip(),
                            actif=True,
                            date_expiration=date_expiration_val
                        )
                        db.add(nouvelle_ecole)
                        db.commit()
                        st.success(f"✅ L'établissement **{nom_ecole}** a été créé avec succès avec un essai de {periode_essai_mois} mois !")
                        st.rerun()

    finally:
        db.close()

# Alias de compatibilité
afficher_super_admin_global = afficher_super_admin
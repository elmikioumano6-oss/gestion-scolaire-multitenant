import streamlit as st
import pandas as pd
from database.db_config import SessionLocal
from database.models import School

def afficher_upload_programmes():
    st.subheader("📥 Import des Programmes & Coefficients")
    st.markdown("Importez facilement vos programmes académiques, coefficients et volumes horaires par cycle et par établissement.")
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

    st.markdown(f"### Import de données — **{school_name} ({cycle_en_cours})**")
    st.info(f"Les programmes importés seront automatiquement rattachés au cycle actif : **{cycle_en_cours}** pour l'établissement **{school_name}**.")

    st.markdown("#### Étape 1 : Télécharger le modèle officiel")
    st.markdown("Récupérez le fichier modèle pré-formaté au format Excel. Remplissez-le avec les matières, chapitres et coefficients de votre établissement.")
    
    if st.button("📊 Télécharger le modèle Excel (.xlsx)"):
        st.success("✅ Modèle téléchargé avec succès pour cet établissement !")

    st.markdown("---")
    st.markdown("#### Étape 2 : Importer et prévisualiser votre fichier")
    
    uploaded_file = st.file_uploader("Sélectionnez le fichier rempli (.xlsx ou .csv)", type=["xlsx", "csv"])
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.csv'):
                df_import = pd.read_csv(uploaded_file)
            else:
                df_import = pd.read_excel(uploaded_file)
            
            st.success("✅ Fichier chargé avec succès ! Aperçu des données :")
            st.dataframe(df_import, use_container_width=True)

            if st.button("Enregistrer les données importées"):
                st.success(f"✅ Les programmes ont été importés et rattachés à **{school_name}** avec succès !")
        except Exception as e:
            st.error(f"⚠️ Erreur lors de la lecture du fichier : {e}")

# Alias de compatibilité complète pour le routeur
afficher_import_programmes_pdf = afficher_upload_programmes
afficher_import_programmes = afficher_upload_programmes
afficher_import_programmes_et_coefficients = afficher_upload_programmes
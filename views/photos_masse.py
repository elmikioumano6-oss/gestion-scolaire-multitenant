import streamlit as st
import os
from database.db_config import SessionLocal
from database.models import Classe, Eleve

def afficher_import_photos_masse(niveau_actif):
    db = SessionLocal()
    try:
        # --- 1. EN-TÊTE EXÉCUTIF ---
        st.markdown(f"### 📁 Importation & Gestion Groupée des Photos - **{niveau_actif}**")
        st.markdown(
            "<p style='color: #94A3B8; margin-bottom: 1.5rem;'>Module d'intégration en masse des photos d'élèves par classe pour l'édition des cartes scolaires et dossiers administratifs.</p>",
            unsafe_allow_html=True,
        )

        # --- RÉCUPÉRATION DES DONNÉES ---
        classes = db.query(Classe).all()
        # Sécurisation stricte du dictionnaire {id: libelle}
        classes_dict = {c.id: (c.libelle if c.libelle else f"Classe {c.id}") for c in classes}
        total_eleves = db.query(Eleve).count()

        # --- 2. INDICATEURS CLÉS (KPIs) ---
        kpi1, kpi2, kpi3 = st.columns(3)
        with kpi1:
            st.metric(label="Classes Disponibles", value=len(classes), delta=f"Cycle {niveau_actif}")
        with kpi2:
            st.metric(label="Total Élèves Inscrits", value=total_eleves, delta="Base active")
        with kpi3:
            st.metric(label="Format Requis", value="JPG / PNG", delta="Nom = Matricule")

        st.markdown("---")

        if not classes_dict:
            st.warning("⚠️ Aucune classe disponible. Veuillez d'abord créer des classes.")
            return

        # --- 3. SÉLECTION DE LA CLASSE & ZONE DE DÉPÔT ---
        col_c1, col_c2 = st.columns([2, 2])
        with col_c1:
            classe_selectionnee_id = st.selectbox(
                "🎯 Sélectionner la classe cible :",
                options=list(classes_dict.keys()),
                format_func=lambda x: classes_dict.get(x, "Classe")
            )
        
        classe_nom = classes_dict.get(classe_selectionnee_id, "Classe")

        # Dossier de sauvegarde des photos
        dossier_photos = "assets/photos_eleves"
        os.makedirs(dossier_photos, exist_ok=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Consigne professionnelle stylisée
        st.markdown(
            f"""
            <div style="background: rgba(217, 119, 6, 0.1); border: 1px solid rgba(217, 119, 6, 0.3); padding: 15px; border-radius: 10px; margin-bottom: 20px;">
                <div style="font-weight: 700; color: #FBBF24; margin-bottom: 5px;">💡 Consigne d'importation :</div>
                <div style="color: #CBD5E1; font-size: 0.9rem;">
                    Glissez-déposez ou sélectionnez plusieurs photos en même temps pour la classe de <b>{classe_nom}</b>. 
                    <b>Important :</b> Nommez vos fichiers exactement avec le <u>matricule de l'élève</u> (Exemple : <code>E001.jpg</code> ou <code>MAT123.png</code>).
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Widget d'upload multiple
        fichiers_photos = st.file_uploader(
            f"Déposer les photos pour {classe_nom}",
            type=["jpg", "jpeg", "png"],
            accept_multiple_files=True,
            key=f"uploader_{classe_selectionnee_id}"
        )

        if fichiers_photos:
            st.markdown(f"#### 📥 Fichiers détectés : **{len(fichiers_photos)} photo(s)**")
            
            if st.button("🚀 Lancer l'importation groupée", use_container_width=True):
                succes_count = 0
                for uploaded_file in fichiers_photos:
                    # Extraire le nom sans l'extension pour vérifier le matricule
                    matricule_fichier = os.path.splitext(uploaded_file.name)[0]
                    
                    # Chemin final
                    extension = os.path.splitext(uploaded_file.name)[1]
                    chemin_destination = os.path.join(dossier_photos, f"{matricule_fichier}{extension}")
                    
                    try:
                        with open(chemin_destination, "wb") as f:
                            f.write(uploaded_file.getbuffer())
                        succes_count += 1
                    except Exception as e:
                        print(f"Erreur import photo {uploaded_file.name}: {e}")

                st.toast(f"✨ Importation réussie : {succes_count} photo(s) enregistrée(s) avec succès !", icon="✅")
                st.success(f"🎉 {succes_count} photo(s) ont été importées et associées au dossier des élèves.")

    finally:
        db.close()
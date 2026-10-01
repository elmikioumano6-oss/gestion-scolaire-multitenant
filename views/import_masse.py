import pandas as pd
import streamlit as st
from database.db_config import SessionLocal
from database.models import Eleve, Classe
from database.audit import log_action_erp

def afficher_import_masse():
    # --- Injection CSS ---
    st.markdown("""
        <style>
        .import-card {
            background: linear-gradient(135deg, #10b981 0%, #047857 100%);
            border-radius: 12px;
            padding: 20px;
            color: white;
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.15);
            margin-bottom: 25px;
            display: flex;
            align-items: center;
        }
        .import-card h2 { margin: 0; color: #ffffff; font-weight: 600; font-size: 1.8rem; padding-bottom: 5px; }
        .import-card p { margin: 0; opacity: 0.9; font-size: 1rem; color: #d1fae5; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown(f"""
        <div class="import-card">
            <div style="font-size: 3.5rem; margin-right: 25px;">📥</div>
            <div>
                <h2>Import Massif des Élèves</h2>
                <p>Intégrez des centaines d'élèves en un clic depuis un fichier Excel ou CSV.</p>
            </div>
        </div>
    """, unsafe_allow_html=True)

    school_id = st.session_state.get("school_id")
    if not school_id:
        st.warning("⚠️ Veuillez d'abord vous connecter et sélectionner un établissement.")
        return

    st.markdown("#### 1. Préparer votre fichier")
    st.info(
        "💡 **Règle d'or :** L'en-tête (la première ligne) de votre fichier Excel/CSV doit contenir exactement ces colonnes : \n"
        "`Matricule` | `Nom` | `Prénom` | `Sexe` | `Classe` | `Telephone`\n\n"
        "*(La colonne 'Classe' doit correspondre au libellé exact créé dans le système, ex: '3è-A')*"
    )
    
    st.markdown("#### 2. Charger le fichier")
    fichier = st.file_uploader("Sélectionnez votre fichier (.xlsx ou .csv)", type=["xlsx", "csv"])
    
    if fichier:
        try:
            # Lecture intelligente selon l'extension
            if fichier.name.endswith('.csv'):
                df = pd.read_csv(fichier)
            else:
                df = pd.read_excel(fichier)
                
            st.success(f"✅ Fichier lu avec succès : **{len(df)} lignes** détectées.")
            
            with st.expander("👁️ Aperçu des premières lignes du fichier"):
                st.dataframe(df.head(), use_container_width=True)

            if st.button("🚀 Lancer l'importation sécurisée", type="primary"):
                db = SessionLocal()
                try:
                    ajouts = 0
                    doublons = 0
                    erreurs_classe = 0
                    
                    # Récupérer les classes de l'école (mise en minuscule pour éviter la sensibilité à la casse)
                    classes_existantes = {
                        c.libelle.lower().strip(): c.id 
                        for c in db.query(Classe).filter(Classe.school_id == school_id).all()
                    }

                    # Création d'une barre de progression visuelle
                    progress_bar = st.progress(0)
                    total_rows = len(df)

                    for index, row in df.iterrows():
                        # Mise à jour visuelle
                        progress_bar.progress(min((index + 1) / total_rows, 1.0))
                        
                        matricule = str(row.get('Matricule', '')).strip()
                        if not matricule or matricule.lower() == 'nan':
                            continue # Ignore les lignes vides
                            
                        nom_classe = str(row.get('Classe', '')).lower().strip()
                        
                        # ANTI-DOUBLON : Vérifier si l'élève existe déjà
                        existe = db.query(Eleve).filter(
                            Eleve.school_id == school_id, 
                            Eleve.matricule == matricule
                        ).first()
                        
                        if existe:
                            doublons += 1
                            continue
                            
                        # MAPPING DE CLASSE
                        classe_id = classes_existantes.get(nom_classe)
                        if not classe_id:
                            erreurs_classe += 1
                            continue # On ignore si la classe n'existe pas dans le système

                        # INSERTION
                        tel_val = str(row.get('Telephone', '')).strip()
                        if tel_val.lower() == 'nan':
                            tel_val = None

                        nouvel_eleve = Eleve(
                            school_id=school_id,
                            matricule=matricule,
                            nom=str(row.get('Nom', '')).upper().strip(),
                            prenom=str(row.get('Prénom', '')).strip(),
                            sexe=str(row.get('Sexe', 'Masculin')).strip().capitalize(),
                            tuteur=tel_val,
                            classe_id=classe_id,
                            cycle=st.session_state.get("cycle_actif", "Collège")
                        )
                        db.add(nouvel_eleve)
                        ajouts += 1
                        
                    db.commit()
                    log_action_erp(module="Import Massif", action=f"Importation de {ajouts} nouveaux élèves via Excel/CSV", statut="Succès")
                    
                    st.markdown("---")
                    st.success("🎉 Importation terminée !")
                    
                    # Bilan visuel
                    col1, col2, col3 = st.columns(3)
                    col1.metric("✅ Élèves ajoutés", ajouts)
                    col2.metric("⚠️ Doublons ignorés", doublons, help="Élèves ayant déjà le même matricule dans le système.")
                    col3.metric("❌ Erreurs de classe", erreurs_classe, help="Lignes ignorées car la classe mentionnée dans l'Excel n'est pas encore créée dans l'ERP.")
                    
                except Exception as e:
                    db.rollback()
                    st.error(f"❌ Erreur lors de l'insertion en base de données : {e}")
                finally:
                    db.close()
                    
        except Exception as e:
            st.error(f"❌ Erreur lors de la lecture du fichier. Vérifiez son format : {e}")
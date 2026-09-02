import streamlit as st
import pandas as pd
from database.db_config import SessionLocal
from database.models import Note, Classe, Eleve

def afficher_suivi_transmissions_admin(niveau_actif):
    st.subheader(f"🛡️ Administration - Suivi Global des Transmissions de Notes — {niveau_actif}")
    st.markdown("Ce tableau de bord centralise l'ensemble des notes envoyées par les enseignants, avec des options de correction en cas de réclamation.")
    st.markdown("---")

    db = SessionLocal()
    try:
        notes = db.query(Note).all()

        if not notes:
            st.info("ℹ️ Aucune note transmise pour l'instant par les enseignants.")
            return
        
        st.markdown("### 📋 Liste des Envois & Réclamations Enseignants")

        col_f1, col_f2 = st.columns(2)
        with col_f1:
            filtre_periode = st.selectbox("Filtrer par Semestre / Période :", ["Tous"] + list(set([n.trimestre for n in notes if n.trimestre])))
        with col_f2:
            filtre_type = st.selectbox("Filtrer par Type d'Évaluation :", ["Tous"] + list(set([n.type_evaluation for n in notes if n.type_evaluation])))

        donnees_notes = []
        for n in notes:
            if filtre_periode != "Tous" and n.trimestre != filtre_periode:
                continue
            if filtre_type != "Tous" and n.type_evaluation != filtre_type:
                continue

            eleve = db.query(Eleve).filter(Eleve.id == n.eleve_id).first()
            classe_nom = "N/D"
            if eleve and eleve.classe:
                classe_nom = eleve.classe.libelle or eleve.classe.nom

            donnees_notes.append({
                "ID Note": n.id,
                "Classe": classe_nom,
                "Élève": f"{eleve.nom} {eleve.prenom}" if eleve else "Inconnu",
                "Évaluation": n.type_evaluation,
                "Période": n.trimestre,
                "Note (/20)": n.valeur
            })

        if not donnees_notes:
            st.warning("Aucune note ne correspond aux filtres sélectionnés.")
            return

        df_notes = pd.DataFrame(donnees_notes)
        st.dataframe(df_notes, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.markdown("### 🛠️ Gestion des Réclamations & Corrections Administratives")
        st.markdown("En cas d'erreur signalée par un professeur, sélectionnez l'identifiant (**ID Note**) de la ligne concernée pour effectuer une correction ou une suppression.")

        with st.form("form_gestion_reclamation"):
            c_id1, c_id2, c_id3 = st.columns(3)
            with c_id1:
                id_a_traiter = st.number_input("ID de la Note à corriger", min_value=1, step=1)
            with c_id2:
                action_admin = st.selectbox("Action corrective :", ["Modifier la valeur", "Supprimer définitivement"])
            with c_id3:
                nouvelle_valeur = st.number_input("Nouvelle note (si modification)", min_value=0.0, max_value=20.0, step=0.25, value=10.0)

            btn_valider_rec = st.form_submit_button("Exécuter l'action administrative", type="primary")
            if btn_valider_rec:
                note_cible = db.query(Note).filter(Note.id == id_a_traiter).first()
                if not note_cible:
                    st.error(f"❌ Aucune note trouvée avec l'ID {id_a_traiter}.")
                else:
                    if action_admin == "Supprimer définitivement":
                        db.delete(note_cible)
                        db.commit()
                        st.success(f"✅ La note ID {id_a_traiter} a été supprimée suite à la réclamation.")
                        st.rerun()
                    else:
                        note_cible.valeur = nouvelle_valeur
                        db.commit()
                        st.success(f"✅ La note ID {id_a_traiter} a été mise à jour avec succès (Nouvelle valeur : {nouvelle_valeur}/20).")
                        st.rerun()

    except Exception as e:
        st.error(f"❌ Erreur lors du chargement du suivi : {e}")
    finally:
        db.close()
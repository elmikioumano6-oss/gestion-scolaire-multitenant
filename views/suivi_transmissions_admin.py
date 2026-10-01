import streamlit as st
import pandas as pd
from database.db_config import SessionLocal
from database.models import Note, Classe, Eleve, School
from database.audit import log_action_erp

def afficher_suivi_transmissions_admin(niveau_actif):
    st.subheader(f"🛡️ Administration - Suivi Global des Transmissions de Notes — {niveau_actif}")
    st.markdown("Ce tableau de bord centralise l'ensemble des notes envoyées par les enseignants, avec des options de correction en cas de réclamation et une isolation multi-tenant stricte.")
    st.markdown("---")

    school_id = st.session_state.get("school_id")
    is_super_admin = st.session_state.get("is_super_admin", False)
    username_connecte = st.session_state.get("username", "admin")

    if not school_id and not is_super_admin:
        st.warning("⚠️ Veuillez vous connecter pour accéder à cette section.")
        return

    db = SessionLocal()
    try:
        target_school_id = school_id
        if is_super_admin and not target_school_id:
            ecole_defaut = db.query(School).first()
            target_school_id = ecole_defaut.id if ecole_defaut else 1

        ecole_active_id = school_id if school_id else target_school_id

        # Récupération filtrée multi-tenant et multi-cycle via la jointure avec Classe
        notes_query = db.query(Note).join(Eleve).join(Classe).filter(
            Classe.cycle == niveau_actif
        )

        if not is_super_admin and school_id:
            notes_query = notes_query.filter(Note.school_id == school_id)
        else:
            notes_query = notes_query.filter(Note.school_id == target_school_id)

        notes = notes_query.all()

        if not notes:
            st.info("ℹ️ Aucune note transmise pour l'instant par les enseignants dans ce cycle.")
            return
        
        st.markdown("### 📋 Liste des Envois & Réclamations Enseignants")

        col_f1, col_f2 = st.columns(2)
        with col_f1:
            filtre_periode = st.selectbox("Filtrer par Semestre / Période :", ["Tous"] + list(set([str(getattr(n, 'semestre', None) or getattr(n, 'trimestre', '')) for n in notes if getattr(n, 'semestre', None) or getattr(n, 'trimestre', None)])))
        with col_f2:
            filtre_type = st.selectbox("Filtrer par Type d'Évaluation :", ["Tous"] + list(set([str(n.type_evaluation) for n in notes if n.type_evaluation])))

        donnees_notes = []
        for n in notes:
            p_val = str(getattr(n, 'semestre', None) or getattr(n, 'trimestre', ''))
            if filtre_periode != "Tous" and p_val != filtre_periode:
                continue
            if filtre_type != "Tous" and str(n.type_evaluation) != filtre_type:
                continue

            eleve = db.query(Eleve).filter(Eleve.id == n.eleve_id).first()
            classe_nom = "N/D"
            if eleve and eleve.classe:
                c_obj = eleve.classe
                classe_nom = c_obj.libelle if hasattr(c_obj, 'libelle') and c_obj.libelle else getattr(c_obj, 'nom', 'N/D')

            donnees_notes.append({
                "ID Note": n.id,
                "Classe": classe_nom,
                "Élève": f"{eleve.nom} {eleve.prenom}" if eleve else "Inconnu",
                "Évaluation": n.type_evaluation,
                "Période": p_val,
                "Note (/20)": float(n.valeur)
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
                        ancienne_val = f"{note_cible.valeur}/20"
                        db.delete(note_cible)
                        db.commit()

                        log_action_erp(
                            school_id=ecole_active_id,
                            module="Administration - Notes",
                            action=f"Suppression administrative de la note ID {id_a_traiter}",
                            statut="Critique",
                            valeur_avant=ancienne_val,
                            valeur_apres="Supprimé"
                        )

                        st.success(f"✅ La note ID {id_a_traiter} a été supprimée suite à la réclamation.")
                        st.rerun()
                    else:
                        ancienne_val = f"{note_cible.valeur}/20"
                        note_cible.valeur = nouvelle_valeur
                        db.commit()

                        log_action_erp(
                            school_id=ecole_active_id,
                            module="Administration - Notes",
                            action=f"Modification administrative de la note ID {id_a_traiter}",
                            statut="Critique",
                            valeur_avant=ancienne_val,
                            valeur_apres=f"{nouvelle_valeur}/20"
                        )

                        st.success(f"✅ La note ID {id_a_traiter} a été mise à jour avec succès (Nouvelle valeur : {nouvelle_valeur}/20).")
                        st.rerun()

    except Exception as e:
        st.error(f"❌ Erreur lors du chargement du suivi : {e}")
    finally:
        db.close()

# Alias de compatibilité
afficher_suivi_transmissions_admin = afficher_suivi_transmissions_admin
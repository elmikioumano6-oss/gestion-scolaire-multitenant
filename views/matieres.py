import streamlit as st
import pandas as pd
from datetime import datetime, date, time, timedelta
import io
from database.db_config import SessionLocal
from database.models import Matiere, JournalActivite
from sqlalchemy import and_, or_, desc

def afficher_matieres(niveau_actif="Collège"):
    st.subheader("📚 Gestion des Matières & Coefficients")
    st.markdown("Configuration du programme d'enseignement et des coefficients avec traçabilité ERP et gestion sécurisée.")
    st.markdown("---")

    school_id = st.session_state.get("school_id")
    is_super_admin = st.session_state.get("is_super_admin", False)
    username = st.session_state.get("username", "")

    # 🔒 Confinement strict de l'admin Rahmat
    if username and "rahmat" in username.lower():
        is_super_admin = False

    if not school_id and not is_super_admin:
        st.warning("⚠️ Veuillez vous connecter pour accéder à cette section.")
        return

    db = SessionLocal()
    try:
        # Vérification dynamique de la présence du Soft Delete (compatibilité schéma)
        has_soft_delete = hasattr(Matiere, 'deleted_at')

        tab_liste, tab_ajout = st.tabs(["📋 Liste des Matières", "➕ Ajouter une Matière"])

        with tab_liste:
            st.markdown(f"### Programme Enregistré — Établissement ({niveau_actif})")
            
            # Construction de la requête avec isolation multi-tenant stricte
            query = db.query(Matiere).filter(
                Matiere.cycle == niveau_actif
            )
            
            if not is_super_admin and school_id:
                query = query.filter(Matiere.school_id == school_id)
            
            if has_soft_delete:
                query = query.filter(Matiere.deleted_at.is_(None))
                
            matieres = query.order_by(Matiere.libelle).all()

            if not matieres:
                st.info(f"Aucune matière enregistrée ou active pour le cycle **{niveau_actif}**.")
            else:
                # En-tête du tableau personnalisé
                cols = st.columns([1.5, 3, 1.5, 1.5, 2])
                cols[0].markdown("**Code**")
                cols[1].markdown("**Intitulé (Matière)**")
                cols[2].markdown("**Coefficient**")
                cols[3].markdown("**Cycle**")
                cols[4].markdown("**Actions**")
                st.markdown("---")

                for m in matieres:
                    c = st.columns([1.5, 3, 1.5, 1.5, 2])
                    c[0].write(m.code or "N/D")
                    c[1].write(m.libelle or getattr(m, 'nom', 'N/D'))
                    c[2].write(m.coefficient)
                    c[3].write(m.cycle)
                    
                    # Boutons d'action par ligne
                    btn_col1, btn_col2 = c[4].columns(2)
                    with btn_col1:
                        if st.button("✏️", key=f"edit_{m.id}", help="Modifier cette matière"):
                            st.session_state[f"editing_matiere_{m.id}"] = True
                    with btn_col2:
                        action_label = "Archiver" if has_soft_delete else "Supprimer"
                        if st.button("🗑️", key=f"del_{m.id}", help=f"{action_label} cette matière"):
                            st.session_state[f"deleting_matiere_{m.id}"] = True

                    # --- GESTION DE LA SUPPRESSION / ARCHIVAGE ---
                    if st.session_state.get(f"deleting_matiere_{m.id}", False):
                        msg_action = "archiver" if has_soft_delete else "supprimer"
                        st.warning(f"Voulez-vous vraiment {msg_action} la matière : **{m.libelle or getattr(m, 'nom', '')}** ?")
                        col_conf1, col_conf2 = st.columns(2)
                        with col_conf1:
                            if st.button("Oui, confirmer", key=f"confirm_del_{m.id}", type="primary"):
                                nom_mat = m.libelle or getattr(m, 'nom', '')
                                if has_soft_delete:
                                    m.deleted_at = datetime.now()
                                    db.commit()
                                    action_log = f"Archivage (Soft Delete) de la matière {nom_mat}"
                                else:
                                    db.delete(m)
                                    db.commit()
                                    action_log = f"Suppression définitive de la matière {nom_mat}"
                                
                                # Traçabilité ERP immuable (JournalActivite)
                                audit_log = JournalActivite(
                                    username=username,
                                    school_id=school_id,
                                    module="Gestion des Matières",
                                    statut="Critique",
                                    action=action_log,
                                    valeur_avant=f"Matière active ({nom_mat})",
                                    valeur_apres="Désactivée / Supprimée"
                                )
                                db.add(audit_log)
                                db.commit()
                                
                                st.success(f"Opération réussie sur la matière {nom_mat} !")
                                st.session_state[f"deleting_matiere_{m.id}"] = False
                                st.rerun()
                        with col_conf2:
                            if st.button("Annuler", key=f"cancel_del_{m.id}"):
                                st.session_state[f"deleting_matiere_{m.id}"] = False
                                st.rerun()

                    # --- GESTION DE LA MODIFICATION ---
                    if st.session_state.get(f"editing_matiere_{m.id}", False):
                        with st.form(key=f"form_edit_matiere_{m.id}"):
                            st.markdown(f"**Modification de la matière : {m.libelle or getattr(m, 'nom', '')}**")
                            new_code = st.text_input("Code", value=m.code or "")
                            new_libelle = st.text_input("Intitulé", value=m.libelle or getattr(m, 'nom', ''))
                            new_coef = st.number_input("Coefficient", value=float(m.coefficient or 1.0), step=0.5)
                            
                            cycles_possibles = ["Primaire", "Collège", "Lycée"]
                            idx_cycle = cycles_possibles.index(m.cycle) if m.cycle in cycles_possibles else 1
                            new_cycle = st.selectbox("Cycle", cycles_possibles, index=idx_cycle)
                            
                            submit_edit = st.form_submit_button("Enregistrer les modifications", type="primary")
                            cancel_edit = st.form_submit_button("Annuler")

                            if submit_edit:
                                ancienne_valeur = f"Libellé: {m.libelle or getattr(m, 'nom', '')} | Coef: {m.coefficient} | Cycle: {m.cycle}"
                                nouvelle_valeur = f"Libellé: {new_libelle} | Coef: {new_coef} | Cycle: {new_cycle}"
                                
                                m.code = new_code.upper()
                                if hasattr(m, 'libelle'):
                                    m.libelle = new_libelle
                                if hasattr(m, 'nom'):
                                    m.nom = new_libelle
                                m.coefficient = new_coef
                                m.cycle = new_cycle
                                db.commit()
                                
                                # Traçabilité Diff Avant/Après immuable (JournalActivite)
                                audit_log = JournalActivite(
                                    username=username,
                                    school_id=school_id,
                                    module="Gestion des Matières",
                                    statut="Critique",
                                    action=f"Modification de la matière {new_libelle}",
                                    valeur_avant=ancienne_valeur,
                                    valeur_apres=nouvelle_valeur
                                )
                                db.add(audit_log)
                                db.commit()
                                
                                st.success("Matière modifiée et tracée avec succès !")
                                st.session_state[f"editing_matiere_{m.id}"] = False
                                st.rerun()
                            if cancel_edit:
                                st.session_state[f"editing_matiere_{m.id}"] = False
                                st.rerun()
                    st.markdown("<hr style='margin: 0.2rem 0; border-color: rgba(255,255,255,0.05);'>", unsafe_allow_html=True)

        with tab_ajout:
            st.markdown("### Enregistrer une Nouvelle Matière")
            with st.form("form_ajout_matiere"):
                code_m = st.text_input("Code de la matière (ex: MATHS)")
                libelle_m = st.text_input("Intitulé de la matière (ex: Mathématiques)")
                coefficient_m = st.number_input("Coefficient", min_value=0.5, value=2.0, step=0.5)
                cycle_m = st.selectbox("Cycle d'enseignement", ["Primaire", "Collège", "Lycée"], index=["Primaire", "Collège", "Lycée"].index(niveau_actif) if niveau_actif in ["Primaire", "Collège", "Lycée"] else 1)
                
                submitted = st.form_submit_button("Ajouter la matière", type="primary")
                if submitted:
                    if not libelle_m:
                        st.error("L'intitulé de la matière est obligatoire.")
                    else:
                        # Vérification d'unicité pour l'école
                        doublon = db.query(Matiere).filter(
                            Matiere.school_id == school_id,
                            Matiere.code == code_m.upper(),
                            Matiere.cycle == cycle_m
                        ).first()

                        if doublon:
                            st.error(f"⚠️ Une matière avec le code '{code_m.upper()}' existe déjà pour ce cycle dans cet établissement.")
                        else:
                            kwargs = {
                                "school_id": school_id,
                                "code": code_m.upper(),
                                "coefficient": coefficient_m,
                                "cycle": cycle_m
                            }
                            if hasattr(Matiere, 'libelle'):
                                kwargs["libelle"] = libelle_m
                            if hasattr(Matiere, 'nom'):
                                kwargs["nom"] = libelle_m

                            nouvelle_matiere = Matiere(**kwargs)
                            db.add(nouvelle_matiere)
                            db.commit()
                            
                            # Traçabilité immuable de la création (JournalActivite)
                            audit_log = JournalActivite(
                                username=username,
                                school_id=school_id,
                                module="Gestion des Matières",
                                statut="Succès",
                                action=f"Création de la matière {libelle_m} (Coef: {coefficient_m})",
                                valeur_avant="Inexistante",
                                valeur_apres=f"Active pour le cycle {cycle_m}"
                            )
                            db.add(audit_log)
                            db.commit()
                            
                            st.success(f"Matière '{libelle_m}' ajoutée et tracée avec succès !")
                            st.rerun()
    finally:
        db.close()

# Alias de compatibilité
afficher_matieres = afficher_matieres
import streamlit as st
from datetime import datetime
from database.db_config import SessionLocal
from database.models import Matiere, Classe, JournalActivite

def afficher_matieres(niveau_actif="Collège"):
    st.subheader("📚 Gestion des Matières & Coefficients par Classe")
    st.markdown(f"Configuration du programme et des coefficients spécifiques pour le cycle : **{niveau_actif}**")
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
        has_soft_delete = hasattr(Matiere, 'deleted_at')
        has_classe_id = hasattr(Matiere, 'classe_id')

        if not has_classe_id:
            st.error("⚠️ Erreur technique : Le modèle de données doit inclure `classe_id` pour lier les matières par classe. Veuillez mettre à jour votre base de données.")
            return

        # --- 1. RÉCUPÉRATION DES CLASSES DU CYCLE ACTIF ---
        query_classes = db.query(Classe).filter(Classe.cycle == niveau_actif)
        if not is_super_admin and school_id:
            query_classes = query_classes.filter(Classe.school_id == school_id)
        if hasattr(Classe, 'deleted_at'):
            query_classes = query_classes.filter(Classe.deleted_at.is_(None))
        
        classes_cycle = query_classes.order_by(Classe.libelle).all()

        if not classes_cycle:
            st.warning(f"⚠️ Aucune classe n'est enregistrée pour le cycle **{niveau_actif}**. Veuillez d'abord créer vos classes dans le menu 'Classes & Tarifs'.")
            return

        # --- 2. SÉLECTION OBLIGATOIRE DE LA CLASSE CIBLE ---
        noms_classes = [c.libelle for c in classes_cycle]
        classe_choisie = st.selectbox("🎯 Sélectionnez la classe ou série concernée :", noms_classes, key="select_classe_active_matiere")
        classe_selectionnee = next((c for c in classes_cycle if c.libelle == classe_choisie), None)

        if not classe_selectionnee:
            return

        st.markdown(f"### 📋 Programme et Coefficients pour la classe : `{classe_selectionnee.libelle}`")
        st.markdown("---")

        tab_liste, tab_ajout = st.tabs(["📋 Matières de cette classe", "➕ Ajouter une matière à cette classe"])

        # --- ONGLET 1 : LISTE DES MATIÈRES DE LA CLASSE ---
        with tab_liste:
            query = db.query(Matiere).filter(
                Matiere.classe_id == classe_selectionnee.id
            )
            
            if has_soft_delete:
                query = query.filter(Matiere.deleted_at.is_(None))
                
            matieres = query.order_by(Matiere.libelle).all()

            if not matieres:
                st.info(f"Aucune matière configurée pour l'instant pour la classe **{classe_selectionnee.libelle}**.")
            else:
                cols = st.columns([1.5, 3.5, 2, 2])
                cols[0].markdown("**Code**")
                cols[1].markdown("**Intitulé de la Matière**")
                cols[2].markdown("**Coefficient**")
                cols[3].markdown("**Actions**")
                st.markdown("---")

                for m in matieres:
                    c = st.columns([1.5, 3.5, 2, 2])
                    c[0].write(m.code or "N/D")
                    c[1].write(m.libelle or getattr(m, 'nom', 'N/D'))
                    c[2].write(f"**{m.coefficient}**")
                    
                    btn_col1, btn_col2 = c[3].columns(2)
                    with btn_col1:
                        if st.button("✏️", key=f"edit_mat_{m.id}", help="Modifier cette matière"):
                            st.session_state[f"editing_matiere_{m.id}"] = True
                    with btn_col2:
                        if st.button("🗑️", key=f"del_mat_{m.id}", help="Supprimer / Archiver"):
                            st.session_state[f"deleting_matiere_{m.id}"] = True

                    # --- SUPPRESSION / ARCHIVAGE ---
                    if st.session_state.get(f"deleting_matiere_{m.id}", False):
                        st.warning(f"Retirer la matière **{m.libelle}** de la classe {classe_selectionnee.libelle} ?")
                        col_conf1, col_conf2 = st.columns(2)
                        with col_conf1:
                            if st.button("Confirmer", key=f"conf_del_mat_{m.id}", type="primary"):
                                nom_mat = m.libelle
                                if has_soft_delete:
                                    m.deleted_at = datetime.now()
                                    db.commit()
                                else:
                                    db.delete(m)
                                    db.commit()

                                audit_log = JournalActivite(
                                    username=username,
                                    school_id=school_id,
                                    module="Gestion des Matières",
                                    statut="Critique",
                                    action=f"Retrait de la matière {nom_mat} de la classe {classe_selectionnee.libelle}",
                                    valeur_avant=f"Actif (Coef: {m.coefficient})",
                                    valeur_apres="Supprimé"
                                )
                                db.add(audit_log)
                                db.commit()

                                st.success("Matière retirée avec succès !")
                                st.session_state[f"deleting_matiere_{m.id}"] = False
                                st.rerun()
                        with col_conf2:
                            if st.button("Annuler", key=f"canc_del_mat_{m.id}"):
                                st.session_state[f"deleting_matiere_{m.id}"] = False
                                st.rerun()

                    # --- MODIFICATION ---
                    if st.session_state.get(f"editing_matiere_{m.id}", False):
                        with st.form(key=f"form_edit_matiere_{m.id}"):
                            st.markdown(f"**Modifier : {m.libelle}** (Classe : {classe_selectionnee.libelle})")
                            new_code = st.text_input("Code", value=m.code or "")
                            new_libelle = st.text_input("Intitulé", value=m.libelle or getattr(m, 'nom', ''))
                            new_coef = st.number_input("Coefficient", value=float(m.coefficient or 1.0), step=0.5, min_value=0.5)
                            
                            sub_edit = st.form_submit_button("Enregistrer", type="primary")
                            canc_edit = st.form_submit_button("Annuler")

                            if sub_edit:
                                ancienne_val = f"Lib: {m.libelle} | Coef: {m.coefficient}"
                                nouvelle_val = f"Lib: {new_libelle} | Coef: {new_coef}"

                                m.code = new_code.upper()
                                if hasattr(m, 'libelle'):
                                    m.libelle = new_libelle
                                if hasattr(m, 'nom'):
                                    m.nom = new_libelle
                                m.coefficient = new_coef
                                db.commit()

                                audit_log = JournalActivite(
                                    username=username,
                                    school_id=school_id,
                                    module="Gestion des Matières",
                                    statut="Critique",
                                    action=f"Modification matière {new_libelle} pour {classe_selectionnee.libelle}",
                                    valeur_avant=ancienne_val,
                                    valeur_apres=nouvelle_val
                                )
                                db.add(audit_log)
                                db.commit()

                                st.success("Mise à jour effectuée !")
                                st.session_state[f"editing_matiere_{m.id}"] = False
                                st.rerun()
                            if canc_edit:
                                st.session_state[f"editing_matiere_{m.id}"] = False
                                st.rerun()
                    st.markdown("<hr style='margin: 0.2rem 0; border-color: rgba(255,255,255,0.05);'>", unsafe_allow_html=True)

        # --- ONGLET 2 : AJOUT D'UNE MATIÈRE À LA CLASSE SÉLECTIONNÉE ---
        with tab_ajout:
            st.markdown(f"### Ajouter une matière pour : **{classe_selectionnee.libelle}**")
            with st.form("form_ajout_matiere_classe"):
                code_m = st.text_input("Code de la matière (ex: MATHS, PHILO, HG)")
                libelle_m = st.text_input("Intitulé de la matière (ex: Mathématiques, Philosophie)")
                coefficient_m = st.number_input("Coefficient dans cette classe", min_value=0.5, value=2.0, step=0.5)
                
                submitted = st.form_submit_button("Enregistrer la matière", type="primary")
                if submitted:
                    if not libelle_m or not code_m:
                        st.error("Le code et l'intitulé de la matière sont obligatoires.")
                    else:
                        doublon = db.query(Matiere).filter(
                            Matiere.classe_id == classe_selectionnee.id,
                            Matiere.code == code_m.upper()
                        ).first()

                        if doublon:
                            st.error(f"⚠️ La matière avec le code '{code_m.upper()}' existe déjà pour la classe **{classe_selectionnee.libelle}**.")
                        else:
                            kwargs = {
                                "school_id": school_id,
                                "code": code_m.upper(),
                                "coefficient": coefficient_m,
                                "cycle": niveau_actif,
                                "classe_id": classe_selectionnee.id
                            }
                            if hasattr(Matiere, 'libelle'):
                                kwargs["libelle"] = libelle_m
                            if hasattr(Matiere, 'nom'):
                                kwargs["nom"] = libelle_m

                            nouvelle_matiere = Matiere(**kwargs)
                            db.add(nouvelle_matiere)
                            db.commit()
                            
                            audit_log = JournalActivite(
                                username=username,
                                school_id=school_id,
                                module="Gestion des Matières",
                                statut="Succès",
                                action=f"Ajout de {libelle_m} (Coef: {coefficient_m}) à la classe {classe_selectionnee.libelle}",
                                valeur_avant="Inexistante",
                                valeur_apres=f"Active pour {classe_selectionnee.libelle}"
                            )
                            db.add(audit_log)
                            db.commit()
                            
                            st.success(f"Matière '{libelle_m}' ajoutée avec succès à la classe **{classe_selectionnee.libelle}** !")
                            st.rerun()
    finally:
        db.close()

afficher_matieres = afficher_matieres
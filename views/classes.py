import streamlit as st
from datetime import datetime
from database.db_config import SessionLocal
from database.models import Classe
from database.audit import log_action_erp

def afficher_classes(niveau_actif="Collège"):
    st.subheader("🏫 Gestion des Classes & Grilles Tarifs")
    st.markdown("Configuration des classes et des frais associés avec traçabilité ERP et archivage sécurisé.")
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
        tab_liste, tab_ajout = st.tabs(["📋 Liste des Classes", "➕ Ajouter une Classe"])

        # --- REQUÊTE COMMUNE AVEC ISOLATION MULTI-TENANT ET FILTRE ROBUSTE ---
        query = db.query(Classe).filter(
            Classe.cycle.ilike(niveau_actif.strip()),
            Classe.deleted_at.is_(None)
        )

        if not is_super_admin and school_id:
            query = query.filter(Classe.school_id == school_id)

        classes = query.order_by(Classe.libelle).all()

        with tab_liste:
            st.markdown(f"### Classes et Grilles Tarifs — Établissement ({niveau_actif})")

            # --- TABLEAU DE BORD / KPIS FINANCIERS ---
            if classes:
                total_classes = len(classes)
                capacite_totale = sum(c.capacite or 0 for c in classes)
                scolarite_moyenne = sum(c.frais_scolarite or 0 for c in classes) / total_classes if total_classes > 0 else 0

                kpi1, kpi2, kpi3 = st.columns(3)
                with kpi1:
                    st.metric("Total Classes Actives", total_classes)
                with kpi2:
                    st.metric("Capacité Totale d'Accueil", f"{capacite_totale} Places")
                with kpi3:
                    st.metric("Scolarité Moyenne", f"{f'{scolarite_moyenne:,.0f}'.replace(',', ' ')} FCFA")
                
                st.markdown("---")

            if not classes:
                st.info(f"Aucune classe enregistrée ou active pour le cycle **{niveau_actif}** dans cet établissement.")
            else:
                cols = st.columns([1.8, 1.2, 1.3, 1.3, 1.3, 1.3, 1.3, 2])
                cols[0].markdown("**Classe**")
                cols[1].markdown("**Capacité**")
                cols[2].markdown("**Scolarité**")
                cols[3].markdown("**Inscription**")
                cols[4].markdown("**Transport**")
                cols[5].markdown("**Cantine**")
                cols[6].markdown("**COGES**")
                cols[7].markdown("**Actions**")
                st.markdown("---")

                for c in classes:
                    # Formatage francophone des montants (séparateur de milliers par espace)
                    scol_str = f"{c.frais_scolarite:,.0f}".replace(",", " ") if c.frais_scolarite else "0"
                    insc_str = f"{c.frais_inscription:,.0f}".replace(",", " ") if c.frais_inscription else "0"
                    trans_str = f"{c.frais_transport:,.0f}".replace(",", " ") if c.frais_transport else "0"
                    cant_str = f"{c.frais_cantine:,.0f}".replace(",", " ") if c.frais_cantine else "0"
                    coges_val = getattr(c, 'frais_coges', 0.0)
                    coges_str = f"{coges_val:,.0f}".replace(",", " ") if coges_val else "0"

                    col = st.columns([1.8, 1.2, 1.3, 1.3, 1.3, 1.3, 1.3, 2])
                    col[0].write(c.libelle)
                    col[1].write(c.capacite)
                    col[2].write(f"{scol_str} F")
                    col[3].write(f"{insc_str} F")
                    col[4].write(f"{trans_str} F")
                    col[5].write(f"{cant_str} F")
                    col[6].write(f"{coges_str} F")
                    
                    btn_col1, btn_col2 = col[7].columns(2)
                    with btn_col1:
                        if st.button("✏️", key=f"edit_classe_{c.id}", help="Modifier les tarifs"):
                            st.session_state[f"editing_classe_{c.id}"] = True
                    with btn_col2:
                        if st.button("🗑️", key=f"del_classe_{c.id}", help="Archiver (Soft Delete)"):
                            st.session_state[f"deleting_classe_{c.id}"] = True

                    # --- GESTION DU SOFT DELETE ---
                    if st.session_state.get(f"deleting_classe_{c.id}", False):
                        st.warning(f"Archiver la classe **{c.libelle}** ? (Elle n'apparaîtra plus mais ses données historiques seront conservées)")
                        c_del1, c_del2 = st.columns(2)
                        with c_del1:
                            if st.button("Confirmer l'archivage", key=f"conf_del_cls_{c.id}", type="primary"):
                                c.deleted_at = datetime.now()
                                db.commit()
                                
                                log_action_erp(
                                    module="Gestion des Classes",
                                    action=f"Archivage (Soft Delete) de la classe {c.libelle}",
                                    statut="Critique",
                                    valeur_avant="Active",
                                    valeur_apres="Archivée"
                                )
                                
                                st.success("Classe archivée avec succès !")
                                st.session_state[f"deleting_classe_{c.id}"] = False
                                st.rerun()
                        with c_del2:
                            if st.button("Annuler", key=f"canc_del_cls_{c.id}"):
                                st.session_state[f"deleting_classe_{c.id}"] = False
                                st.rerun()

                    # --- GESTION DE LA MODIFICATION TARIFAIRE ---
                    if st.session_state.get(f"editing_classe_{c.id}", False):
                        with st.form(key=f"form_edit_cls_{c.id}"):
                            st.markdown(f"**Modifier la grille tarifaire : {c.libelle}**")
                            new_lib = st.text_input("Nom de la classe", value=c.libelle)
                            new_cap = st.number_input("Capacité", value=int(c.capacite or 30))
                            new_scol = st.number_input("Scolarité", value=float(c.frais_scolarite or 0.0), step=5000.0)
                            new_insc = st.number_input("Inscription", value=float(c.frais_inscription or 0.0), step=1000.0)
                            new_trans = st.number_input("Transport", value=float(c.frais_transport or 0.0), step=1000.0)
                            new_cant = st.number_input("Cantine", value=float(c.frais_cantine or 0.0), step=1000.0)
                            new_coges = st.number_input("Frais COGES", value=float(getattr(c, 'frais_coges', 0.0)), step=500.0)
                            
                            sub_edit = st.form_submit_button("Enregistrer les modifications", type="primary")
                            canc_edit = st.form_submit_button("Annuler")

                            if sub_edit:
                                ancienne_valeur = f"Scol:{c.frais_scolarite}F | Insc:{c.frais_inscription}F | Transp:{c.frais_transport}F"
                                nouvelle_valeur = f"Scol:{new_scol}F | Insc:{new_insc}F | Transp:{new_trans}F"
                                
                                c.libelle = new_lib
                                c.capacite = new_cap
                                c.frais_scolarite = new_scol
                                c.frais_inscription = new_insc
                                c.frais_transport = new_trans
                                c.frais_cantine = new_cant
                                c.frais_coges = new_coges
                                db.commit()
                                
                                log_action_erp(
                                    module="Gestion des Classes",
                                    action=f"Modification des tarifs pour la classe {new_lib}",
                                    statut="Critique",
                                    valeur_avant=ancienne_valeur,
                                    valeur_apres=nouvelle_valeur
                                )
                                
                                st.success("Modifications tarifaires enregistrées et tracées !")
                                st.session_state[f"editing_classe_{c.id}"] = False
                                st.rerun()
                            if canc_edit:
                                st.session_state[f"editing_classe_{c.id}"] = False
                                st.rerun()
                    st.markdown("<hr style='margin: 0.2rem 0; border-color: rgba(255,255,255,0.05);'>", unsafe_allow_html=True)

        with tab_ajout:
            st.markdown("### Enregistrer une Nouvelle Classe")
            with st.form("form_ajout_classe"):
                libelle_c = st.text_input("Nom de la classe (ex: 6ème A)")
                capacite_c = st.number_input("Capacité maximale", min_value=1, value=35)
                scol_c = st.number_input("Frais de scolarité", min_value=0.0, value=0.0, step=5000.0)
                insc_c = st.number_input("Frais d'inscription", min_value=0.0, value=0.0, step=1000.0)
                trans_c = st.number_input("Frais de transport", min_value=0.0, value=0.0, step=1000.0)
                cant_c = st.number_input("Frais de cantine", min_value=0.0, value=0.0, step=1000.0)
                coges_c = st.number_input("Frais COGES", min_value=0.0, value=0.0, step=500.0)
                
                submitted = st.form_submit_button("Ajouter la classe", type="primary")
                if submitted:
                    if not libelle_c:
                        st.error("Le nom de la classe est obligatoire.")
                    else:
                        doublon = db.query(Classe).filter(
                            Classe.school_id == school_id,
                            Classe.libelle == libelle_c,
                            Classe.cycle.ilike(niveau_actif.strip()),
                            Classe.deleted_at.is_(None)
                        ).first()

                        if doublon:
                            st.error(f"⚠️ Une classe nommée '{libelle_c}' existe déjà pour ce cycle dans cet établissement.")
                        else:
                            nouvelle_classe = Classe(
                                school_id=school_id,
                                libelle=libelle_c,
                                niveau=libelle_c,
                                cycle=niveau_actif,
                                capacite=capacite_c,
                                frais_scolarite=scol_c,
                                frais_inscription=insc_c,
                                frais_transport=trans_c,
                                frais_cantine=cant_c,
                                frais_coges=coges_c
                            )
                            db.add(nouvelle_classe)
                            db.commit()
                            
                            scol_formatted = f"{scol_c:,.0f}".replace(",", " ")
                            log_action_erp(
                                module="Gestion des Classes",
                                action=f"Création de la classe {libelle_c} (Capacité: {capacite_c})",
                                statut="Succès",
                                valeur_avant="Inexistante",
                                valeur_apres=f"Scolarité fixée à {scol_formatted} F"
                            )
                            
                            st.success(f"Classe '{libelle_c}' ajoutée et tracée avec succès !")
                            st.rerun()
    finally:
        db.close()

# Alias de compatibilité
afficher_classes = afficher_classes
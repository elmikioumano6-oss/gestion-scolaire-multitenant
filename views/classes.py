import streamlit as st
from database.db_config import SessionLocal
from database.models import Classe

def afficher_classes(niveau_actif="Collège"):
    st.subheader("🏫 Gestion des Classes & Grilles Tarifs")
    st.markdown("Configuration des classes et des frais associés avec isolation multi-tenant stricte.")
    st.markdown("---")

    school_id = st.session_state.get("school_id")
    if not school_id:
        st.warning("⚠️ Veuillez vous connecter pour accéder à cette section.")
        return

    db = SessionLocal()
    try:
        tab_liste, tab_ajout = st.tabs(["📋 Liste des Classes", "➕ Ajouter une Classe"])

        with tab_liste:
            st.markdown(f"### Classes et Grilles Tarifs — Établissement ({niveau_actif})")
            
            classes = db.query(Classe).filter(
                Classe.school_id == school_id,
                Classe.cycle == niveau_actif
            ).all()

            if not classes:
                st.info(f"Aucune classe enregistrée pour le cycle **{niveau_actif}** dans cet établissement.")
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
                    col = st.columns([1.8, 1.2, 1.3, 1.3, 1.3, 1.3, 1.3, 2])
                    col[0].write(c.libelle)
                    col[1].write(c.capacite)
                    col[2].write(f"{c.frais_scolarite:,.0f} F")
                    col[3].write(f"{c.frais_inscription:,.0f} F")
                    col[4].write(f"{c.frais_transport:,.0f} F")
                    col[5].write(f"{c.frais_cantine:,.0f} F")
                    col[6].write(f"{getattr(c, 'frais_coges', 0.0):,.0f} F")
                    
                    btn_col1, btn_col2 = col[7].columns(2)
                    with btn_col1:
                        if st.button("✏️", key=f"edit_classe_{c.id}", help="Modifier"):
                            st.session_state[f"editing_classe_{c.id}"] = True
                    with btn_col2:
                        if st.button("🗑️", key=f"del_classe_{c.id}", help="Supprimer"):
                            st.session_state[f"deleting_classe_{c.id}"] = True

                    if st.session_state.get(f"deleting_classe_{c.id}", False):
                        st.warning(f"Supprimer la classe **{c.libelle}** ?")
                        c_del1, c_del2 = st.columns(2)
                        with c_del1:
                            if st.button("Confirmer", key=f"conf_del_cls_{c.id}"):
                                db.delete(c)
                                db.commit()
                                st.success("Classe supprimée !")
                                st.session_state[f"deleting_classe_{c.id}"] = False
                                st.rerun()
                        with c_del2:
                            if st.button("Annuler", key=f"canc_del_cls_{c.id}"):
                                st.session_state[f"deleting_classe_{c.id}"] = False
                                st.rerun()

                    if st.session_state.get(f"editing_classe_{c.id}", False):
                        with st.form(key=f"form_edit_cls_{c.id}"):
                            st.markdown(f"**Modifier : {c.libelle}**")
                            new_lib = st.text_input("Nom de la classe", value=c.libelle)
                            new_cap = st.number_input("Capacité", value=int(c.capacite or 30))
                            new_scol = st.number_input("Scolarité", value=float(c.frais_scolarite or 0.0))
                            new_insc = st.number_input("Inscription", value=float(c.frais_inscription or 0.0))
                            new_trans = st.number_input("Transport", value=float(c.frais_transport or 0.0))
                            new_cant = st.number_input("Cantine", value=float(c.frais_cantine or 0.0))
                            new_coges = st.number_input("COGES", value=float(getattr(c, 'frais_coges', 0.0)))
                            
                            sub_edit = st.form_submit_button("Enregistrer")
                            canc_edit = st.form_submit_button("Annuler")

                            if sub_edit:
                                c.libelle = new_lib
                                c.capacite = new_cap
                                c.frais_scolarite = new_scol
                                c.frais_inscription = new_insc
                                c.frais_transport = new_trans
                                c.frais_cantine = new_cant
                                c.frais_coges = new_coges
                                db.commit()
                                st.success("Modifications enregistrées !")
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
                
                submitted = st.form_submit_button("Ajouter la classe")
                if submitted:
                    if not libelle_c:
                        st.error("Le nom de la classe est obligatoire.")
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
                        st.success(f"Classe '{libelle_c}' ajoutée avec succès !")
                        st.rerun()
    finally:
        db.close()

# Alias de compatibilité
afficher_classes = afficher_classes
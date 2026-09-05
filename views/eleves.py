import streamlit as st
from datetime import datetime
from database.db_config import SessionLocal
from database.models import Eleve, Classe, Paiement
from database.audit import log_action_erp

def afficher_eleves(niveau_actif="Collège"):
    st.subheader("🎓 Inscription et Gestion des Élèves")
    st.markdown("Enregistrement et suivi des effectifs scolaires avec isolation multi-tenant stricte et traçabilité ERP.")
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
        tab_liste, tab_ajout = st.tabs(["📋 Liste des Élèves", "➕ Inscrire un Élève"])

        # --- REQUÊTE COMMUNE AVEC ISOLATION MULTI-TENANT ---
        query = db.query(Eleve).join(Classe).filter(
            Classe.cycle == niveau_actif,
            Eleve.deleted_at.is_(None)
        )

        if not is_super_admin and school_id:
            query = query.filter(Eleve.school_id == school_id)

        eleves = query.order_by(Eleve.nom).all()

        with tab_liste:
            st.markdown(f"### Effectifs Enregistrés — Établissement ({niveau_actif})")
            
            if eleves:
                total_eleves = len(eleves)
                garcons = sum(1 for e in eleves if getattr(e, 'sexe', '').lower() in ['masculin', 'm', 'garçon'])
                filles = sum(1 for e in eleves if getattr(e, 'sexe', '').lower() in ['féminin', 'f', 'fille'])

                kpi1, kpi2, kpi3 = st.columns(3)
                with kpi1:
                    st.metric("Total Élèves Inscrits", total_eleves)
                with kpi2:
                    st.metric("Garçons", garcons)
                with kpi3:
                    st.metric("Filles", filles)
                
                st.markdown("---")

            if not eleves:
                st.info(f"Aucun élève inscrit pour le cycle **{niveau_actif}**.")
            else:
                cols = st.columns([1.5, 2, 2, 1.2, 2, 1.5, 2])
                cols[0].markdown("**Matricule**")
                cols[1].markdown("**Nom**")
                cols[2].markdown("**Prénom**")
                cols[3].markdown("**Sexe**")
                cols[4].markdown("**Classe**")
                cols[5].markdown("**Réduction**")
                cols[6].markdown("**Actions**")
                st.markdown("---")

                for e in eleves:
                    montant_red = getattr(e, 'montant_reduction', 0.0) or 0.0
                    red_str = f"{montant_red:,.0f}".replace(",", " ") if montant_red > 0 else "0"

                    c = st.columns([1.5, 2, 2, 1.2, 2, 1.5, 2])
                    c[0].write(e.matricule or "N/D")
                    c[1].write(e.nom)
                    c[2].write(e.prenom)
                    c[3].write(e.sexe or "N/D")
                    c[4].write(e.classe.libelle if e.classe else "N/D")
                    c[5].write(f"{red_str} FCFA")
                    
                    btn_col1, btn_col2 = c[6].columns(2)
                    with btn_col1:
                        if st.button("✏️", key=f"edit_eleve_{e.id}", help="Modifier cet élève"):
                            st.session_state[f"editing_eleve_{e.id}"] = True
                    with btn_col2:
                        if st.button("🗑️", key=f"del_eleve_{e.id}", help="Archiver (Soft Delete) cet élève"):
                            st.session_state[f"deleting_eleve_{e.id}"] = True

                    # Gestion du Soft Delete
                    if st.session_state.get(f"deleting_eleve_{e.id}", False):
                        st.warning(f"Voulez-vous vraiment archiver l'élève **{e.nom} {e.prenom}** ?")
                        c_del1, c_del2 = st.columns(2)
                        with c_del1:
                            if st.button("Confirmer l'archivage", key=f"conf_del_el_{e.id}", type="primary"):
                                e.deleted_at = datetime.now()
                                db.commit()

                                log_action_erp(
                                    module="Inscription Élèves",
                                    action=f"Archivage (Soft Delete) de l'élève {e.nom} {e.prenom} (Mat: {e.matricule})",
                                    statut="Critique",
                                    valeur_avant="Actif",
                                    valeur_apres="Archivé / Supprimé logiquement"
                                )

                                st.success("Élève archivé avec succès !")
                                st.session_state[f"deleting_eleve_{e.id}"] = False
                                st.rerun()
                        with c_del2:
                            if st.button("Annuler", key=f"canc_del_el_{e.id}"):
                                st.session_state[f"deleting_eleve_{e.id}"] = False
                                st.rerun()

                    # Gestion de la modification
                    if st.session_state.get(f"editing_eleve_{e.id}", False):
                        with st.form(key=f"form_edit_eleve_{e.id}"):
                            st.markdown(f"**Modifier l'élève : {e.nom} {e.prenom}**")
                            
                            classes_dispo = db.query(Classe).filter(
                                Classe.school_id == school_id,
                                Classe.cycle == niveau_actif,
                                Classe.deleted_at.is_(None)
                            ).all()
                            options_classes = {cl.libelle: cl.id for cl in classes_dispo}
                            current_classe_name = e.classe.libelle if e.classe and e.classe.libelle in options_classes else list(options_classes.keys())[0] if options_classes else ""

                            new_matricule = st.text_input("Matricule", value=e.matricule or "")
                            new_nom = st.text_input("Nom", value=e.nom or "")
                            new_prenom = st.text_input("Prénom", value=e.prenom or "")
                            
                            sexes = ["Masculin", "Féminin"]
                            idx_sexe = sexes.index(e.sexe) if e.sexe in sexes else 0
                            new_sexe = st.selectbox("Sexe", sexes, index=idx_sexe)
                            
                            class_names = list(options_classes.keys())
                            idx_cls = class_names.index(current_classe_name) if current_classe_name in class_names else 0
                            new_classe_nom = st.selectbox("Classe", class_names, index=idx_cls)
                            
                            types_red = ["Aucune", "Bourse scolaire", "Cas social", "Enfant d'enseignant", "Autre"]
                            idx_red = types_red.index(e.type_reduction) if e.type_reduction in types_red else 0
                            new_type_red = st.selectbox("Type de réduction", types_red, index=idx_red)
                            
                            new_montant_red = st.number_input("Montant de la réduction (FCFA)", value=float(e.montant_reduction or 0.0), step=5000.0)

                            sub_edit = st.form_submit_button("Enregistrer les modifications", type="primary")
                            canc_edit = st.form_submit_button("Annuler")

                            if sub_edit:
                                if not new_nom or not new_prenom or not new_matricule:
                                    st.error("Le nom, le prénom et le matricule sont obligatoires.")
                                else:
                                    ancienne_valeurs = f"Nom: {e.nom}, Prénom: {e.prenom}, Mat: {e.matricule}"
                                    
                                    e.matricule = new_matricule.strip()
                                    e.nom = new_nom.upper().strip()
                                    e.prenom = new_prenom.strip()
                                    e.sexe = new_sexe
                                    e.classe_id = options_classes[new_classe_nom]
                                    e.type_reduction = new_type_red
                                    e.montant_reduction = new_montant_red
                                    db.commit()

                                    nouvelles_valeurs = f"Nom: {e.nom}, Prénom: {e.prenom}, Mat: {e.matricule}"

                                    log_action_erp(
                                        module="Inscription Élèves",
                                        action=f"Modification des informations de l'élève ID {e.id}",
                                        statut="Critique",
                                        valeur_avant=ancienne_valeurs,
                                        valeur_apres=nouvelles_valeurs
                                    )

                                    st.success("Informations de l'élève modifiées et tracées avec succès !")
                                    st.session_state[f"editing_eleve_{e.id}"] = False
                                    st.rerun()
                            if canc_edit:
                                st.session_state[f"editing_eleve_{e.id}"] = False
                                st.rerun()
                    st.markdown("<hr style='margin: 0.2rem 0; border-color: rgba(255,255,255,0.05);'>", unsafe_allow_html=True)

        with tab_ajout:
            st.markdown("### Formulaire d'Inscription & Ventilation Financière")
            
            classes_dispo = db.query(Classe).filter(
                Classe.school_id == school_id,
                Classe.cycle == niveau_actif,
                Classe.deleted_at.is_(None)
            ).all()

            if not classes_dispo:
                st.warning(f"⚠️ Veuillez d'abord créer des classes pour le cycle **{niveau_actif}** dans le menu 'Classes & Tarifs'.")
                return

            # Dictionnaire pour retrouver facilement l'objet classe et ses tarifs
            dict_classes = {c.libelle: c for c in classes_dispo}
            options_classes = list(dict_classes.keys())

            with st.form("form_inscription_eleve"):
                col1, col2 = st.columns(2)
                with col1:
                    nom_e = st.text_input("Nom de l'élève")
                    prenom_e = st.text_input("Prénom de l'élève")
                    classe_choisie_nom = st.selectbox("Sélectionner la classe", options_classes)
                with col2:
                    sexe_e = st.selectbox("Sexe", ["Masculin", "Féminin"])
                    matricule_e = st.text_input("Matricule de l'élève (requis)")

                # --- RAPPEL VISUEL DE LA GRILLE TARIFAIRE DE LA CLASSE SÉLECTIONNÉE ---
                classe_obj_selectionnee = dict_classes.get(classe_choisie_nom)
                if classe_obj_selectionnee:
                    scol_ref = f"{classe_obj_selectionnee.frais_scolarite:,.0f}".replace(",", " ")
                    insc_ref = f"{classe_obj_selectionnee.frais_inscription:,.0f}".replace(",", " ")
                    coges_ref = f"{getattr(classe_obj_selectionnee, 'frais_coges', 0.0):,.0f}".replace(",", " ")
                    trans_ref = f"{classe_obj_selectionnee.frais_transport:,.0f}".replace(",", " ")
                    cant_ref = f"{classe_obj_selectionnee.frais_cantine:,.0f}".replace(",", " ")

                    st.info(
                        f"📌 **Grille tarifaire officielle de la classe ({classe_choisie_nom})** :\n"
                        f"- Scolarité : **{scol_ref} F** | Inscription : **{insc_ref} F** | COGES : **{coges_ref} F**\n"
                        f"- Transport : **{trans_ref} F** | Cantine : **{cant_ref} F**"
                    )

                st.markdown("#### 💰 Ventilation des Versements Initiaux à l'Inscription (FCFA)")
                col_v1, col_v2, col_v3 = st.columns(3)
                with col_v1:
                    versement_inscription = st.number_input("Part Inscription", min_value=0.0, value=float(classe_obj_selectionnee.frais_inscription or 0.0) if classe_obj_selectionnee else 0.0, step=1000.0)
                    versement_coges = st.number_input("Part COGES", min_value=0.0, value=float(getattr(classe_obj_selectionnee, 'frais_coges', 0.0)) if classe_obj_selectionnee else 0.0, step=500.0)
                with col_v2:
                    versement_scolarite = st.number_input("Acompte Scolarité (1ère Tranche)", min_value=0.0, value=0.0, step=5000.0)
                    versement_transport = st.number_input("Part Transport", min_value=0.0, value=0.0, step=1000.0)
                with col_v3:
                    versement_cantine = st.number_input("Part Cantine", min_value=0.0, value=0.0, step=1000.0)
                    mode_reglement = st.selectbox("Mode de règlement", ["Espèces", "Virement bancaire", "Chèque", "Mobile Money"])

                st.markdown("#### 🏷️ Réduction sur les Frais de Scolarité (Optionnel)")
                col_red1, col_red2 = st.columns(2)
                with col_red1:
                    type_reduction = st.selectbox("Type de réduction", ["Aucune", "Bourse scolaire", "Cas social", "Enfant d'enseignant", "Autre"])
                with col_red2:
                    montant_reduction = st.number_input("Montant de la réduction (FCFA)", min_value=0.0, value=0.0, step=5000.0)

                submitted = st.form_submit_button("Valider l'inscription & encaisser", type="primary")
                if submitted:
                    if not nom_e or not prenom_e or not matricule_e:
                        st.error("Le nom, le prénom et le matricule de l'élève sont obligatoires.")
                    else:
                        # Vérification d'unicité du matricule
                        doublon_mat = db.query(Eleve).filter(
                            Eleve.school_id == school_id,
                            Eleve.matricule == matricule_e.strip(),
                            Eleve.deleted_at.is_(None)
                        ).first()

                        if doublon_mat:
                            st.error(f"⚠️ Un élève avec le matricule '{matricule_e.strip()}' existe déjà dans cet établissement.")
                        else:
                            classe_id_sel = classe_obj_selectionnee.id
                            
                            nouvel_eleve = Eleve(
                                school_id=school_id,
                                nom=nom_e.upper().strip(),
                                prenom=prenom_e.strip(),
                                matricule=matricule_e.strip(),
                                sexe=sexe_e,
                                cycle=niveau_actif,
                                classe_id=classe_id_sel,
                                type_reduction=type_reduction if type_reduction != "Aucune" else "Aucune",
                                montant_reduction=montant_reduction
                            )
                            db.add(nouvel_eleve)
                            db.commit()
                            db.refresh(nouvel_eleve)

                            # Enregistrement des paiements ventilés pour chaque poste perçu
                            import random
                            versements_effectues = {
                                "Frais d'inscription": versement_inscription,
                                "Cotisation COGES": versement_coges,
                                "Scolarité (Acompte)": versement_scolarite,
                                "Frais de transport": versement_transport,
                                "Frais de cantine": versement_cantine
                            }

                            total_encaisse = 0.0
                            for motif_paiement, montant_verse in versements_effectues.items():
                                if montant_verse > 0:
                                    total_encaisse += montant_verse
                                    ref_recu = f"REC-{random.randint(10000, 99999)}"
                                    nouveau_paiement = Paiement(
                                        school_id=school_id,
                                        reference_recu=ref_recu,
                                        eleve_id=nouvel_eleve.id,
                                        montant=montant_verse,
                                        mode_reglement=mode_reglement,
                                        motif=motif_paiement,
                                        agent_caisse=st.session_state.get("username", "admin"),
                                        date_paiement=datetime.now()
                                    )
                                    db.add(nouveau_paiement)
                            db.commit()

                            log_action_erp(
                                module="Inscription Élèves",
                                action=f"Inscription de l'élève {nom_e.upper()} {prenom_e} (Mat: {matricule_e.strip()}) - Total encaissé: {total_encaisse:,.0f} F",
                                statut="Succès",
                                valeur_avant="Inexistant",
                                valeur_apres=f"Inscrit en {classe_choisie_nom} avec {total_encaisse:,.0f} F de versements initiaux"
                            )

                            st.success(f"Élève **{nom_e} {prenom_e}** inscrit avec succès ! Total encaissé à la caisse : **{total_encaisse:,.0f} FCFA**.")
                            st.rerun()
    finally:
        db.close()

# Alias de compatibilité
afficher_eleves = afficher_eleves
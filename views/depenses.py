from datetime import datetime
from database.audit import log_action_erp
from database.db_config import SessionLocal
from database.models import CahierTexte, Depense, Enseignant, School, Classe, Matiere
import pandas as pd
import streamlit as st


def formater_fcfa(montant):
    if montant is None:
        return "0"
    return f"{int(float(montant)):,}".replace(",", ".")


def afficher_depenses():
    st.subheader("📉 Gestion des Dépenses, Salaires & Acomptes")
    st.markdown("Suivi des charges opérationnelles, paie des salaires fixes, des acomptes et calcul des vacations par cycle avec traçabilité ERP.")
    st.markdown("---")

    school_id = st.session_state.get("school_id")
    is_super_admin = st.session_state.get("is_super_admin", False)
    school_name = st.session_state.get("school_name", "Établissement")
    cycle_en_cours = st.session_state.get("cycle_actif", "Collège")
    username_connecte = st.session_state.get("username", "admin")
    user_role = str(st.session_state.get("role", "")).lower()

    profil_autorise_annulation = (
        is_super_admin
        or ("directeur" in user_role)
        or ("comptable" in user_role)
        or ("admin" in user_role)
    )

    if not school_id and not is_super_admin:
        st.warning("⚠️ Veuillez vous connecter pour accéder à cette section.")
        return

    db = SessionLocal()
    try:
        target_school_id = school_id or 1

        tab_saisie, tab_historique = st.tabs([
            "➕ Enregistrer un Décaissement / Acompte",
            "📋 Historique & Contre-Passation",
        ])

        with tab_saisie:
            st.markdown(f"### Enregistrement des Sorties de Trésorerie — **{school_name} ({cycle_en_cours})**")

            type_saisie = st.radio(
                "Type de décaissement",
                [
                    "Dépense Opérationnelle Classique",
                    "Salaire Fixe (Permanent / Admin)",
                    "Acompte sur Salaire",
                    "Salaire Vacation (Horaire)",
                ],
                horizontal=True,
            )

            enseignants_db = db.query(Enseignant).filter(Enseignant.school_id == target_school_id).all()
            liste_profs = [f"{e.nom} {e.prenom}".strip() for e in enseignants_db]

            if type_saisie == "Acompte sur Salaire":
                with st.form("form_add_acompte"):
                    col1, col2 = st.columns(2)
                    with col1:
                        beneficiaire_acompte = st.text_input("Nom et Prénom du Personnel / Bénéficiaire *")
                        montant_acompte = st.number_input("Montant de l'acompte (FCFA) *", min_value=0.0, step=5000.0, value=0.0)
                        mois_concerne = st.selectbox(
                            "Mois de référence (Paie)",
                            ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"],
                            index=datetime.now().month - 1,
                        )
                    with col2:
                        ref_piece = st.text_input("N° de Bon d'Acompte / Référence *", placeholder="Ex: ACOMPTE-SEP-001")
                        mode_paiement = st.selectbox("Mode de versement", ["Espèces (Caisse)", "Virement Bancaire", "Mobile Money (Orange/Moov)"])
                        date_depense = st.date_input("Date de versement de l'acompte", value=datetime.now())

                    submitted_acompte = st.form_submit_button("💾 Valider et Enregistrer l'Acompte", type="primary")
                    if submitted_acompte:
                        ref_clean = ref_piece.strip()
                        libelle_final = f"Acompte sur salaire - {beneficiaire_acompte} (Mois : {mois_concerne})"
                        if not beneficiaire_acompte.strip() or montant_acompte <= 0:
                            st.error("⚠️ Veuillez renseigner le nom du bénéficiaire et un montant supérieur à zéro.")
                        elif not ref_clean:
                            st.error("⚠️ Le numéro de bon ou la référence est obligatoire.")
                        else:
                            doublon = db.query(Depense).filter(Depense.school_id == target_school_id, Depense.reference_piece == ref_clean).first()
                            if doublon:
                                st.error(f"⚠️ La référence '{ref_clean}' existe déjà.")
                            else:
                                nouvelle_depense = Depense(
                                    school_id=target_school_id,
                                    cycle=cycle_en_cours,
                                    libelle=libelle_final,
                                    montant=montant_acompte,
                                    categorie="Salaires Fixes & Personnel",
                                    reference_piece=ref_clean,
                                    date_depense=datetime.combine(date_depense, datetime.now().time()),
                                    auteur=username_connecte,
                                )
                                db.add(nouvelle_depense)
                                log_action_erp(
                                    module="Gestion des Dépenses & Acomptes",
                                    action=f"Versement Acompte : {libelle_final} ({formater_fcfa(montant_acompte)} FCFA)",
                                    statut="Critique",
                                    valeur_avant="0 FCFA",
                                    valeur_apres=f"{formater_fcfa(montant_acompte)} FCFA",
                                )
                                db.commit()
                                st.success("✅ Acompte enregistré avec succès !")
                                st.rerun()

            elif type_saisie == "Salaire Fixe (Permanent / Admin)":
                with st.form("form_add_salaire_fixe"):
                    col1, col2 = st.columns(2)
                    with col1:
                        beneficiaire = st.text_input("Nom et Prénom du Bénéficiaire *")
                        fonction_poste = st.selectbox("Fonction / Poste", ["Directeur", "Proviseur", "Censeur", "Surveillant Général", "Enseignant Permanent", "Secrétaire / Économe", "Personnel d'appui / Gardien"])
                        montant_fixe = st.number_input("Salaire Net Mensuel (FCFA) *", min_value=0.0, step=5000.0, value=0.0)
                    with col2:
                        mois_concerne = st.selectbox("Mois de paie", ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"], index=8)
                        ref_piece = st.text_input("N° de Bon de Caisse / Référence de paie *", placeholder="Ex: SAL-FIX-SEP-001")
                        mode_paiement = st.selectbox("Mode de décaissement", ["Espèces (Caisse)", "Virement Bancaire", "Mobile Money (Orange/Moov)"])
                        date_depense = st.date_input("Date du versement", value=datetime.now())

                    submitted_fixe = st.form_submit_button("💾 Valider et Enregistrer le Salaire Fixe", type="primary")
                    if submitted_fixe:
                        ref_clean = ref_piece.strip()
                        libelle_final = f"Salaire Fixe [{fonction_poste}] - {beneficiaire} (Mois : {mois_concerne})"
                        if not beneficiaire.strip() or montant_fixe <= 0:
                            st.error("⚠️ Veuillez renseigner le nom du bénéficiaire et un montant valide.")
                        elif not ref_clean:
                            st.error("⚠️ La référence est obligatoire.")
                        else:
                            doublon = db.query(Depense).filter(Depense.school_id == target_school_id, Depense.reference_piece == ref_clean).first()
                            if doublon:
                                st.error(f"⚠️ La référence '{ref_clean}' existe déjà.")
                            else:
                                nouvelle_depense = Depense(
                                    school_id=target_school_id,
                                    cycle=cycle_en_cours,
                                    libelle=libelle_final,
                                    montant=montant_fixe,
                                    categorie="Salaires Fixes & Personnel",
                                    reference_piece=ref_clean,
                                    date_depense=datetime.combine(date_depense, datetime.now().time()),
                                    auteur=username_connecte,
                                )
                                db.add(nouvelle_depense)
                                db.commit()
                                st.success("✅ Salaire fixe enregistré avec succès !")
                                st.rerun()

            elif type_saisie == "Salaire Vacation (Horaire)":
                col1, col2 = st.columns(2)
                with col1:
                    enseignant_concerne = st.selectbox(
                        "Enseignant / Vacataire *",
                        options=(liste_profs if liste_profs else ["Aucun enseignant enregistré"]),
                    )
                    cycle_vacation = st.selectbox("Cycle d'enseignement (Vacation)", ["Collège", "Lycée"], index=0 if cycle_en_cours == "Collège" else 1)

                    # --- MOTEUR DE CALCUL UNIFIÉ (Identique à la Fiche de Paie) ---
                    heures_auto = 0.0
                    if enseignants_db and enseignant_concerne != "Aucun enseignant enregistré":
                        prof_obj = next((e for e in enseignants_db if f"{e.nom} {e.prenom}".strip() == enseignant_concerne or e.nom in enseignant_concerne), None)
                        if prof_obj:
                            cahier_entries = db.query(CahierTexte).filter(CahierTexte.school_id == target_school_id).all()
                            classes_db = db.query(Classe).filter(Classe.school_id == target_school_id).all()
                            dict_classes_id = {c.id: c for c in classes_db}
                            matieres_db = db.query(Matiere).filter(Matiere.school_id == target_school_id).all()
                            dict_matieres_id = {m.id: m for m in matieres_db}

                            for entry in cahier_entries:
                                matched_ens_id = getattr(entry, "enseignant_id", None)
                                classe_entry = dict_classes_id.get(getattr(entry, "classe_id", None))

                                # Recours par matière et classe si l'ID direct est absent ou saisi par admin
                                if not matched_ens_id or str(getattr(entry, "auteur_saisie", "")).lower() in ["admin", "admin_rahmat", "directeur", "censeur"]:
                                    matiere_entree_id = getattr(entry, "matiere_id", None)
                                    classe_entree_id = getattr(entry, "classe_id", None)
                                    if matiere_entree_id and classe_entree_id:
                                        matiere_obj_db = dict_matieres_id.get(matiere_entree_id)
                                        nom_mat_db = str(getattr(matiere_obj_db, "libelle", "") or getattr(matiere_obj_db, "nom", "")).lower() if matiere_obj_db else ""
                                        mat_attr = str(getattr(prof_obj, "matieres_attribuees", "") or getattr(prof_obj, "matieres", "")).lower()
                                        cls_attr = str(getattr(prof_obj, "classes_attribuees", "") or getattr(prof_obj, "classes", "")).lower()
                                        if classe_entry and (classe_entry.libelle.lower() in cls_attr) and (nom_mat_db and nom_mat_db in mat_attr):
                                            matched_ens_id = prof_obj.id

                                # Recours textuel global par nom/prénom
                                if not matched_ens_id:
                                    texte_entree = f"{getattr(entry, 'auteur_saisie', '')} {getattr(entry, 'cours', '')} {getattr(entry, 'contenu', '')}".lower()
                                    nom = str(getattr(prof_obj, "nom", "")).strip().lower()
                                    prenom = str(getattr(prof_obj, "prenom", "")).strip().lower()
                                    if (nom and nom in texte_entree) or (prenom and prenom in texte_entree):
                                        matched_ens_id = prof_obj.id

                                if matched_ens_id == prof_obj.id:
                                    classe_str = f"{getattr(classe_entry, 'cycle', '')} {getattr(classe_entry, 'libelle', '')}".lower() if classe_entry else ""
                                    mots_lycee = ["lycée", "lycee", "2de", "2nd", "seconde", "1ere", "1ère", "premiere", "terminale", "tle"]
                                    is_lycee_cours = any(kw in classe_str for kw in mots_lycee) or (classe_entry and str(getattr(classe_entry, "cycle", "")).lower() == "lycée")
                                    cycle_nom = "Lycée" if is_lycee_cours else "Collège"

                                    if cycle_nom == cycle_vacation:
                                        duree_str = str(getattr(entry, "duree_seance", "1"))
                                        chiffres = "".join([c for c in duree_str if c.isdigit() or c == '.'])
                                        heures_auto += float(chiffres) if chiffres else 1.0

                    taux_defaut = 1500.0 if cycle_vacation == "Collège" else 2000.0
                    taux_horaire = st.number_input("Taux Horaire (FCFA)", min_value=0.0, step=100.0, value=taux_defaut)

                with col2:
                    mode_saisie_heures = st.radio("Source du volume horaire", ["Automatique (Cahier de texte)", "Saisie / Ajustement Manuel"], horizontal=True)
                    if mode_saisie_heures == "Automatique (Cahier de texte)":
                        nombre_heures = float(heures_auto)
                        st.info(f"📖 **Heures détectées :** {nombre_heures:g} h")
                    else:
                        nombre_heures = st.number_input("Nombre d'heures (Ajustement manuel) *", min_value=0.0, step=0.5, value=float(heures_auto))

                    montant_calcule = taux_horaire * nombre_heures
                    st.markdown(f"💰 **Montant Total Calculé :** `{formater_fcfa(montant_calcule)} FCFA`")

                with st.form("form_valider_vacation"):
                    col_f1, col_f2 = st.columns(2)
                    with col_f1:
                        ref_piece = st.text_input("N° de Bon de Caisse / Pièce de paie *", value="", placeholder="Ex: BC-VAC-001")
                    with col_f2:
                        mode_paiement = st.selectbox("Mode de décaissement", ["Espèces (Caisse)", "Virement Bancaire", "Mobile Money (Orange/Moov)"])
                    date_depense = st.date_input("Date du versement", value=datetime.now())

                    submitted_vac = st.form_submit_button("💾 Valider et Enregistrer la Vacation", type="primary")
                    if submitted_vac:
                        ref_clean = ref_piece.strip()
                        libelle_final = f"Salaire Vacation ({cycle_vacation}) - {enseignant_concerne} ({nombre_heures:g}h @ {formater_fcfa(taux_horaire)}F)"
                        if montant_calcule <= 0:
                            st.error("⚠️ Le montant total calculé doit être supérieur à zéro.")
                        elif not ref_clean:
                            st.error("⚠️ Le numéro de bon de caisse est obligatoire.")
                        else:
                            doublon = db.query(Depense).filter(Depense.school_id == target_school_id, Depense.reference_piece == ref_clean).first()
                            if doublon:
                                st.error(f"⚠️ La référence '{ref_clean}' existe déjà.")
                            else:
                                nouvelle_depense = Depense(
                                    school_id=target_school_id,
                                    cycle=cycle_en_cours,
                                    libelle=libelle_final,
                                    montant=montant_calcule,
                                    categorie="Salaires Fixes & Personnel",
                                    reference_piece=ref_clean,
                                    date_depense=datetime.combine(date_depense, datetime.now().time()),
                                    auteur=username_connecte,
                                )
                                db.add(nouvelle_depense)
                                db.commit()
                                st.success("✅ Vacation enregistrée avec succès !")
                                st.rerun()

            else:
                with st.form("form_add_depense_classique"):
                    col1, col2 = st.columns(2)
                    with col1:
                        libelle_depense = st.text_input("Libellé / Motif de la dépense *", placeholder="Ex: Achat de fournitures pédagogiques")
                        montant = st.number_input("Montant (FCFA) *", min_value=0.0, step=1000.0, value=0.0)
                        categorie = st.selectbox("Catégorie", ["Fournitures scolaires", "Maintenance & Réparations", "Charges administratives", "Énergie & Eau", "Divers"])
                    with col2:
                        ref_piece = st.text_input("N° de Pièce Justificative / Facture *", placeholder="Ex: BC-2026-001")
                        mode_paiement = st.selectbox("Mode de décaissement", ["Espèces", "Chèque", "Virement Bancaire", "Mobile Money (Orange/Moov)"])
                        date_depense = st.date_input("Date de la dépense", value=datetime.now())

                    submitted = st.form_submit_button("💾 Valider et Enregistrer", type="primary")
                    if submitted:
                        ref_clean = ref_piece.strip()
                        if not libelle_depense.strip() or montant <= 0:
                            st.error("⚠️ Veuillez renseigner des informations valides.")
                        elif not ref_clean:
                            st.error("⚠️ Le numéro de pièce justificative est obligatoire.")
                        else:
                            doublon = db.query(Depense).filter(Depense.school_id == target_school_id, Depense.reference_piece == ref_clean).first()
                            if doublon:
                                st.error(f"⚠️ La référence '{ref_clean}' existe déjà.")
                            else:
                                nouvelle_depense = Depense(
                                    school_id=target_school_id,
                                    cycle=cycle_en_cours,
                                    libelle=libelle_depense.strip(),
                                    montant=montant,
                                    categorie=categorie,
                                    reference_piece=ref_clean,
                                    date_depense=datetime.combine(date_depense, datetime.now().time()),
                                    auteur=username_connecte,
                                )
                                db.add(nouvelle_depense)
                                db.commit()
                                st.success("✅ Dépense enregistrée avec succès !")
                                st.rerun()

        with tab_historique:
            st.markdown(f"### Historique & Contre-Passation — **{school_name} ({cycle_en_cours})**")
            query_depenses = db.query(Depense).filter(Depense.cycle == cycle_en_cours)
            if not is_super_admin and school_id:
                query_depenses = query_depenses.filter(Depense.school_id == school_id)
            depenses_list = query_depenses.order_by(Depense.date_depense.desc()).all()

            if not depenses_list:
                st.info(f"📌 Aucune sortie enregistrée pour le cycle **{cycle_en_cours}**.")
            else:
                total_depenses = sum(d.montant for d in depenses_list)
                st.metric("💵 Total des Charges & Salaires du Cycle", f"{formater_fcfa(total_depenses)} FCFA")
                st.markdown("---")
                for d in depenses_list:
                    ref_p = d.reference_piece if hasattr(d, "reference_piece") and d.reference_piece else "Sans référence"
                    col_d1, col_d2, col_d3, col_d4 = st.columns([2, 1.5, 2.5, 1])
                    col_d1.write(f"**Pièce :** `{ref_p}`")
                    col_d2.write(f"**Montant :** {formater_fcfa(d.montant)} F")
                    col_d3.write(f"**Motif :** {d.libelle} *({d.categorie})*")
                    with col_d4:
                        if not ref_p.startswith("AVOIR-"):
                            if st.button("🔄 Contre-passer", key=f"contrepasser_depense_{d.id}"):
                                if not profil_autorise_annulation:
                                    st.error("🔒 Accès restreint.")
                                else:
                                    montant_d = float(d.montant)
                                    depense_avoir = Depense(
                                        school_id=target_school_id,
                                        cycle=cycle_en_cours,
                                        libelle=f"CONTRE-PASSATION (Avoir) - Réf: {ref_p} ({d.libelle})",
                                        montant=-montant_d,
                                        categorie=d.categorie,
                                        reference_piece=f"AVOIR-{ref_p}",
                                        date_depense=datetime.utcnow(),
                                        auteur=username_connecte,
                                    )
                                    db.add(depense_avoir)
                                    db.commit()
                                    st.success("✅ Contre-passation effectuée !")
                                    st.rerun()
    except Exception as e:
        st.error(f"Erreur technique : {e}")
    finally:
        db.close()

afficher_depenses = afficher_depenses
afficher_gestion_depenses = afficher_depenses
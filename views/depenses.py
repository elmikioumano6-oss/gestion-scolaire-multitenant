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


def calculer_net_exact_depuis_paie(db, target_school_id, beneficiaire_nom, mois_selectionne):
    try:
        enseignants_db = db.query(Enseignant).filter(Enseignant.school_id == target_school_id).all()
        if not enseignants_db:
            return 0.0

        dict_enseignants = {e.id: e for e in enseignants_db}
        classes_db = db.query(Classe).filter(Classe.school_id == target_school_id).all()
        dict_classes_id = {c.id: c for c in classes_db}
        matieres_db = db.query(Matiere).filter(Matiere.school_id == target_school_id).all()
        dict_matieres_id = {m.id: m for m in matieres_db}

        mapping_mois = {
            "septembre": 9, "octobre": 10, "novembre": 11, "decembre": 12, "décembre": 12,
            "janvier": 1, "février": 2, "fevrier": 2, "mars": 3, "avril": 4,
            "mai": 5, "juin": 6, "juillet": 7, "aout": 8, "août": 8
        }
        parties_mois = mois_selectionne.split()
        nom_mois = parties_mois[0].lower() if len(parties_mois) > 0 else "octobre"
        annee_mois = int(parties_mois[1]) if len(parties_mois) > 1 else 2026
        num_mois = mapping_mois.get(nom_mois, 10)

        cahier_entries = db.query(CahierTexte).filter(CahierTexte.school_id == target_school_id).all()

        heures_par_cycle = {ens.id: {"Collège": 0.0, "Lycée": 0.0} for ens in enseignants_db}
        cycles_detectes = {ens.id: set() for ens in enseignants_db}
        mots_lycee_kw = ["lycée", "lycee", "2de", "2nd", "seconde", "1ere", "1ère", "premiere", "terminale", "tle"]

        for entry in cahier_entries:
            try:
                date_c = getattr(entry, "date_cours", None)
                if date_c:
                    if isinstance(date_c, str):
                        dt_obj = datetime.strptime(date_c.strip()[:10], "%Y-%m-%d")
                    elif isinstance(date_c, datetime):
                        dt_obj = date_c
                    else:
                        dt_obj = None
                    if dt_obj and (dt_obj.month != num_mois or dt_obj.year != annee_mois):
                        continue

                classe_entry = dict_classes_id.get(getattr(entry, "classe_id", None))
                matched_ens_id = getattr(entry, "enseignant_id", None)

                if not matched_ens_id and classe_entry and getattr(entry, "matiere_id", None):
                    matiere_obj_db = dict_matieres_id.get(entry.matiere_id)
                    nom_mat_db = str(getattr(matiere_obj_db, "libelle", "") or getattr(matiere_obj_db, "nom", "")).lower() if matiere_obj_db else ""
                    for ens in enseignants_db:
                        mat_attr = str(getattr(ens, "matieres_attribuees", "") or getattr(ens, "matieres", "")).lower()
                        cls_attr = str(getattr(ens, "classes_attribuees", "") or getattr(ens, "classes", "")).lower()
                        if (classe_entry.libelle.lower() in cls_attr) and (nom_mat_db and nom_mat_db in mat_attr):
                            matched_ens_id = ens.id
                            break

                if not matched_ens_id:
                    texte_entree = f"{getattr(entry, 'auteur_saisie', '')} {getattr(entry, 'contenu', '')} {getattr(entry, 'titre', '')}".lower()
                    for ens in enseignants_db:
                        nom = str(getattr(ens, "nom", "") or "").strip().lower()
                        prenom = str(getattr(ens, "prenom", "") or "").strip().lower()
                        if (nom and nom in texte_entree) or (prenom and prenom in texte_entree):
                            matched_ens_id = ens.id
                            break

                if not matched_ens_id:
                    continue

                cycle_str = f"{getattr(classe_entry, 'cycle', '')} {getattr(classe_entry, 'libelle', '')}".lower() if classe_entry else ""
                is_lycee = any(kw in cycle_str for kw in mots_lycee_kw) or (classe_entry and str(getattr(classe_entry, "cycle", "")).lower() in ["lycee", "lycée"])
                cycle_nom = "Lycée" if is_lycee else "Collège"

                duree_str = str(getattr(entry, "duree_seance", "1"))
                chiffres = "".join([c for c in duree_str if c.isdigit() or c == '.'])
                duree_val = float(chiffres) if chiffres else 1.0

                heures_par_cycle[matched_ens_id][cycle_nom] += duree_val
                cycles_detectes[matched_ens_id].add(cycle_nom)
            except Exception:
                continue

        acomptes_depenses_dict = {}
        depenses_list = db.query(Depense).filter(Depense.school_id == target_school_id).all()
        for dep in depenses_list:
            libelle_dep = str(getattr(dep, "libelle", "") or "").lower()
            beneficiaire_dep = str(getattr(dep, "beneficiaire", "") or "").lower()
            if any(k in libelle_dep for k in ["acompte", "avance", "paie"]):
                montant_dep = float(getattr(dep, "montant", 0.0) or 0.0)
                for ens in enseignants_db:
                    nom_p = str(getattr(ens, "nom", "")).strip().lower()
                    prenom_p = str(getattr(ens, "prenom", "")).strip().lower()
                    nom_complet_ens = f"{nom_p} {prenom_p}".strip()
                    if (nom_p and (nom_p in libelle_dep or nom_p in beneficiaire_dep)) or (prenom_p and (prenom_p in libelle_dep or prenom_p in beneficiaire_dep)) or (nom_complet_ens and nom_complet_ens in libelle_dep):
                        acomptes_depenses_dict[ens.id] = acomptes_depenses_dict.get(ens.id, 0.0) + montant_dep

        for ens_id, cycles_dict in heures_par_cycle.items():
            ens = dict_enseignants.get(ens_id)
            if not ens:
                continue
            nom_ens = f"{getattr(ens, 'nom', '')} {getattr(ens, 'prenom', '')}".strip()
            if nom_ens.lower() != beneficiaire_nom.lower() and beneficiaire_nom.lower() not in nom_ens.lower():
                continue

            retenue = float(getattr(ens, "retenue", 0.0) or 0.0)
            acompte_base = float(getattr(ens, "acompte", 0.0) or 0.0)
            acompte_total = acompte_base + acomptes_depenses_dict.get(ens.id, 0.0)

            cycles_valides = cycles_detectes.get(ens_id, set())
            if not cycles_valides:
                cycles_valides = {"Collège"}
            list_cycles_ordre = list(cycles_valides)

            total_net_prof = 0.0
            for cycle_nom in ["Collège", "Lycée"]:
                heures = cycles_dict[cycle_nom]
                if cycle_nom not in cycles_valides and heures == 0:
                    continue
                taux_horaire = 2000.0 if cycle_nom == "Lycée" else 1500.0
                brut = heures * taux_horaire
                is_first_cycle = (cycle_nom == list_cycles_ordre[0]) if list_cycles_ordre else True
                net_a_payer = max(0.0, brut - (retenue if cycle_nom == "Collège" else 0.0) - (acompte_total if is_first_cycle else 0.0))
                total_net_prof += net_a_payer

            return total_net_prof
        return 0.0
    except Exception:
        return 0.0


def afficher_depenses():
    st.subheader("📉 Gestion des Dépenses, Salaires & Paiements Mynita")
    st.markdown("Suivi des charges opérationnelles, paie des salaires fixes, acomptes, vacations et règlements mobiles via Mynita avec traçabilité ERP.")
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

        tab_saisie, tab_mynita, tab_historique = st.tabs([
            "➕ Enregistrer un Décaissement / Acompte",
            "📲 Paiement Mobile Mynita",
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
                        mode_paiement = st.selectbox("Mode de versement", ["Espèces (Caisse)", "Virement Bancaire", "Mynita (Mobile Money)"])
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
                        mode_paiement = st.selectbox("Mode de décaissement", ["Espèces (Caisse)", "Virement Bancaire", "Mynita (Mobile Money)"])
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
                with st.form("form_valider_vacation"):
                    col1, col2 = st.columns(2)
                    with col1:
                        enseignant_concerne = st.selectbox(
                            "Enseignant / Vacataire *",
                            options=(liste_profs if liste_profs else ["Aucun enseignant enregistré"]),
                        )
                        index_defaut_cycle = 0 if cycle_en_cours == "Collège" else 1
                        cycle_vacation = st.selectbox("Cycle d'enseignement (Vacation)", ["Collège", "Lycée"], index=index_defaut_cycle)

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

                        dernier_bon = db.query(Depense).filter(Depense.school_id == target_school_id, Depense.reference_piece.like("BC-VAC-%")).order_by(Depense.id.desc()).first()
                        if dernier_bon and dernier_bon.reference_piece:
                            try:
                                dernier_num = int(dernier_bon.reference_piece.split("-")[-1])
                                prochain_num = dernier_num + 1
                            except ValueError:
                                prochain_num = 1
                        else:
                            prochain_num = 1
                        
                        defaut_ref_vac = f"BC-VAC-{prochain_num:03d}"
                        ref_piece = st.text_input("N° de Bon de Caisse / Pièce de paie *", value=defaut_ref_vac)

                        mode_paiement = st.selectbox("Mode de décaissement", ["Espèces (Caisse)", "Virement Bancaire", "Mynita (Mobile Money)"])
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
                        mode_paiement = st.selectbox("Mode de décaissement", ["Espèces", "Chèque", "Virement Bancaire", "Mynita (Mobile Money)"])
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

        # --- ONGLET PAIEMENT MOBILE Mynita ---
        with tab_mynita:
            st.markdown(f"### 📲 Décaissement Rapide via **Mynita (Mobile Money)** — **{school_name}**")
            st.markdown("Sélectionnez l'enseignant et le mois concerné : le montant net et le numéro du bénéficiaire se remplissent automatiquement.")
            
            col_sel1, col_sel2 = st.columns(2)
            with col_sel1:
                beneficiaire_mynita = st.selectbox("Bénéficiaire (Personnel / Enseignant) *", options=(liste_profs if liste_profs else ["Aucun personnel disponible"]), key="sel_prof_mynita")
            with col_sel2:
                mois_mynita = st.selectbox(
                    "Mois concerné",
                    ["Octobre 2026", "Novembre 2026", "Décembre 2026", "Janvier 2027", "Février 2027", "Mars 2027", "Avril 2027", "Mai 2027", "Juin 2027", "Juillet 2027", "Août 2027", "Septembre 2026"],
                    index=0,
                    key="sel_mois_mynita"
                )

            montant_net_exact = calculer_net_exact_depuis_paie(db, target_school_id, beneficiaire_mynita, mois_mynita)
            
            prof_selectionne_obj = next((e for e in enseignants_db if f"{e.nom} {e.prenom}".strip() == beneficiaire_mynita), None)
            tel_auto = ""
            if prof_selectionne_obj:
                tel_auto = getattr(prof_selectionne_obj, "telephone", "") or getattr(prof_selectionne_obj, "phone", "") or ""

            with st.form("form_paiement_mynita_auto"):
                col_m1, col_m2 = st.columns(2)
                with col_m1:
                    montant_mynita = st.number_input("Montant du transfert Mynita (FCFA) *", min_value=0.0, step=500.0, value=float(montant_net_exact))
                    numero_expediteur = st.text_input("N° Caisse École / Expéditeur Mynita (Saisie libre)", placeholder="Ex: 96 00 00 00")

                with col_m2:
                    dernier_mynita = db.query(Depense).filter(Depense.school_id == target_school_id, Depense.reference_piece.like("MYNITA-%")).order_by(Depense.id.desc()).first()
                    prochain_num_m = int(dernier_mynita.reference_piece.split("-")[-1]) + 1 if dernier_mynita and dernier_mynita.reference_piece else 1
                    defaut_ref_mynita = f"MYNITA-{prochain_num_m:03d}"
                    
                    ref_mynita = st.text_input("Référence / N° de Reçu Mynita *", value=defaut_ref_mynita)
                    numero_beneficiaire = st.text_input("N° de téléphone Mynita du bénéficiaire (Récepteur) *", value=str(tel_auto), placeholder="Ex: +227...")
                    date_mynita = st.date_input("Date du transfert Mynita", value=datetime.now(), key="date_mynita_picker")

                submitted_mynita = st.form_submit_button("🚀 Valider et Exécuter le Paiement Mynita", type="primary")
                if submitted_mynita:
                    ref_clean_m = ref_mynita.strip()
                    libelle_mynita_final = f"Paiement Mynita - {beneficiaire_mynita} (Mois : {mois_mynita}) [Caisse/Exp: {numero_expediteur} -> Vers: {numero_beneficiaire}]"
                    
                    if montant_mynita <= 0:
                        st.error("⚠️ Le montant du transfert Mynita doit être supérieur à zéro.")
                    elif not ref_clean_m:
                        st.error("⚠️ La référence Mynita est obligatoire.")
                    elif not numero_beneficiaire.strip():
                        st.error("⚠️ Le numéro de téléphone du bénéficiaire est obligatoire.")
                    else:
                        doublon_m = db.query(Depense).filter(Depense.school_id == target_school_id, Depense.reference_piece == ref_clean_m).first()
                        if doublon_m:
                            st.error(f"⚠️ La référence Mynita '{ref_clean_m}' existe déjà.")
                        else:
                            nouvelle_depense_m = Depense(
                                school_id=target_school_id,
                                cycle=cycle_en_cours,
                                libelle=libelle_mynita_final,
                                montant=montant_mynita,
                                categorie="Salaires Fixes & Personnel",
                                reference_piece=ref_clean_m,
                                date_depense=datetime.combine(date_mynita, datetime.min.time()),
                                auteur=username_connecte,
                            )
                            db.add(nouvelle_depense_m)
                            log_action_erp(
                                module="Gestion Mynita & Trésorerie",
                                action=f"Transfert Mynita (Caisse: {numero_expediteur} -> {numero_beneficiaire}) vers {beneficiaire_mynita} ({formater_fcfa(montant_mynita)} FCFA) - Réf: {ref_clean_m}",
                                statut="Critique",
                                valeur_avant="0 FCFA",
                                valeur_apres=f"{formater_fcfa(montant_mynita)} FCFA",
                            )
                            db.commit()
                            st.success(f"✅ Paiement Mynita de **{formater_fcfa(montant_mynita)} FCFA** validé pour **{beneficiaire_mynita}** (Réf: `{ref_clean_m}`) !")
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
                st.metric("💵 Total des Charges, Salaires & Paiements du Cycle", f"{formater_fcfa(total_depenses)} FCFA")
                st.markdown("---")
                
                for d in depenses_list:
                    ref_p = d.reference_piece if hasattr(d, "reference_piece") and d.reference_piece else "Sans référence"
                    col_d1, col_d2, col_d3, col_d4 = st.columns([2, 1.5, 2.5, 1.5])
                    col_d1.write(f"**Pièce :** `{ref_p}`")
                    col_d2.write(f"**Montant :** {formater_fcfa(d.montant)} F")
                    col_d3.write(f"**Motif :** {d.libelle} *({d.categorie})*")
                    
                    with col_d4:
                        if not ref_p.startswith("AVOIR-"):
                            if profil_autorise_annulation:
                                sub_col1, sub_col2 = st.columns(2)
                                with sub_col1:
                                    if st.button("🔄", key=f"contre_{d.id}", help="Contre-passer (Avoir)"):
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
                                        log_action_erp(
                                            module="Gestion des Dépenses & Acomptes",
                                            action=f"Contre-passation pièce {ref_p} ({formater_fcfa(montant_d)} FCFA)",
                                            statut="Critique",
                                            valeur_avant=f"{formater_fcfa(montant_d)} FCFA",
                                            valeur_apres=f"-{formater_fcfa(montant_d)} FCFA",
                                        )
                                        db.commit()
                                        st.success("✅ Contre-passation effectuée !")
                                        st.rerun()
                                with sub_col2:
                                    if st.button("🗑️", key=f"suppr_{d.id}", help="Supprimer définitivement (Admin uniquement)"):
                                        montant_d_suppr = float(d.montant)
                                        log_action_erp(
                                            module="Gestion des Dépenses & Acomptes",
                                            action=f"Suppression dépense {ref_p} ({formater_fcfa(montant_d_suppr)} FCFA)",
                                            statut="Critique",
                                            valeur_avant=f"{formater_fcfa(montant_d_suppr)} FCFA",
                                            valeur_apres="Supprimé",
                                        )
                                        db.delete(d)
                                        db.commit()
                                        st.success("✅ Dépense supprimée !")
                                        st.rerun()
                            else:
                                st.caption("🔒 Consultation seule")

    except Exception as e:
        st.error(f"Erreur technique : {e}")
    finally:
        db.close()

afficher_depenses = afficher_depenses
afficher_gestion_depenses = afficher_depenses
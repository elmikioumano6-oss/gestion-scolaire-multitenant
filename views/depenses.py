from datetime import datetime
from database.audit import log_action_erp
from database.db_config import SessionLocal
from database.models import CahierTexte, Depense, Enseignant, School
import pandas as pd
import streamlit as st


def formater_fcfa(montant):
    """Formate un nombre avec un point pour les milliers, sans décimales."""
    if montant is None:
        return "0"
    val = float(montant)
    return f"{int(val):,}".replace(",", ".")


def afficher_depenses():
    st.subheader("📉 Gestion des Dépenses & Salaires")
    st.markdown(
        "Suivi des charges opérationnelles, paie des salaires fixes et calcul"
        " des vacations par cycle avec récupération automatique ou ajustement"
        " manuel."
    )
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
            "➕ Enregistrer une Dépense / Salaire",
            "📋 Historique & Contre-Passation",
        ])

        with tab_saisie:
            st.markdown(
                f"### Enregistrement des Sorties de Trésorerie — **{school_name}"
                f" ({cycle_en_cours})**"
            )

            type_saisie = st.radio(
                "Type de décaissement",
                [
                    "Dépense Opérationnelle Classique",
                    "Salaire Fixe (Permanent / Admin)",
                    "Salaire Vacation (Horaire)",
                ],
                horizontal=True,
            )

            enseignants_db = (
                db.query(Enseignant)
                .filter(Enseignant.school_id == target_school_id)
                .all()
            )
            liste_profs = [f"{e.nom} {e.prenom}" for e in enseignants_db]

            # --- CAS 1 : SALAIRE VACATION ---
            if type_saisie == "Salaire Vacation (Horaire)":
                col1, col2 = st.columns(2)
                with col1:
                    enseignant_concerne = st.selectbox(
                        "Enseignant / Vacataire *",
                        options=(
                            liste_profs
                            if liste_profs
                            else ["Aucun enseignant enregistré"]
                        ),
                    )
                    cycle_vacation = st.selectbox(
                        "Cycle d'enseignement (Vacation)",
                        ["Collège", "Lycée"],
                        index=0 if cycle_en_cours == "Collège" else 1,
                    )

                    heures_auto = 0.0
                    if (
                        enseignants_db
                        and enseignant_concerne != "Aucun enseignant enregistré"
                    ):
                        nom_part = enseignant_concerne.split()[0]
                        prof_obj = next(
                            (e for e in enseignants_db if e.nom == nom_part),
                            None,
                        )
                        if prof_obj and hasattr(CahierTexte, "enseignant_id"):
                            q_ct = db.query(CahierTexte).filter(
                                CahierTexte.enseignant_id == prof_obj.id,
                                CahierTexte.cycle == cycle_vacation,
                            )
                            if hasattr(CahierTexte, "duree"):
                                heures_auto = (
                                    q_ct.with_entities(
                                        db.func.sum(CahierTexte.duree)
                                    ).scalar()
                                    or 0.0
                                )
                            else:
                                heures_auto = float(q_ct.count())

                    taux_defaut = (
                        1500.0 if cycle_vacation == "Collège" else 2000.0
                    )
                    taux_horaire = st.number_input(
                        "Taux Horaire (FCFA)",
                        min_value=0.0,
                        step=100.0,
                        value=taux_defaut,
                    )

                with col2:
                    mode_saisie_heures = st.radio(
                        "Source du volume horaire",
                        [
                            "Automatique (Cahier de texte)",
                            "Saisie / Ajustement Manuel",
                        ],
                        horizontal=True,
                    )

                    if mode_saisie_heures == "Automatique (Cahier de texte)":
                        nombre_heures = float(heures_auto)
                        st.info(f"📖 **Heures détectées :** {nombre_heures} h")
                    else:
                        nombre_heures = st.number_input(
                            "Nombre d'heures (Ajustement manuel) *",
                            min_value=0.0,
                            step=0.5,
                            value=float(heures_auto),
                        )

                    montant_calcule = taux_horaire * nombre_heures
                    st.markdown(
                        f"💰 **Montant Total Calculé :**"
                        f" `{formater_fcfa(montant_calcule)} FCFA`"
                    )

                with st.form("form_valider_vacation"):
                    col_f1, col_f2 = st.columns(2)
                    with col_f1:
                        ref_piece = st.text_input(
                            "N° de Bon de Caisse / Pièce de paie *",
                            value="",
                            placeholder="Ex: BC-VAC-001",
                        )
                    with col_f2:
                        mode_paiement = st.selectbox(
                            "Mode de décaissement",
                            [
                                "Espèces (Caisse)",
                                "Virement Bancaire",
                                "Mobile Money (Orange/Moov)",
                            ],
                        )
                    date_depense = st.date_input(
                        "Date du versement", value=datetime.now()
                    )

                    submitted_vac = st.form_submit_button(
                        "💾 Valider et Enregistrer la Vacation",
                        type="primary",
                    )
                    if submitted_vac:
                        ref_clean = ref_piece.strip()
                        libelle_final = f"Salaire Vacation ({cycle_vacation}) - {enseignant_concerne} ({nombre_heures}h @ {formater_fcfa(taux_horaire)}F)"
                        montant_final = montant_calcule
                        categorie_final = "Salaires & Vacations"

                        if montant_final <= 0:
                            st.error(
                                "⚠️ Le montant total calculé doit être supérieur"
                                " à zéro."
                            )
                        elif not ref_clean:
                            st.error(
                                "⚠️ Le numéro de bon de caisse est obligatoire."
                            )
                        else:
                            doublon_piece = (
                                db.query(Depense)
                                .filter(
                                    Depense.school_id == target_school_id,
                                    Depense.reference_piece == ref_clean,
                                )
                                .first()
                            )
                            if doublon_piece:
                                st.error(
                                    f"⚠️ La référence '{ref_clean}' existe déjà"
                                    " dans le système."
                                )
                            else:
                                nouvelle_depense = Depense(
                                    school_id=target_school_id,
                                    cycle=cycle_en_cours,
                                    libelle=libelle_final,
                                    montant=montant_final,
                                    categorie=categorie_final,
                                    reference_piece=ref_clean,
                                    mode_paiement=mode_paiement,
                                    date_depense=datetime.combine(
                                        date_depense, datetime.now().time()
                                    ),
                                    auteur=username_connecte,
                                )
                                db.add(nouvelle_depense)
                                log_action_erp(
                                    module="Gestion des Dépenses & Salaires",
                                    action=(
                                        f"Décaissement [{categorie_final}] :"
                                        f" {libelle_final}"
                                        f" ({formater_fcfa(montant_final)} FCFA)"
                                        f" - Réf: {ref_clean}"
                                    ),
                                    statut="Critique",
                                    valeur_avant="0 FCFA",
                                    valeur_apres=(
                                        f"{formater_fcfa(montant_final)} FCFA"
                                    ),
                                )
                                db.commit()
                                st.success(
                                    f"✅ Vacation de {formater_fcfa(montant_final)}"
                                    f" FCFA enregistrée avec succès sous la"
                                    f" référence **{ref_clean}** !"
                                )
                                st.rerun()

            # --- CAS 2 : SALAIRE FIXE OU DÉPENSE CLASSIQUE ---
            else:
                with st.form("form_add_depense_classique"):
                    col1, col2 = st.columns(2)
                    if type_saisie == "Salaire Fixe (Permanent / Admin)":
                        with col1:
                            beneficiaire = st.text_input(
                                "Nom et Prénom du Bénéficiaire *"
                            )
                            fonction_poste = st.selectbox(
                                "Fonction / Poste",
                                [
                                    "Directeur",
                                    "Proviseur",
                                    "Censeur",
                                    "Surveillant Général",
                                    "Enseignant Permanent",
                                    "Secrétaire / Économe",
                                    "Personnel d'appui / Gardien",
                                ],
                            )
                            montant_fixe = st.number_input(
                                "Salaire Net Mensuel (FCFA) *",
                                min_value=0.0,
                                step=5000.0,
                                value=0.0,
                            )
                        with col2:
                            mois_concerne = st.selectbox(
                                "Mois de paie",
                                [
                                    "Janvier",
                                    "Février",
                                    "Mars",
                                    "Avril",
                                    "Mai",
                                    "Juin",
                                    "Juillet",
                                    "Août",
                                    "Septembre",
                                    "Octobre",
                                    "Novembre",
                                    "Décembre",
                                ],
                            )
                            ref_piece = st.text_input(
                                "N° de Bon de Caisse / Référence de paie *",
                                placeholder="Ex: SAL-FIXE-OCT-001",
                            )
                            mode_paiement = st.selectbox(
                                "Mode de décaissement",
                                [
                                    "Espèces (Caisse)",
                                    "Virement Bancaire",
                                    "Mobile Money (Orange/Moov)",
                                ],
                            )
                            date_depense = st.date_input(
                                "Date du versement", value=datetime.now()
                            )

                        libelle_final = f"Salaire Fixe [{fonction_poste}] - {beneficiaire} (Mois : {mois_concerne})"
                        montant_final = montant_fixe
                        categorie_final = "Salaires Fixes & Personnel"

                    else:
                        with col1:
                            libelle_depense = st.text_input(
                                "Libellé / Motif de la dépense *",
                                placeholder=(
                                    "Ex: Achat de fournitures pédagogiques"
                                ),
                            )
                            montant = st.number_input(
                                "Montant (FCFA) *",
                                min_value=0.0,
                                step=1000.0,
                                value=0.0,
                            )
                            categorie = st.selectbox(
                                "Catégorie",
                                [
                                    "Fournitures scolaires",
                                    "Maintenance & Réparations",
                                    "Charges administratives",
                                    "Énergie & Eau",
                                    "Divers",
                                ],
                            )
                        with col2:
                            ref_piece = st.text_input(
                                "N° de Pièce Justificative / Facture *",
                                placeholder="Ex: BC-2026-001",
                            )
                            mode_paiement = st.selectbox(
                                "Mode de décaissement",
                                [
                                    "Espèces",
                                    "Chèque",
                                    "Virement Bancaire",
                                    "Mobile Money (Orange/Moov)",
                                ],
                            )
                            date_depense = st.date_input(
                                "Date de la dépense", value=datetime.now()
                            )

                        libelle_final = (
                            libelle_depense.strip()
                            if "libelle_depense" in locals()
                            else ""
                        )
                        montant_final = (
                            montant if "montant" in locals() else 0.0
                        )
                        categorie_final = (
                            categorie if "categorie" in locals() else "Divers"
                        )

                    submitted = st.form_submit_button(
                        "💾 Valider et Enregistrer", type="primary"
                    )
                    if submitted:
                        ref_clean = ref_piece.strip()
                        if not libelle_final or montant_final <= 0:
                            st.error(
                                "⚠️ Veuillez renseigner des informations valides"
                                " (montant supérieur à zéro)."
                            )
                        elif not ref_clean:
                            st.error(
                                "⚠️ Le numéro de pièce justificative /"
                                " référence est obligatoire."
                            )
                        else:
                            doublon_piece = (
                                db.query(Depense)
                                .filter(
                                    Depense.school_id == target_school_id,
                                    Depense.reference_piece == ref_clean,
                                )
                                .first()
                            )
                            if doublon_piece:
                                st.error(
                                    f"⚠️ La référence '{ref_clean}' existe"
                                    " déjà dans le système."
                                )
                            else:
                                nouvelle_depense = Depense(
                                    school_id=target_school_id,
                                    cycle=cycle_en_cours,
                                    libelle=libelle_final,
                                    montant=montant_final,
                                    categorie=categorie_final,
                                    reference_piece=ref_clean,
                                    mode_paiement=mode_paiement,
                                    date_depense=datetime.combine(
                                        date_depense, datetime.now().time()
                                    ),
                                    auteur=username_connecte,
                                )
                                db.add(nouvelle_depense)
                                log_action_erp(
                                    module="Gestion des Dépenses & Salaires",
                                    action=(
                                        f"Décaissement [{categorie_final}] :"
                                        f" {libelle_final}"
                                        f" ({formater_fcfa(montant_final)} FCFA)"
                                        f" - Réf: {ref_clean}"
                                    ),
                                    statut="Critique",
                                    valeur_avant="0 FCFA",
                                    valeur_apres=(
                                        f"{formater_fcfa(montant_final)} FCFA"
                                    ),
                                )
                                db.commit()
                                st.success(
                                    f"✅ Décaissement de"
                                    f" {formater_fcfa(montant_final)} FCFA"
                                    f" ('{libelle_final}') enregistré sous"
                                    f" la référence **{ref_clean}** !"
                                )
                                st.rerun()

        with tab_historique:
            st.markdown(
                f"### Historique & Contre-Passation — **{school_name}"
                f" ({cycle_en_cours})**"
            )
            query_depenses = db.query(Depense).filter(
                Depense.cycle == cycle_en_cours
            )
            if not is_super_admin and school_id:
                query_depenses = query_depenses.filter(
                    Depense.school_id == school_id
                )
            depenses_list = (
                query_depenses.order_by(Depense.date_depense.desc()).all()
            )

            if not depenses_list:
                st.info(
                    f"📌 Aucune sortie enregistrée pour le cycle **{cycle_en_cours}**."
                )
            else:
                total_depenses = sum(d.montant for d in depenses_list)
                st.metric(
                    "💵 Total des Charges & Salaires du Cycle",
                    f"{formater_fcfa(total_depenses)} FCFA",
                )
                st.markdown("---")
                st.markdown(
                    "#### 🔍 Liste détaillée et gestion des contre-passations"
                )

                for d in depenses_list:
                    ref_p = (
                        d.reference_piece
                        if hasattr(d, "reference_piece") and d.reference_piece
                        else "Sans référence"
                    )
                    col_d1, col_d2, col_d3, col_d4 = st.columns(
                        [2, 1.5, 2.5, 1]
                    )
                    col_d1.write(f"**Pièce :** `{ref_p}`")
                    col_d2.write(
                        f"**Montant :** {formater_fcfa(d.montant)} F"
                    )
                    col_d3.write(f"**Motif :** {d.libelle} *({d.categorie})*")

                    with col_d4:
                        if not ref_p.startswith("AVOIR-"):
                            if st.button(
                                "🔄 Contre-passer",
                                key=f"contrepasser_depense_{d.id}",
                            ):
                                if not profil_autorise_annulation:
                                    st.error(
                                        "🔒 Accès restreint : Réservé aux"
                                        " Directeurs et Comptables."
                                    )
                                else:
                                    montant_d = float(d.montant)
                                    ref_orig = ref_p
                                    depense_avoir = Depense(
                                        school_id=target_school_id,
                                        cycle=cycle_en_cours,
                                        libelle=f"CONTRE-PASSATION (Avoir) - Réf: {ref_orig} ({d.libelle})",
                                        montant=-montant_d,
                                        categorie=d.categorie,
                                        reference_piece=f"AVOIR-{ref_orig}",
                                        mode_paiement=(
                                            "Régularisation Comptable"
                                        ),
                                        date_depense=datetime.utcnow(),
                                        auteur=username_connecte,
                                    )
                                    db.add(depense_avoir)
                                    log_action_erp(
                                        module="Gestion des Dépenses",
                                        action=(
                                            f"Contre-passation de décaissement de"
                                            f" {formater_fcfa(montant_d)} F"
                                            f" (Pièce d'avoir: AVOIR-{ref_orig})"
                                        ),
                                        statut="Critique",
                                        valeur_avant=(
                                            f"{formater_fcfa(montant_d)} FCFA"
                                        ),
                                        valeur_apres=(
                                            f"-{formater_fcfa(montant_d)}"
                                            " FCFA"
                                        ),
                                    )
                                    db.commit()
                                    st.success(
                                        "✅ Écriture de contre-passation"
                                        " générée avec succès !"
                                    )
                                    st.rerun()
                    st.markdown(
                        "<hr style='margin: 0.2rem 0;"
                        " border-color: rgba(255,255,255,0.05);'>",
                        unsafe_allow_html=True,
                    )
    finally:
        db.close()


afficher_depenses = afficher_depenses
afficher_gestion_depenses = afficher_depenses
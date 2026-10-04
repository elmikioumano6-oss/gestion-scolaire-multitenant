from datetime import datetime
import io
from database.audit import log_action_erp
from database.db_config import SessionLocal
from database.models import Classe, Depense, Eleve, Paiement, School
from database.queries import get_classes_cached, get_matieres_cached
import pandas as pd
import streamlit as st


def afficher_rapports():
    st.subheader("📑 Rapports & Bilan Financier Consolidé")
    st.markdown(
        "Synthèse macroscopique des flux de trésorerie avec ventilation "
        "analytique des salaires (fixes et vacations horaires) et des charges "
        "opérationnelles de l'établissement."
    )
    st.markdown("---")

    school_id = st.session_state.get("school_id")
    is_super_admin = st.session_state.get("is_super_admin", False)
    school_name = st.session_state.get("school_name", "Établissement")
    cycle_en_cours = st.session_state.get("cycle_actif", "Collège")

    if not school_id and not is_super_admin:
        st.warning("⚠️ Veuillez vous connecter pour accéder à cette section.")
        return

    db = SessionLocal()
    try:
        try:
            db.rollback()
        except Exception:
            pass

        # 1. Récupération des classes du cycle actif
        classes_query = db.query(Classe).filter(Classe.cycle == cycle_en_cours)
        if hasattr(Classe, "deleted_at"):
            classes_query = classes_query.filter(Classe.deleted_at.is_(None))
        if school_id:
            classes_query = classes_query.filter(Classe.school_id == school_id)
        classes_cycle = classes_query.all()

        classes_dict = {c.id: c for c in classes_cycle}
        classes_ids = list(classes_dict.keys())

        # Élèves du cycle actif
        eleves_cycle_query = db.query(Eleve)
        if hasattr(Eleve, "deleted_at"):
            eleves_cycle_query = eleves_cycle_query.filter(Eleve.deleted_at.is_(None))
        if school_id:
            eleves_cycle_query = eleves_cycle_query.filter(Eleve.school_id == school_id)
            
        if classes_ids:
            eleves_cycle_query = eleves_cycle_query.filter(Eleve.classe_id.in_(classes_ids))
        else:
            eleves_cycle_query = eleves_cycle_query.filter(Eleve.classe_id == -1)

        eleves_cycle_list = eleves_cycle_query.all()
        eleves_cycle_ids = [e.id for e in eleves_cycle_list]

        # Recettes du cycle actif uniquement
        recettes_cycle = 0.0
        if eleves_cycle_ids:
            p_cycle = db.query(Paiement).filter(Paiement.eleve_id.in_(eleves_cycle_ids)).all()
            recettes_cycle = sum(p.montant for p in p_cycle) if p_cycle else 0.0

        # Recettes globales de l'établissement
        tous_eleves_ecole_query = db.query(Eleve)
        if hasattr(Eleve, "deleted_at"):
            tous_eleves_ecole_query = tous_eleves_ecole_query.filter(Eleve.deleted_at.is_(None))
        if school_id:
            tous_eleves_ecole_query = tous_eleves_ecole_query.filter(Eleve.school_id == school_id)
        tous_eleves_ecole = tous_eleves_ecole_query.all()
        tous_eleves_ids = [e.id for e in tous_eleves_ecole]

        recettes_globales_ecole = 0.0
        if tous_eleves_ids:
            p_global = db.query(Paiement).filter(Paiement.eleve_id.in_(tous_eleves_ids)).all()
            recettes_globales_ecole = sum(p.montant for p in p_global) if p_global else 0.0

        # Organisation en onglets
        tab_bilan, tab_postes, tab_reductions = st.tabs([
            "📊 Bilan & Trésorerie",
            "🏷️ Ventilation par Poste (Scolarité, COGES, etc.)",
            "📉 Registre des Réductions",
        ])

        with tab_bilan:
            st.markdown(
                f"### Bilan Financier — **{school_name} (Cycle : {cycle_en_cours})**"
            )

            # --- FILTRES TEMPORELS POUR LES DÉPENSES ---
            st.markdown("#### 📅 Filtrer les Sorties par Période")
            col_f1, col_f2, _ = st.columns([2, 2, 4])
            with col_f1:
                annees_dispo = [str(y) for y in range(datetime.now().year, 2023, -1)]
                annee_selectionnee = st.selectbox(
                    "Année", options=["Toutes"] + annees_dispo, key="filtre_annee_depenses"
                )
            with col_f2:
                mois_options = {
                    "Tous": None, "Janvier": 1, "Février": 2, "Mars": 3, "Avril": 4,
                    "Mai": 5, "Juin": 6, "Juillet": 7, "Août": 8,
                    "Septembre": 9, "Octobre": 10, "Novembre": 11, "Décembre": 12
                }
                mois_selectionne = st.selectbox(
                    "Mois", options=list(mois_options.keys()), key="filtre_mois_depenses"
                )

            # Dépenses globales de l'établissement
            depenses_query = db.query(Depense)
            if school_id:
                depenses_query = depenses_query.filter(Depense.school_id == school_id)
            depenses_list = depenses_query.all()

            total_depenses_globales = 0.0
            total_salaires_fixes = 0.0
            total_salaires_vacations = 0.0
            total_charges_classiques = 0.0

            for d in depenses_list:
                if d.date_depense:
                    if annee_selectionnee != "Toutes" and d.date_depense.year != int(annee_selectionnee):
                        continue
                    if mois_selectionne != "Tous" and d.date_depense.month != mois_options[mois_selectionne]:
                        continue

                montant_d = float(d.montant or 0.0)
                total_depenses_globales += montant_d
                cat = str(getattr(d, "categorie", "")).lower()
                lib = str(getattr(d, "libelle", "")).lower()

                if "fixe" in cat or "fixe" in lib or "salaires fixes" in cat:
                    total_salaires_fixes += montant_d
                elif (
                    "vacation" in cat
                    or "vacation" in lib
                    or "salaires & vacations" in cat
                ):
                    total_salaires_vacations += montant_d
                else:
                    total_charges_classiques += montant_d

            # CORRECTION : Le solde net du cycle représente les encaissements propres du cycle, 
            # tandis que les charges globales sont présentées de manière distincte pour l'établissement.
            solde_net_cycle = recettes_cycle
            resultat_net_global = recettes_globales_ecole - total_depenses_globales

            # Calcul du taux de recouvrement du cycle en cours
            total_attendu_cycle = 0.0
            for classe in classes_cycle:
                frais_base = float(classe.frais_scolarite or 0.0) + float(
                    getattr(classe, "frais_coges", 0.0) or 0.0
                )
                eleves_classe = [e for e in eleves_cycle_list if e.classe_id == classe.id]
                for e in eleves_classe:
                    red = float(e.montant_reduction or 0.0)
                    total_attendu_cycle += max(0.0, frais_base - red)

            taux_recouvrement_cycle = (
                (recettes_cycle / total_attendu_cycle * 100)
                if total_attendu_cycle > 0
                else 0.0
            )

            # Affichage des métriques corrigées
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric(f"Total Encaissé ({cycle_en_cours})", f"{recettes_cycle:,.0f} FCFA")
            with col2:
                st.metric("Total Sorties Globales (École)", f"{total_depenses_globales:,.0f} FCFA")
            with col3:
                st.metric(
                    f"Solde Net en Caisse ({cycle_en_cours})",
                    f"{solde_net_cycle:,.0f} FCFA",
                    delta="Disponible",
                    delta_color="normal",
                )
            with col4:
                st.metric(
                    f"Recouvrement ({cycle_en_cours})", f"{taux_recouvrement_cycle:.1f}%"
                )

            st.markdown("---")
            st.markdown("#### 💳 Ventilation Analytique des Sorties Globales de l'Établissement")
            col_a1, col_a2, col_a3 = st.columns(3)
            with col_a1:
                st.metric("Salaires Fixes (Permanents/Admin)", f"{total_salaires_fixes:,.0f} FCFA")
            with col_a2:
                st.metric("Salaires Vacations (Horaires)", f"{total_salaires_vacations:,.0f} FCFA")
            with col_a3:
                st.metric("Charges Opérationnelles Classiques", f"{total_charges_classiques:,.0f} FCFA")

            st.markdown("---")
            st.markdown(
                f"### Bilan Consolidé & Impayés par Classe — **{school_name} "
                f"({cycle_en_cours})**"
            )

            if not classes_cycle:
                st.info(
                    f"📌 Aucune classe configurée pour le cycle **{cycle_en_cours}**."
                )
            else:
                rapport_data = []
                for classe in classes_cycle:
                    eleves_classe = [e for e in eleves_cycle_list if e.classe_id == classe.id]
                    eleves_classe_ids = [e.id for e in eleves_classe]

                    recettes_classe = 0.0
                    if eleves_classe_ids:
                        p_classe = (
                            db.query(Paiement)
                            .filter(Paiement.eleve_id.in_(eleves_classe_ids))
                            .all()
                        )
                        recettes_classe = (
                            sum(p.montant for p in p_classe) if p_classe else 0.0
                        )

                    frais_base_classe = float(classe.frais_scolarite or 0.0) + float(
                        getattr(classe, "frais_coges", 0.0) or 0.0
                    )
                    total_attendu_classe = 0.0
                    for e in eleves_classe:
                        red = float(e.montant_reduction or 0.0)
                        total_attendu_classe += max(0.0, frais_base_classe - red)

                    reste_a_recouvrer_classe = max(
                        0.0, total_attendu_classe - recettes_classe
                    )

                    classe_lib = classe.libelle if hasattr(classe, 'libelle') else getattr(classe, 'nom', 'N/A')
                    rapport_data.append({
                        "Classe": classe_lib,
                        "Niveau": getattr(classe, "niveau", "N/D"),
                        "Effectif": len(eleves_classe),
                        "Recettes (FCFA)": f"{recettes_classe:,.0f}",
                        "Reste à Recouvrer (FCFA)": f"{reste_a_recouvrer_classe:,.0f}",
                    })

                df_rapport = pd.DataFrame(rapport_data)
                st.dataframe(df_rapport, use_container_width=True)

                output_io = io.BytesIO()
                with pd.ExcelWriter(output_io, engine="openpyxl") as writer:
                    df_rapport.to_excel(
                        writer, index=False, sheet_name="Bilan_Consolide"
                    )
                st.download_button(
                    "📥 Télécharger le Bilan Consolidé (.xlsx)",
                    output_io.getvalue(),
                    f"Bilan_Consolide_{cycle_en_cours}.xlsx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )

        with tab_postes:
            st.markdown(
                f"### Ventilation Théorique par Poste de Recette — "
                f"**{cycle_en_cours}**"
            )
            st.markdown(
                "Analyse des redevances attendues ventilées par poste (Scolarité, "
                "Inscription, COGES, Cantine, Transport)."
            )

            total_scolarite = 0.0
            total_inscription = 0.0
            total_coges = 0.0
            total_cantine = 0.0
            total_transport = 0.0

            for classe in classes_cycle:
                eleves_classe_count = len(
                    [e for e in eleves_cycle_list if e.classe_id == classe.id]
                )
                total_scolarite += (
                    float(classe.frais_scolarite or 0.0) * eleves_classe_count
                )
                total_inscription += (
                    float(getattr(classe, "frais_inscription", 0.0) or 0.0)
                    * eleves_classe_count
                )
                total_coges += (
                    float(getattr(classe, "frais_coges", 0.0) or 0.0)
                    * eleves_classe_count
                )
                total_cantine += (
                    float(getattr(classe, "frais_cantine", 0.0) or 0.0)
                    * eleves_classe_count
                )
                total_transport += (
                    float(getattr(classe, "frais_transport", 0.0) or 0.0)
                    * eleves_classe_count
                )

            data_postes = [
                {
                    "Poste de Recette": "Frais de Scolarité",
                    "Montant Total Attendu (FCFA)": total_scolarite,
                },
                {
                    "Poste de Recette": "Frais d'Inscription",
                    "Montant Total Attendu (FCFA)": total_inscription,
                },
                {
                    "Poste de Recette": "Redevance COGES",
                    "Montant Total Attendu (FCFA)": total_coges,
                },
                {
                    "Poste de Recette": "Frais de Cantine",
                    "Montant Total Attendu (FCFA)": total_cantine,
                },
                {
                    "Poste de Recette": "Frais de Transport",
                    "Montant Total Attendu (FCFA)": total_transport,
                },
            ]

            df_postes = pd.DataFrame(data_postes)
            st.dataframe(df_postes, use_container_width=True)

        with tab_reductions:
            st.markdown(
                f"### Registre Nominatif des Réductions & Exonérations — "
                f"**{cycle_en_cours}**"
            )
            st.markdown(
                "Suivi détaillé de tous les élèves bénéficiant d'une remise sur leur "
                "scolarité."
            )

            eleves_avec_reduction = [
                e
                for e in eleves_cycle_list
                if float(getattr(e, "montant_reduction", 0.0) or 0.0) > 0
            ]

            if not eleves_avec_reduction:
                st.info(
                    f"📌 Aucune réduction ou exonération n'a été enregistrée pour les "
                    f"élèves du cycle **{cycle_en_cours}**."
                )
            else:
                data_red = []
                total_remises = 0.0
                for e in eleves_avec_reduction:
                    classe = classes_dict.get(e.classe_id) if e.classe_id else None
                    montant_red = float(e.montant_reduction or 0.0)
                    total_remises += montant_red

                    classe_lib = (classe.libelle if hasattr(classe, 'libelle') else getattr(classe, 'nom', 'Non assignée')) if classe else "Non assignée"
                    data_red.append({
                        "Matricule": getattr(e, "matricule", "N/A"),
                        "Élève": f"{e.nom} {e.prenom}",
                        "Classe": classe_lib,
                        "Type / Motif de Réduction": (
                            getattr(e, "type_reduction", "Standard") or "Standard"
                        ),
                        "Montant Réduction (FCFA)": montant_red,
                    })

                df_red = pd.DataFrame(data_red)
                st.dataframe(df_red, use_container_width=True)
                st.metric(
                    "Total Cumulé des Remises Accordées", f"{total_remises:,.0f} FCFA"
                )

    finally:
        db.close()

# Alias de compatibilité exhaustive pour le routeur app.py
afficher_rapports = afficher_rapports
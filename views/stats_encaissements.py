from datetime import datetime
import io
from database.audit import log_action_erp
from database.db_config import SessionLocal
from database.models import ActivityLog, Classe, Eleve, Paiement, School
from database.queries import get_classes_cached, get_matieres_cached
import pandas as pd
import streamlit as st


def afficher_stats_encaissements():
    st.subheader("📊 Statistiques des Encaissements & Recouvrement")
    st.markdown(
        "Analyse avancée des flux de trésorerie, suivi des créances et rapports"
        " financiers par cycle et par établissement avec isolation multi-tenant"
        " stricte."
    )
    st.markdown("---")

    school_id = st.session_state.get("school_id")
    is_super_admin = st.session_state.get("is_super_admin", False)
    cycle_en_cours = st.session_state.get("cycle_actif", "Collège")
    username_connecte = st.session_state.get("username", "admin")

    db = SessionLocal()
    try:
        target_school_id = school_id
        if is_super_admin and not target_school_id:
            ecole_defaut = db.query(School).first()
            target_school_id = ecole_defaut.id if ecole_defaut else 1

        ecole_active_id = school_id if school_id else target_school_id

        ecole_courante = (
            db.query(School).filter(School.id == ecole_active_id).first()
        )
        school_name = (
            ecole_courante.nom
            if ecole_courante
            else st.session_state.get("school_name", "Établissement")
        )
    finally:
        db.close()

    if not school_id and not is_super_admin:
        st.warning("⚠️ Veuillez vous connecter pour accéder à cette section.")
        return

    db = SessionLocal()
    try:
        # Récupération sécurisée des classes du cycle actif
        classes_query = db.query(Classe).filter(
            Classe.cycle == cycle_en_cours, Classe.school_id == ecole_active_id
        )
        if hasattr(Classe, "deleted_at"):
            classes_query = classes_query.filter(Classe.deleted_at.is_(None))
        classes_cycle = classes_query.all()

        def get_classe_libelle(c):
            for attr in ['libelle', 'nom', 'name', 'titre']:
                if hasattr(c, attr) and getattr(c, attr):
                    return getattr(c, attr)
            return f"Classe {c.id}"

        classes_dict = {c.id: c for c in classes_cycle}
        classes_ids = list(classes_dict.keys())

        # Récupération sécurisée des élèves rattachés strictement aux classes du cycle
        eleves_query = db.query(Eleve).filter(Eleve.school_id == ecole_active_id)
        if hasattr(Eleve, "deleted_at"):
            eleves_query = eleves_query.filter(Eleve.deleted_at.is_(None))
        
        if classes_ids:
            eleves_query = eleves_query.filter(Eleve.classe_id.in_(classes_ids))
        else:
            # Si aucune classe n'appartient à ce cycle, on force un résultat vide
            eleves_query = eleves_query.filter(Eleve.id == -1)
            
        eleves = eleves_query.all()

        total_attendu = 0.0
        total_recouvre = 0.0
        data = []

        for eleve in eleves:
            classe = classes_dict.get(eleve.classe_id) if eleve.classe_id else None

            frais_scol = float(getattr(classe, "frais_scolarite", 0.0) or 0.0)
            frais_inscr = float(getattr(classe, "frais_inscription", 0.0) or 0.0)
            frais_coges = float(getattr(classe, "frais_coges", 0.0) or 0.0)

            frais_brut_total = (
                (frais_scol + frais_inscr + frais_coges)
                if (frais_scol + frais_inscr + frais_coges) > 0
                else 65000.0
            )
            reduction = float(getattr(eleve, "montant_reduction", 0.0) or 0.0)
            total_du_net = max(0.0, frais_brut_total - reduction)

            paiements_eleve = (
                db.query(Paiement)
                .filter(
                    Paiement.eleve_id == eleve.id,
                    Paiement.school_id == ecole_active_id,
                )
                .all()
            )
            montant_paye = (
                sum(
                    float(getattr(p, "montant_total", None) or getattr(p, "montant", 0.0))
                    for p in paiements_eleve
                )
                if paiements_eleve
                else 0.0
            )

            total_attendu += total_du_net
            total_recouvre += montant_paye
            solde_restant = max(0.0, total_du_net - montant_paye)

            classe_lib = (get_classe_libelle(classe)) if classe else "Non assignée"
            data.append({
                "Matricule": getattr(eleve, "matricule", "N/D"),
                "Élève": f"{getattr(eleve, 'nom', '')} {getattr(eleve, 'prenom', '')}".strip()
                or "Élève",
                "Classe": classe_lib,
                "Montant Dû (Net)": total_du_net,
                "Montant Payé": montant_paye,
                "Solde Restant": solde_restant,
                "Statut": "Soldé" if solde_restant <= 0 else "Débiteur",
            })

        reste_a_recouvrer = max(0.0, total_attendu - total_recouvre)
        taux = (
            (total_recouvre / total_attendu * 100) if total_attendu > 0 else 0.0
        )

        st.markdown(
            f"### Tableau de Bord Financier — **{school_name} ({cycle_en_cours})**"
        )

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(
                "Chiffre d'Affaires Attendu (Net)", f"{total_attendu:,.0f} FCFA"
            )
        with col2:
            st.metric(
                "Total Global Recouvré",
                f"{total_recouvre:,.0f} FCFA",
                delta=f"{taux:.1f}% de réalisation",
            )
        with col3:
            st.metric(
                "Créances (Reste à Recouvrer)", f"{reste_a_recouvrer:,.0f} FCFA"
            )

        st.markdown("---")

        # Options de filtrage avancées & Export
        col_f1, col_f2 = st.columns([2, 2])
        with col_f1:
            filtre_statut = st.selectbox(
                "🔍 Filtrer l'affichage par statut financier",
                ["Tous les élèves", "Uniquement les débiteurs (Impayés)", "Soldés"],
            )
        with col_f2:
            st.markdown(
                "<div style='margin-top: 28px;'></div>", unsafe_allow_html=True
            )

        if not data:
            st.info(
                f"📌 Aucune donnée financière ou élève enregistré pour le cycle"
                f" **{cycle_en_cours}** dans l'établissement **{school_name}**."
            )
        else:
            df = pd.DataFrame(data)

            if filtre_statut == "Uniquement les débiteurs (Impayés)":
                df_affiche = df[df["Solde Restant"] > 0]
            elif filtre_statut == "Soldés":
                df_affiche = df[df["Solde Restant"] <= 0]
            else:
                df_affiche = df

            st.markdown(
                f"#### Visualisation et Suivi — **{cycle_en_cours}**"
                f" ({len(df_affiche)} enregistrements)"
            )
            st.dataframe(df_affiche, use_container_width=True)

            # Section Export des rapports financiers (Norme professionnelle)
            st.markdown("##### 📥 Exportation des Rapports Financiers")
            col_e1, col_e2 = st.columns(2)

            with col_e1:
                csv_data = df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="📊 Télécharger le rapport CSV",
                    data=csv_data,
                    file_name=(
                        f"Rapport_Financier_{school_name}_{cycle_en_cours}.csv"
                    ),
                    mime="text/csv",
                )

            with col_e2:
                output_excel = io.BytesIO()
                with pd.ExcelWriter(output_excel, engine="openpyxl") as writer:
                    df.to_excel(writer, index=False, sheet_name="Recouvrement")
                excel_bytes = output_excel.getvalue()
                st.download_button(
                    label="📈 Télécharger le rapport Excel (.xlsx)",
                    data=excel_bytes,
                    file_name=(
                        f"Rapport_Financier_{school_name}_{cycle_en_cours}.xlsx"
                    ),
                    mime=(
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    ),
                )

        # Traçabilité d'audit de consultation des statistiques
        db.add(
            ActivityLog(
                school_id=ecole_active_id,
                timestamp=datetime.utcnow(),
                username=username_connecte,
                action=(
                    f"Consultation des statistiques financières ({cycle_en_cours})"
                ),
                module="Stats Encaissements",
                statut="Succès",
            )
        )
        db.commit()

    finally:
        db.close()


# Alias de compatibilité exhaustive
afficher_stats_encaissements = afficher_stats_encaissements
afficher_statistiques_encaissements = afficher_stats_encaissements
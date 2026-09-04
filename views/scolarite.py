import streamlit as st
import pandas as pd
from datetime import datetime
from database.db_config import SessionLocal
from database.models import Eleve, Classe, Paiement
from database.audit import log_action_erp

def afficher_encaissement(niveau_actif="Collège"):
    st.subheader("💰 Gestion des Encaissements & Quittances")
    st.markdown("Enregistrement des versements scolaires avec ventilation multi-rubriques et saisie manuelle des reçus.")
    st.markdown("---")

    school_id = st.session_state.get("school_id")
    if not school_id:
        st.warning("⚠️ Veuillez vous connecter pour accéder à cette section.")
        return

    db = SessionLocal()
    try:
        classes = db.query(Classe).filter(
            Classe.school_id == school_id,
            Classe.cycle == niveau_actif,
            Classe.deleted_at.is_(None)
        ).all()

        if not classes:
            st.warning(f"Aucune classe trouvée pour le cycle {niveau_actif}.")
            return

        options_classes = {c.libelle: c.id for c in classes}
        choix_classe = st.selectbox("Sélectionner la classe", list(options_classes.keys()))
        
        classe_id_sel = options_classes[choix_classe]
        eleves = db.query(Eleve).filter(
            Eleve.school_id == school_id,
            Eleve.classe_id == classe_id_sel,
            Eleve.deleted_at.is_(None)
        ).all()

        if not eleves:
            st.info("Aucun élève inscrit dans cette classe.")
            return

        options_eleves = {f"{e.nom} {e.prenom} (Matricule: {e.matricule})": e.id for e in eleves}
        choix_eleve_str = st.selectbox("Sélectionner l'élève", list(options_eleves.keys()))
        eleve_id_sel = options_eleves[choix_eleve_str]

        eleve_actif = db.query(Eleve).filter(Eleve.id == eleve_id_sel).first()

        st.info(f"Élève sélectionné : **{eleve_actif.nom} {eleve_actif.prenom}** (Classe : {choix_classe})")

        with st.form("form_encaissement_multiple"):
            st.markdown("#### 📝 Ventilation du Versement Global")
            
            # Saisie manuelle de la référence du reçu en premier
            ref_recu = st.text_input("Référence du Reçu / N° de Quittance (Requis)")

            col_r1, col_r2 = st.columns(2)
            
            with col_r1:
                payer_scolarite = st.checkbox("Scolarité", value=True)
                montant_scolarite = st.number_input("Montant Scolarité (FCFA)", min_value=0.0, value=0.0, step=5000.0)

                payer_inscription = st.checkbox("Inscription")
                montant_inscription = st.number_input("Montant Inscription (FCFA)", min_value=0.0, value=0.0, step=1000.0)

                payer_coges = st.checkbox("COGES")
                montant_coges = st.number_input("Montant COGES (FCFA)", min_value=0.0, value=0.0, step=500.0)

            with col_r2:
                payer_cantine = st.checkbox("Cantine")
                montant_cantine = st.number_input("Montant Cantine (FCFA)", min_value=0.0, value=0.0, step=1000.0)

                payer_transport = st.checkbox("Transport")
                montant_transport = st.number_input("Montant Transport (FCFA)", min_value=0.0, value=0.0, step=1000.0)

                mode_reglement = st.selectbox("Mode de règlement", ["Espèces", "Orange Money / Moov Money", "Virement Bancaire", "Chèque"])
                nom_payeur = st.text_input("Nom du payeur (Parent / Tuteur)", value=eleve_actif.tuteur or "")

            total_versement = (
                (montant_scolarite if payer_scolarite else 0) +
                (montant_inscription if payer_inscription else 0) +
                (montant_coges if payer_coges else 0) +
                (montant_cantine if payer_cantine else 0) +
                (montant_transport if payer_transport else 0)
            )

            st.markdown(f"### 💵 Montant Total Perçu : **{total_versement:,.0f} FCFA**")

            submitted = st.form_submit_button("Valider l'encaissement global et éditer la quittance", type="primary")
            if submitted:
                if not ref_recu.strip():
                    st.error("Veuillez saisir la référence ou le numéro du reçu.")
                elif total_versement <= 0:
                    st.error("Le montant total du versement doit être supérieur à zéro.")
                else:
                    # Vérifier si la référence existe déjà pour cette école
                    existant = db.query(Paiement).filter(
                        Paiement.school_id == school_id,
                        Paiement.reference_recu == ref_recu.strip()
                    ).first()

                    if existant:
                        st.error(f"Erreur : La référence de reçu '{ref_recu}' existe déjà.")
                    else:
                        motifs_concernes = []
                        if payer_scolarite and montant_scolarite > 0:
                            motifs_concernes.append(f"Scolarité: {montant_scolarite}F")
                        if payer_inscription and montant_inscription > 0:
                            motifs_concernes.append(f"Inscription: {montant_inscription}F")
                        if payer_coges and montant_coges > 0:
                            motifs_concernes.append(f"COGES: {montant_coges}F")
                        if payer_cantine and montant_cantine > 0:
                            motifs_concernes.append(f"Cantine: {montant_cantine}F")
                        if payer_transport and montant_transport > 0:
                            motifs_concernes.append(f"Transport: {montant_transport}F")

                        motif_global = " | ".join(motifs_concernes) if motifs_concernes else "Versement global"

                        nouveau_paiement = Paiement(
                            school_id=school_id,
                            reference_recu=ref_recu.strip(),
                            eleve_id=eleve_id_sel,
                            montant=total_versement,
                            mode_reglement=mode_reglement,
                            motif=motif_global,
                            nom_payeur=nom_payeur,
                            agent_caisse=st.session_state.get("username", "admin"),
                            date_paiement=datetime.now()
                        )
                        db.add(nouveau_paiement)
                        
                        # Traçabilité médico-légale de l'encaissement (Normes ERP - SOC 2 / ISO 27001)
                        log_action_erp(
                            module="Encaissement",
                            action=f"Enregristrement du versement de {total_versement:,.0f} FCFA pour l'élève {eleve_actif.nom} {eleve_actif.prenom} (Reçu N° {ref_recu.strip()})",
                            statut="Critique",
                            valeur_avant="Aucun versement",
                            valeur_apres=f"{total_versement:,.0f} FCFA ({mode_reglement})"
                        )

                        db.commit()

                        st.success(f"Encaissement de **{total_versement:,.0f} FCFA** validé avec succès ! Reçu N° : **{ref_recu}**")
                        st.balloons()
    finally:
        db.close()

# Alias de compatibilité
afficher_encaissement = afficher_encaissement
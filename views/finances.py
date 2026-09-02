import streamlit as st
import pandas as pd
from datetime import datetime
from database.db_config import SessionLocal
from database.models import Paiement, Eleve, School, ActivityLog

def afficher_encaissement():
    st.subheader("💳 Encaissement & Quittance")
    st.markdown("Perception unifiée, clôture journalière, suivi des versements et édition de quittances officielles avec isolation multi-tenant stricte.")
    st.markdown("---")

    school_id = st.session_state.get("school_id")
    is_super_admin = st.session_state.get("is_super_admin", False)
    cycle_en_cours = st.session_state.get("cycle_actif", "Collège")

    if not school_id and not is_super_admin:
        st.warning("⚠️ Veuillez vous connecter pour accéder à cette section.")
        return

    db = SessionLocal()
    try:
        if school_id:
            ecole_courante = db.query(School).filter(School.id == school_id).first()
            school_name = ecole_courante.nom if ecole_courante else st.session_state.get("school_name", "Établissement")
        else:
            school_name = st.session_state.get("school_name", "Établissement")

        # Récupération des élèves de l'école active
        query_eleves = db.query(Eleve)
        if not is_super_admin and school_id:
            query_eleves = query_eleves.filter(Eleve.school_id == school_id)
        eleves = query_eleves.all()

        tab_saisie, tab_historique = st.tabs(["➕ Nouvel Encaissement", "📊 Suivi & Historique Financier"])

        with tab_saisie:
            st.markdown(f"### Saisie d'un Encaissement — **{school_name} ({cycle_en_cours})**")
            
            if not eleves:
                st.info("⚠️ Aucun élève enregistré dans cet établissement. Veuillez d'abord en ajouter.")
            else:
                options_eleves = {f"{e.nom} {e.prenom} (Mat: {e.matricule})": e.id for e in eleves}
                
                with st.form("form_nouveau_paiement"):
                    col1, col2 = st.columns(2)
                    with col1:
                        eleve_selectionne_label = st.selectbox("Sélectionner l'élève", list(options_eleves.keys()))
                        montant_paye = st.number_input("Montant versé (FCFA)", min_value=0.0, step=500.0, value=10000.0)
                        motif_paiement = st.selectbox("Motif du versement", [
                            "Frais de scolarité - 1ère Tranche",
                            "Frais de scolarité - 2ème Tranche",
                            "Frais de scolarité - 3ème Tranche",
                            "Frais d'inscription / Réinscription",
                            "Frais de tenues / Uniformes",
                            "Frais d'examen / Concourses",
                            "Autres frais scolaires"
                        ])
                    with col2:
                        mode_reglement = st.selectbox("Mode de règlement", ["Espèces", "Orange Money Niger", "Moov Money Niger", "Virement Bancaire", "Chèque"])
                        agent_caisse = st.text_input("Nom du caissier / Agent", value=st.session_state.get("username", "admin"))
                        date_versement = st.date_input("Date du versement", value=datetime.now())

                    submitted_paiement = st.form_submit_button("💾 Encaisser et générer la quittance")
                    if submitted_paiement:
                        if montant_paye <= 0:
                            st.error("⚠️ Le montant du versement doit être supérieur à zéro.")
                        else:
                            eleve_id = options_eleves[eleve_selectionne_label]
                            ref_recu = f"REC-{datetime.now().strftime('%Y%m%d')}-{abs(hash(str(datetime.now()) + str(eleve_id))) % 10000:04d}"
                            
                            target_school_id = school_id or 1
                            nouveau_paiement = Paiement(
                                school_id=target_school_id,
                                eleve_id=eleve_id,
                                montant=montant_paye,
                                motif=motif_paiement,
                                mode_reglement=mode_reglement,
                                reference_recu=ref_recu,
                                agent_caisse=agent_caisse,
                                date_paiement=datetime.combine(date_versement, datetime.now().time())
                            )
                            db.add(nouveau_paiement)
                            
                            db.add(ActivityLog(
                                school_id=target_school_id,
                                timestamp=datetime.utcnow(),
                                username=st.session_state.get("username", "admin"),
                                action=f"Encaissement de {montant_paye:,.0f} FCFA ({ref_recu})",
                                module="Encaissement",
                                statut="Succès"
                            ))
                            db.commit()
                            st.success(f"✅ Encaissement validé avec succès ! Référence de quittance : **{ref_recu}**")

        with tab_historique:
            query_paiements = db.query(Paiement)
            if not is_super_admin and school_id:
                query_paiements = query_paiements.filter(Paiement.school_id == school_id)
            paiements = query_paiements.all()

            total_recettes = sum(p.montant for p in paiements) if paiements else 0.0
            total_attendu = len(eleves) * 65000  # Base forfaitaire annuelle par élève
            solde_restant = max(0.0, total_attendu - total_recettes)
            taux_recouvrement = (total_recettes / total_attendu * 100) if total_attendu > 0 else 0.0

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("💵 Total Encaissé", f"{total_recettes:,.0f} FCFA", delta="Recettes")
            with col2:
                st.metric("📊 Objectif Prévisionnel", f"{total_attendu:,.0f} FCFA", delta="Attendu")
            with col3:
                st.metric("📉 Reste à Recouvrer", f"{solde_restant:,.0f} FCFA", delta=f"{taux_recouvrement:.1f}% recouvré")

            st.markdown("---")
            st.markdown("### 📋 Historique Détaillé des Encaissements")

            if not paiements:
                st.info("Aucun encaissement enregistré pour le moment.")
            else:
                data = []
                for p in paiements:
                    eleve = db.query(Eleve).filter(Eleve.id == p.eleve_id).first()
                    nom_eleve = f"{eleve.nom} {eleve.prenom}" if eleve else "Élève inconnu"
                    matricule = eleve.matricule if eleve else "N/D"
                    
                    data.append({
                        "Référence": p.reference_recu,
                        "Date": p.date_paiement.strftime("%d/%m/%Y %H:%M") if p.date_paiement else "N/D",
                        "Matricule": matricule,
                        "Élève": nom_eleve,
                        "Montant (FCFA)": f"{p.montant:,.0f}",
                        "Motif": p.motif,
                        "Mode": p.mode_reglement,
                        "Caissier(e)": p.agent_caisse or "N/D"
                    })
                df_finances = pd.DataFrame(data)
                st.dataframe(df_finances, use_container_width=True)

    finally:
        db.close()

# Alias de compatibilité exhaustive pour le routeur app.py
afficher_encaissement = afficher_encaissement
afficher_finances = afficher_encaissement
afficher_encaissements = afficher_encaissement
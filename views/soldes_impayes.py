import streamlit as st
from database.db_config import SessionLocal
from database.models import Eleve, Classe, Paiement

def afficher_soldes_impayes(niveau_actif="Collège"):
    st.subheader("📊 Soldes & Suivi des Impayés")
    st.markdown("Suivi des encaissements, des réductions et des soldes restants par élève.")
    st.markdown("---")

    school_id = st.session_state.get("school_id")
    if not school_id:
        st.warning("⚠️ Veuillez vous connecter pour accéder à cette section.")
        return

    db = SessionLocal()
    try:
        classes = db.query(Classe).filter(
            Classe.school_id == school_id,
            Classe.cycle == niveau_actif
        ).all()

        if not classes:
            st.warning(f"Aucune classe trouvée pour le cycle {niveau_actif}.")
            return

        options_classes = {c.libelle: c.id for c in classes}
        choix_classe = st.selectbox("Filtrer par classe", list(options_classes.keys()), key="select_classe_solde")
        
        classe_id_sel = options_classes[choix_classe]
        classe_obj = db.query(Classe).filter(Classe.id == classe_id_sel).first()
        
        eleves = db.query(Eleve).filter(
            Eleve.school_id == school_id,
            Eleve.classe_id == classe_id_sel
        ).all()

        if not eleves:
            st.info("Aucun élève dans cette classe.")
            return

        # Frais de base de la classe + COGES
        frais_scolarite_base = float(classe_obj.frais_scolarite or 0.0)
        frais_coges = float(getattr(classe_obj, 'frais_coges', 0.0) or 0.0)
        total_brut_classe = frais_scolarite_base + frais_coges

        cols = st.columns([2, 1.5, 1.5, 1.5, 1.5, 2])
        cols[0].markdown("**Élève**")
        cols[1].markdown("**Montant Brut**")
        cols[2].markdown("**Réduction**")
        cols[3].markdown("**Net à Payer**")
        cols[4].markdown("**Total Versé**")
        cols[5].markdown("**Solde Restant**")
        for i in range(6):
            cols[i].markdown("---")

        for e in eleves:
            reduction = float(e.montant_reduction or 0.0)
            
            # Calcul du Net à Payer (Montant Brut - Réduction, plancher à 0)
            net_a_payer = max(0.0, total_brut_classe - reduction)

            # Total des versements de l'élève
            paiements_eleve = db.query(Paiement).filter(
                Paiement.school_id == school_id,
                Paiement.eleve_id == e.id
            ).all()
            
            total_verse = sum([float(p.montant) for p in paiements_eleve])
            
            # Le solde restant se base sur le Net à Payer et non sur le brut !
            solde_restant = net_a_payer - total_verse

            c = st.columns([2, 1.5, 1.5, 1.5, 1.5, 2])
            c[0].write(f"{e.nom} {e.prenom} ({e.matricule})")
            c[1].write(f"{total_brut_classe:,.0f} F")
            c[2].write(f"-{reduction:,.0f} F" if reduction > 0 else "0 F")
            c[3].write(f"{net_a_payer:,.0f} F")
            c[4].write(f"{total_verse:,.0f} F")
            
            if solde_restant > 0:
                c[5].markdown(f"<span style='color: red; font-weight: bold;'>{solde_restant:,.0f} F (Impayé)</span>", unsafe_allow_html=True)
            elif solde_restant < 0:
                c[5].markdown(f"<span style='color: orange; font-weight: bold;'>{abs(solde_restant):,.0f} F (Trop-perçu)</span>", unsafe_allow_html=True)
            else:
                c[5].markdown("<span style='color: green; font-weight: bold;'>Soldé (0 F)</span>", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### 🛠️ Gestion & Annulation des Versements Erronés")
        
        options_eleves_tous = {f"{elev.nom} {elev.prenom} ({elev.matricule})": elev.id for elev in eleves}
        eleve_a_gerer_str = st.selectbox("Sélectionner un élève pour auditer ou annuler ses reçus", list(options_eleves_tous.keys()))
        eleve_gerer_id = options_eleves_tous[eleve_a_gerer_str]

        historique_paiements = db.query(Paiement).filter(
            Paiement.school_id == school_id,
            Paiement.eleve_id == eleve_gerer_id
        ).all()

        if not historique_paiements:
            st.info("Aucun versement enregistré pour cet élève.")
        else:
            for p in historique_paiements:
                col_p1, col_p2, col_p3, col_p4 = st.columns([2, 2, 2, 1])
                col_p1.write(f"**Reçu :** {p.reference_recu}")
                col_p2.write(f"**Montant :** {p.montant:,.0f} F")
                col_p3.write(f"**Motif :** {p.motif}")
                
                with col_p4:
                    if st.button("🗑️ Annuler", key=f"del_paiement_{p.id}", help="Supprimer ce reçu erroné"):
                        db.delete(p)
                        db.commit()
                        st.success(f"Le reçu {p.reference_recu} a été supprimé avec succès !")
                        st.rerun()
                st.markdown("<hr style='margin: 0.1rem 0; border-color: rgba(255,255,255,0.05);'>", unsafe_allow_html=True)

    finally:
        db.close()

# Alias de compatibilité
afficher_soldes_impayes = afficher_soldes_impayes
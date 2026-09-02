import streamlit as st
import pandas as pd
from database.db_config import SessionLocal
from database.models import Classe, Eleve, School

def afficher_encaissement():
    st.subheader("💳 Encaissement & Quittance")
    st.markdown("Perception unifiée, clôture journalière, suivi des versements et édition de quittances officielles.")
    st.markdown("---")

    school_id = st.session_state.get("school_id")
    is_super_admin = st.session_state.get("is_super_admin", False)
    school_name = st.session_state.get("school_name", "Établissement")
    
    # Récupération automatique du cycle actif depuis le menu latéral gauche
    cycle_en_cours = st.session_state.get("cycle_actif", "Collège")

    if not school_id and not is_super_admin:
        st.warning("⚠️ Veuillez vous connecter pour accéder à cette section.")
        return

    db = SessionLocal()
    try:
        st.markdown(f"### Encaissements — **{school_name} ({cycle_en_cours})**")

        # 1. Isolation multi-écoles et multi-cycles pour les classes
        classes_query = db.query(Classe).filter(Classe.cycle == cycle_en_cours)
        if not is_super_admin and school_id:
            classes_query = classes_query.filter(Classe.school_id == school_id)
        
        classes_cycle = classes_query.all()

        if not classes_cycle:
            st.info(f"📌 Aucune classe disponible pour le cycle **{cycle_en_cours}** dans cet établissement. Veuillez d'abord en créer dans le menu 'Classes & Tarifs'.")
            return

        noms_classes = [c.libelle for c in classes_cycle]
        classe_selectionnee = st.selectbox("Sélectionner la classe", noms_classes)

        classe_obj = next((c for c in classes_cycle if c.libelle == classe_selectionnee), None)

        if classe_obj:
            # 2. Récupérer les élèves de cette classe spécifique pour l'encaissement
            eleves_query = db.query(Eleve).filter(Eleve.classe_id == classe_obj.id)
            if not is_super_admin and school_id:
                eleves_query = eleves_query.filter(Eleve.school_id == school_id)
            eleves = eleves_query.all()

            if not eleves:
                st.warning(f"⚠️ Aucun élève inscrit dans la classe {classe_selectionnee}.")
            else:
                noms_eleves = [f"{e.nom} {e.prenom}" for e in eleves]
                eleve_choisi = st.selectbox("Sélectionner l'élève", noms_eleves)

                eleve_obj = next((e for e in eleves if f"{e.nom} {e.prenom}" == eleve_choisi), None)

                if eleve_obj:
                    st.info(f"Élève sélectionné : **{eleve_obj.nom} {eleve_obj.prenom}** (Classe : {classe_obj.libelle})")
                    
                    with st.form("form_encaissement"):
                        montant_verse = st.number_input("Montant à verser (FCFA)", min_value=0.0, step=1000.0)
                        motif = st.selectbox("Motif du versement", ["Scolarité", "Inscription", "Transport", "Cantine", "COGES"])
                        
                        submitted = st.form_submit_button("Valider l'encaissement et éditer la quittance")
                        if submitted:
                            if montant_verse <= 0:
                                st.error("⚠️ Veuillez entrer un montant valide.")
                            else:
                                # Mise à jour du montant payé de l'élève
                                actuel_paye = getattr(eleve_obj, 'montant_paye', 0.0) or 0.0
                                eleve_obj.montant_paye = actuel_paye + montant_verse
                                db.commit()
                                st.success(f"✅ Encaissement de {montant_verse:,.0f} FCFA validé avec succès pour {eleve_obj.nom} !")
                                st.rerun()

    finally:
        db.close()
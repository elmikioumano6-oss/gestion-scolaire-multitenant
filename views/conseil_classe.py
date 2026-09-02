import streamlit as st
import pandas as pd
from datetime import datetime
from database.db_config import SessionLocal
from database.models import Classe, Eleve, School, ActivityLog

def afficher_conseil_classe():
    st.subheader("🏆 Conseil de Classe")
    st.markdown("Synthèse des résultats, délibérations et appréciations par classe et par cycle avec isolation multi-tenant stricte.")
    st.markdown("---")

    school_id = st.session_state.get("school_id")
    is_super_admin = st.session_state.get("is_super_admin", False)
    
    db = SessionLocal()
    try:
        if school_id:
            ecole_courante = db.query(School).filter(School.id == school_id).first()
            school_name = ecole_courante.nom if ecole_courante else st.session_state.get("school_name", "Établissement")
        else:
            school_name = st.session_state.get("school_name", "Établissement")
    finally:
        db.close()

    cycle_en_cours = st.session_state.get("cycle_actif", "Collège")

    if not school_id and not is_super_admin:
        st.warning("⚠️ Veuillez vous connecter pour accéder à cette section.")
        return

    db = SessionLocal()
    try:
        classes_query = db.query(Classe).filter(Classe.cycle == cycle_en_cours)
        if not is_super_admin and school_id:
            classes_query = classes_query.filter(Classe.school_id == school_id)
        classes_cycle = classes_query.all()

        st.markdown(f"### Conseil de Classe — **{school_name} ({cycle_en_cours})**")

        if not classes_cycle:
            st.warning(f"⚠️ Aucune classe n'est actuellement configurée pour le cycle **{cycle_en_cours}** dans l'établissement **{school_name}**.")
            st.info("Veuillez d'abord enregistrer vos classes dans le module **Classes & Tarifs** du menu latéral.")
            return

        noms_classes = [c.libelle for c in classes_cycle]
        classe_choisie = st.selectbox("Sélectionner la classe pour les délibérations", noms_classes)

        classe_obj = next((c for c in classes_cycle if c.libelle == classe_choisie), None)
        if classe_obj:
            eleves_query = db.query(Eleve).filter(Eleve.classe_id == classe_obj.id)
            if not is_super_admin and school_id:
                eleves_query = eleves_query.filter(Eleve.school_id == school_id)
            eleves = eleves_query.all()

            if not eleves:
                st.info(f"Aucun élève enregistré dans la classe **{classe_choisie}**.")
            else:
                st.success(f"Délibérations en cours pour la classe de **{classe_choisie}** ({len(eleves)} élèves).")
                
                notes_store = st.session_state.get("notes_evaluation_data", {})

                synthese_data = []
                for e in eleves:
                    notes_eleve = []
                    for key, evaluations in notes_store.items():
                        if f"_{classe_choisie}_" in key or str(school_id) in key:
                            if e.id in evaluations:
                                notes_eleve.append(evaluations[e.id])

                    moyenne = round(sum(notes_eleve) / len(notes_eleve), 2) if notes_eleve else 0.0
                    decision = "Admis(e)" if moyenne >= 10 else "Ajourné(e)" if moyenne > 0 else "En attente"

                    synthese_data.append({
                        "id": e.id,
                        "Nom & Prénom": f"{e.nom} {e.prenom}",
                        "Matricule": getattr(e, 'matricule', 'N/D'),
                        "Moyenne Générale": moyenne,
                        "Décision du Conseil": decision
                    })

                synthese_data.sort(key=lambda x: x["Moyenne Générale"], reverse=True)
                
                for rang, item in enumerate(synthese_data, start=1):
                    item["Rang"] = rang if item["Moyenne Générale"] > 0 else "—"

                df_synthese = pd.DataFrame(synthese_data)[["Rang", "Nom & Prénom", "Matricule", "Moyenne Générale", "Décision du Conseil"]]
                st.dataframe(df_synthese, use_container_width=True)

                if st.button("⚖️ Valider et Clôturer les Délibérations du Conseil"):
                    target_school_id = school_id or 1
                    
                    nouveau_log = ActivityLog(
                        school_id=target_school_id,
                        timestamp=datetime.utcnow(),
                        username=st.session_state.get("username", "admin"),
                        action=f"Clôture des délibérations du Conseil de Classe - {classe_choisie}",
                        module="Conseil de classe",
                        statut="Validé"
                    )
                    db.add(nouveau_log)
                    db.commit()
                    
                    st.success(f"✅ Le conseil de classe pour la classe de **{classe_choisie}** a été clôturé et validé avec succès !")

    finally:
        db.close()

# Alias de compatibilité exhaustive pour éviter toute erreur d'importation du routeur
afficher_conseil_de_classe = afficher_conseil_classe
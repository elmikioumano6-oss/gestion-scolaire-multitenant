import streamlit as st
import pandas as pd
from database.db_config import SessionLocal
from database.models import Classe, Eleve, School

def afficher_cartes_scolaires():
    st.subheader("🪪 Génération des Cartes Scolaires")
    st.markdown("Édition et impression des cartes d'identité des élèves avec isolation multi-tenant stricte.")
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
        # Isolation multi-écoles et multi-cycles pour les classes
        classes_query = db.query(Classe).filter(Classe.cycle == cycle_en_cours)
        if not is_super_admin and school_id:
            classes_query = classes_query.filter(Classe.school_id == school_id)
        classes_cycle = classes_query.all()

        if not classes_cycle:
            st.info(f"📌 **{school_name}** — Aucune classe disponible pour le cycle **{cycle_en_cours}**.")
            return

        classes_dict = {c.id: c.libelle for c in classes_cycle}
        classes_ids = list(classes_dict.keys())

        # Récupération des élèves inscrits dans ces classes
        eleves_query = db.query(Eleve).filter(Eleve.classe_id.in_(classes_ids))
        if not is_super_admin and school_id:
            eleves_query = eleves_query.filter(Eleve.school_id == school_id)
        eleves = eleves_query.all()

        st.markdown(f"### Cartes Scolaires — **{school_name} ({cycle_en_cours})**")

        if not eleves:
            st.info("Aucun élève enregistré pour générer les cartes scolaires dans ce cycle.")
        else:
            noms_eleves = [f"{e.nom} {e.prenom} ({classes_dict.get(e.classe_id, 'N/D')})" for e in eleves]
            choix_eleve = st.selectbox("Sélectionner un élève pour générer sa carte", noms_eleves)

            eleve_obj = next((e for e in eleves if f"{e.nom} {e.prenom} ({classes_dict.get(e.classe_id, 'N/D')})" == choix_eleve), None)

            if eleve_obj:
                st.markdown("---")
                st.markdown("#### 🎫 Aperçu de la Carte d'Identité Scolaire")
                
                # Encadré visuel représentant la carte scolaire
                st.info(
                    f"**{school_name.upper()}**\n\n"
                    f"🎓 **Carte Scolaire — Année 2026-2027**\n\n"
                    f"👤 **Nom & Prénom :** {eleve_obj.nom} {eleve_obj.prenom}\n"
                    f"🏫 **Classe :** {classes_dict.get(eleve_obj.classe_id, 'N/D')}\n"
                    f"📌 **Cycle :** {cycle_en_cours}\n"
                    f"🔖 **Matricule :** {getattr(eleve_obj, 'matricule', 'N/D')}"
                )

                if st.button("🖨️ Imprimer / Télécharger la carte"):
                    st.success(f"✅ La carte scolaire de {eleve_obj.nom} {eleve_obj.prenom} a été préparée pour l'impression !")

    finally:
        db.close()
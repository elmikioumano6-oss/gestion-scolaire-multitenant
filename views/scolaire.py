import streamlit as st
import pandas as pd
from database.db_config import SessionLocal
from database.models import Eleve, Classe

# La fonction reçoit désormais le "niveau_actif" (Primaire, Collège, Lycée) envoyé par main.py
def afficher_scolarite(niveau_actif):
    st.subheader(f"🎓 Gestion des Élèves - {niveau_actif}")
    db = SessionLocal()

    # 1. On récupère UNIQUEMENT les classes du niveau sélectionné en haut de l'écran
    classes_du_niveau = db.query(Classe).filter(Classe.cycle == niveau_actif).all()

    # Sécurité : on empêche d'inscrire un élève si aucune classe n'existe pour ce cycle
    if not classes_du_niveau:
        st.warning(f"⚠️ Aucune classe n'est configurée pour le {niveau_actif}. Veuillez d'abord créer une classe dans le module 'Classes'.")
        db.close()
        return

    # --- FORMULAIRE D'AJOUT ---
    with st.form("form_ajout_eleve", clear_on_submit=True):
        st.markdown(f"### Inscrire un nouvel élève au {niveau_actif}")
        
        col1, col2 = st.columns(2)
        with col1:
            nom = st.text_input("Nom de l'élève *")
            prenom = st.text_input("Prénom(s) *")
            matricule = st.text_input("Matricule * (ex: E001-2026)")
        with col2:
            sexe = st.selectbox("Sexe", ["Garçon", "Fille"])
            contact_parent = st.text_input("Contact du Parent (ex: 90123456)")
            
            # Le menu déroulant ne propose QUE les classes du niveau actif !
            noms_classes = [c.nom for c in classes_du_niveau]
            classe_choisie = st.selectbox("Classe *", noms_classes)

        submit = st.form_submit_button("Enregistrer l'élève", type="primary")

        if submit:
            if nom.strip() and prenom.strip() and matricule.strip():
                # Vérifier si le matricule est déjà utilisé dans toute l'école
                existe = db.query(Eleve).filter(Eleve.matricule == matricule.strip()).first()
                if existe:
                    st.error(f"❌ Le matricule {matricule} est déjà utilisé par un autre élève !")
                else:
                    # Retrouver l'ID de la classe choisie pour l'affecter à l'élève
                    classe_id = next(c.id for c in classes_du_niveau if c.nom == classe_choisie)
                    
                    nouvel_eleve = Eleve(
                        nom=nom.strip().upper(),  # Met le nom en majuscules proprement
                        prenom=prenom.strip().title(), # Met la 1ère lettre du prénom en majuscule
                        matricule=matricule.strip(),
                        sexe=sexe,
                        contact_parent=contact_parent.strip(),
                        classe_id=classe_id
                    )
                    db.add(nouvel_eleve)
                    db.commit()
                    st.success(f"✅ Élève {nom} {prenom} inscrit avec succès en {classe_choisie} !")
                    st.rerun()
            else:
                st.error("⚠️ Veuillez remplir tous les champs obligatoires (*).")

    st.markdown("---")

    # --- AFFICHAGE FILTRÉ DES ÉLÈVES ---
    st.markdown(f"### Liste des élèves du {niveau_actif}")
    
    # LE FILTRE MAGIQUE : On récupère uniquement les élèves dont la classe appartient au cycle choisi
    eleves = db.query(Eleve).join(Classe).filter(Classe.cycle == niveau_actif).all()

    if eleves:
        # Préparation des données pour faire un beau tableau interactif
        donnees = []
        for e in eleves:
            donnees.append({
                "Matricule": e.matricule,
                "Nom": e.nom,
                "Prénom": e.prenom,
                "Sexe": getattr(e, 'sexe', 'N/A'),
                "Classe": e.classe.nom if e.classe else "N/A",
                "Contact Parent": getattr(e, 'contact_parent', 'Non renseigné')
            })
            
        df = pd.DataFrame(donnees)
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Option de suppression sécurisée
        with st.expander("🗑️ Supprimer un élève"):
            options = {f"{e.nom} {e.prenom} ({e.matricule})": e.id for e in eleves}
            a_supprimer = st.selectbox("Sélectionnez l'élève à supprimer :", options.keys())
            
            if st.button("Confirmer la suppression", type="primary"):
                eleve_a_suppr = db.query(Eleve).filter(Eleve.id == options[a_supprimer]).first()
                if eleve_a_suppr:
                    db.delete(eleve_a_suppr)
                    db.commit()
                    st.success("Élève supprimé avec succès !")
                    st.rerun()
    else:
        st.info(f"Aucun élève n'est encore inscrit au {niveau_actif}.")

    db.close()
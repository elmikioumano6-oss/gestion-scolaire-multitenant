from datetime import datetime
import urllib.parse
import pandas as pd
import streamlit as st
from database.db_config import SessionLocal
from database.models import Classe, Eleve, Note, Presence, Paiement


def generer_lien_whatsapp(telephone: str, nom_eleve: str, type_alerte: str, details: str) -> str:
    """Génère un lien URL WhatsApp pré-rempli et sécurisé."""
    telephone_propre = str(telephone).replace(" ", "").replace("+", "").replace("-", "")
    url_connexion = "https://www.gestionscolairepro.com"
    
    message = (
        f"🔔 *CSP RAHMAT-FH* - Alerte Scolaire\n\n"
        f"Chers Parents,\n"
        f"Nous vous informons qu'il y a du nouveau concernant votre enfant *{nom_eleve}* :\n\n"
        f"📌 *{type_alerte}* :\n{details}\n\n"
        f"🌐 Connectez-vous à votre *Espace Famille* : {url_connexion}\n\n"
        f"Cordialement,\n*La Direction du CSP RAHMAT-FH*"
    )
    
    return f"https://wa.me/{telephone_propre}?text={urllib.parse.quote(message)}"


def afficher_bloc_notifications(titre: str, donnees, type_alerte: str, db):
    """Affiche de manière générique les lignes de notifications pour optimiser le code."""
    if not donnees:
        st.info("Aucun élément récent trouvé pour cette sélection.")
        return

    for item in donnees:
        eleve = db.query(Eleve).filter(Eleve.id == item.eleve_id).first()
        if eleve and getattr(eleve, "tuteur", None):
            nom_complet = f"{eleve.nom} {eleve.prenom}"
            
            # Formatage spécifique selon le type d'élément
            if type_alerte == "Nouvelle note enregistrée":
                matiere_obj = getattr(item, "matiere", None)
                matiere_nom = getattr(matiere_obj, "libelle", "Matière") if matiere_obj else "Matière"
                valeur_note = getattr(item, "valeur", 0)
                type_eval = getattr(item, "type_evaluation", "Évaluation")
                sur_note = getattr(item, "sur", 20) or 20
                
                details = f"Matière : {matiere_nom} | Évaluation : {type_eval} | Note : {valeur_note} / {sur_note}"
                libelle_info = f"📝 {matiere_nom} : **{valeur_note}**"
            elif type_alerte == "Point d'assiduité":
                statut_pres = getattr(item, "statut", "Présent")
                date_pres = getattr(item, "date", datetime.now().strftime("%d/%m/%Y"))
                details = f"Statut : {statut_pres} | Date : {date_pres}"
                libelle_info = f"⚠️ {statut_pres}"
            else:  # Paiement
                montant_paye = getattr(item, "montant", 0)
                motif_paiement = getattr(item, "motif", "Scolarité") or "Scolarité"
                details = f"Montant versé : {montant_paye} FCFA | Motif : {motif_paiement}"
                libelle_info = f"💰 {montant_paye} FCFA"

            lien_wa = generer_lien_whatsapp(eleve.tuteur, nom_complet, type_alerte, details)

            col1, col2, col3 = st.columns([3, 3, 2])
            col1.write(f"🎓 **{nom_complet}**")
            col2.write(libelle_info)
            with col3:
                st.link_button("📲 Notifier", lien_wa, key=f"btn_{type_alerte[:3]}_{item.id}", type="primary")


def afficher_centre_notifications():
    st.subheader("📢 Centre de Notifications & Alertes WhatsApp")
    st.markdown("Filtrez par niveau et par classe pour envoyer en un clic les informations aux parents.")
    st.markdown("---")

    db = SessionLocal()
    try:
        # 1. Sélection du niveau / cycle
        cycles_disponibles = ["Maternelle", "Primaire", "Collège", "Lycée"]
        cycle_selectionne = st.selectbox("Filtrer par Cycle / Niveau", cycles_disponibles, key="notif_cycle")

        # 2. Récupérer les classes du cycle
        classes_cycle = db.query(Classe).filter(Classe.cycle == cycle_selectionne).all()
        
        if not classes_cycle:
            st.info(f"Aucune classe trouvée pour le cycle **{cycle_selectionne}**.")
            return

        dict_classes = {c.libelle or getattr(c, "nom", f"Classe {c.id}"): c.id for c in classes_cycle}
        classe_nom_choisi = st.selectbox("Sélectionner la Classe", list(dict_classes.keys()), key="notif_classe")
        classe_id_choisi = dict_classes[classe_nom_choisi]

        # 3. Récupérer les élèves de cette classe
        eleves_classe = db.query(Eleve).filter(
            Eleve.classe_id == classe_id_choisi,
            Eleve.deleted_at.is_(None)
        ).all()

        if not eleves_classe:
            st.warning("Aucun élève inscrit dans cette classe.")
            return

        eleves_ids = [e.id for e in eleves_classe]

        # 4. Onglets par type de notification
        tab_notes, tab_absences, tab_paiements = st.tabs([
            "📚 Notes de la classe",
            "📌 Assiduité (Absences/Retards)",
            "💳 Paiements de la classe"
        ])

        with tab_notes:
            st.markdown(f"#### Notes pour la classe de {classe_nom_choisi}")
            notes_classe = db.query(Note).filter(Note.eleve_id.in_(eleves_ids)).order_by(Note.id.desc()).all()
            afficher_bloc_notifications("Notes", notes_classe, "Nouvelle note enregistrée", db)

        with tab_absences:
            st.markdown(f"#### Assiduité pour la classe de {classe_nom_choisi}")
            absences_classe = db.query(Presence).filter(Presence.eleve_id.in_(eleves_ids)).order_by(Presence.id.desc()).all()
            afficher_bloc_notifications("Absences", absences_classe, "Point d'assiduité", db)

        with tab_paiements:
            st.markdown(f"#### Paiements pour la classe de {classe_nom_choisi}")
            paiements_classe = db.query(Paiement).filter(Paiement.eleve_id.in_(eleves_ids)).order_by(Paiement.id.desc()).all()
            afficher_bloc_notifications("Paiements", paiements_classe, "Confirmation de versement", db)

    except Exception as e:
        db.rollback()
        st.error(f"Une erreur est survenue lors du chargement des notifications : {e}")
    finally:
        db.close()


afficher_centre_notifications = afficher_centre_notifications
from datetime import datetime
from database.audit import log_action_erp
from database.db_config import SessionLocal
from database.models import (
    Classe,
    Eleve,
    EmploiDuTemps,
    Matiere,
    Note,
    Paiement,
    Presence,
    School,
    User,
    Message,
)
from database.queries import get_classes_cached, get_matieres_cached
import pandas as pd
import streamlit as st


def afficher_espace_parent():
  st.subheader("👨‍👩‍👧 Espace Famille & Suivi Élève")
  st.markdown(
      "Consultation sécurisée et auditée des notes, du cahier d'appel, de"
      " l'emploi du temps, de la situation financière et messagerie avec"
      " l'administration."
  )
  st.markdown("---")

  school_id = st.session_state.get("school_id")
  is_super_admin = st.session_state.get("is_super_admin", False)
  school_name = st.session_state.get("school_name", "Établissement")
  cycle_en_cours = st.session_state.get("cycle_actif", "Collège")
  username = st.session_state.get("username")
  user_role = st.session_state.get("role", "")

  if not school_id and not is_super_admin:
    st.warning("⚠️ Veuillez vous connecter pour accéder à cette section.")
    return

  db = SessionLocal()
  try:
    user_obj = (
        db.query(User).filter(User.username == username).first()
        if username
        else None
    )

    st.markdown(f"### Portail Parents — **{school_name} ({cycle_en_cours})**")

    classes_query = db.query(Classe).filter(Classe.cycle == cycle_en_cours)
    if not is_super_admin and school_id:
      classes_query = classes_query.filter(Classe.school_id == school_id)
    classes_cycle = classes_query.all()
    classes_ids = [c.id for c in classes_cycle]

    eleves_query = db.query(Eleve)

    if user_role and user_role.lower() == "parent" and user_obj:
      eleves_query = eleves_query.filter(
          (Eleve.parent_id == user_obj.id)
          | (Eleve.id == user_obj.eleve_id)
          | (Eleve.contact_parent == user_obj.username)
      )
    else:
      if not is_super_admin and school_id:
        eleves_query = eleves_query.filter(Eleve.school_id == school_id)
      if classes_ids:
        eleves_query = eleves_query.filter(Eleve.classe_id.in_(classes_ids))

    eleves = eleves_query.all()

    if not eleves:
      if user_role and user_role.lower() == "parent":
        st.warning(
            "⚠️ Aucun profil d'élève n'est actuellement rattaché à votre compte"
            " parent. Veuillez contacter l'administration."
        )
      else:
        st.info(
            f"📌 Aucun élève enregistré pour le cycle **{cycle_en_cours}** dans"
            " cet établissement."
        )
    else:
      noms_eleves = [
          f"{e.nom} {e.prenom} (Matricule: {e.matricule})" for e in eleves
      ]
      eleve_choisi = st.selectbox(
          "Sélectionner l'enfant à consulter", noms_eleves
      )

      eleve_obj = next(
          (
              e
              for e in eleves
              if f"{e.nom} {e.prenom} (Matricule: {e.matricule})"
              == eleve_choisi
          ),
          None,
      )

      if eleve_obj:
        classe = (
            db.query(Classe)
            .filter(Classe.id == eleve_obj.classe_id)
            .first()
            if eleve_obj.classe_id
            else None
        )
        classe_nom = (
            classe.libelle
            if classe and hasattr(classe, "libelle") and classe.libelle
            else getattr(classe, "nom", "Non assignée")
        )

        # --- TRACABILITÉ D'AUDIT DE LA CONSULTATION (NORMES SOC 2 / ISO 27001) ---
        if "last_consulted_eleve" not in st.session_state or (
            st.session_state.get("last_consulted_eleve") != eleve_obj.id
        ):
          st.session_state["last_consulted_eleve"] = eleve_obj.id
          log_action_erp(
              module="Espace Parent",
              action=(
                  f"Consultation sécurisée du dossier de l'élève"
                  f" {eleve_obj.nom} {eleve_obj.prenom}"
                  f" (Matricule: {eleve_obj.matricule})"
              ),
              statut="Succès",
          )

        st.success(
            f"📌 Suivi de l'élève : **{eleve_obj.nom} {eleve_obj.prenom}** |"
            f" Classe : **{classe_nom}**"
        )

        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
            "📚 Notes & Évaluations",
            "📋 Bulletins",
            "🕒 Emploi du Temps",
            "📌 Assiduité (Cahier d'appel)",
            "💳 Situation Financière",
            "✉️ Envoyer un message",
        ])

        # Onglet 1 : Notes & Évaluations
        with tab1:
          st.markdown("#### Notes des Évaluations Récentes")
          notes_list = (
              db.query(Note).filter(Note.eleve_id == eleve_obj.id).all()
          )
          if not notes_list:
            st.info("Aucune note enregistrée pour le moment.")
          else:
            data_notes = []
            for n in notes_list:
              mat = (
                  db.query(Matiere)
                  .filter(Matiere.id == n.matiere_id)
                  .first()
              )
              mat_lib = (
                  mat.libelle
                  if mat and hasattr(mat, "libelle") and mat.libelle
                  else getattr(mat, "nom", "N/D")
              )
              data_notes.append({
                  "Matière": mat_lib,
                  "Type d'évaluation": n.type_evaluation,
                  "Semestre": getattr(n, "semestre", getattr(n, "trimestre", "N/D")),
                  "Note /20": float(n.valeur),
              })
            st.dataframe(pd.DataFrame(data_notes), use_container_width=True, hide_index=True)

        # Onglet 2 : Bulletins
        with tab2:
          st.markdown("#### Synthèse du Bulletin de Notes")
          notes_list = (
              db.query(Note).filter(Note.eleve_id == eleve_obj.id).all()
          )
          if not notes_list:
            st.info("Bulletin non disponible (aucune note saisie).")
          else:
            matieres_dict = {}
            for n in notes_list:
              mat = (
                  db.query(Matiere)
                  .filter(Matiere.id == n.matiere_id)
                  .first()
              )
              nom_mat = (
                  (mat.libelle if hasattr(mat, "libelle") and mat.libelle else getattr(mat, "nom", "Autre"))
                  if mat
                  else "Autre"
              )
              if nom_mat not in matieres_dict:
                matieres_dict[nom_mat] = []
              matieres_dict[nom_mat].append(float(n.valeur))

            bulletin_data = []
            total_points = 0.0
            total_coef = 0.0
            for mat_nom, notes in matieres_dict.items():
              moy_mat = sum(notes) / len(notes)
              mat_obj = (
                  db.query(Matiere)
                  .filter(
                      (Matiere.libelle == mat_nom) | (Matiere.nom == mat_nom)
                  )
                  .first()
              )
              coef = float(getattr(mat_obj, "coefficient", 1.0) or 1.0) if mat_obj else 1.0
              total_points += moy_mat * coef
              total_coef += coef
              bulletin_data.append({
                  "Matière": mat_nom,
                  "Coefficient": coef,
                  "Moyenne Matière": round(moy_mat, 2),
              })

            st.dataframe(pd.DataFrame(bulletin_data), use_container_width=True, hide_index=True)
            if total_coef > 0:
              moy_generale = total_points / total_coef
              st.metric(
                  "Moyenne Générale Estimée", f"{moy_generale:.2f} / 20"
              )

        # Onglet 3 : Emploi du Temps
        with tab3:
          st.markdown(f"#### Emploi du Temps de la classe : {classe_nom}")
          if not eleve_obj.classe_id:
            st.warning("⚠️ L'élève n'est assigné à aucune classe.")
          else:
            edt_list = (
                db.query(EmploiDuTemps)
                .filter(EmploiDuTemps.classe_id == eleve_obj.classe_id)
                .all()
            )
            if not edt_list:
              st.info("Aucun emploi du temps configuré pour cette classe.")
            else:
              edt_data = []
              for ed in edt_list:
                edt_data.append({
                    "Jour": ed.jour,
                    "Heure": ed.heure,
                    "Matière": ed.matiere,
                    "Enseignant": getattr(ed, "enseignant", "N/D") or "N/D",
                })
              st.dataframe(pd.DataFrame(edt_data), use_container_width=True, hide_index=True)

        # Onglet 4 : Assiduité & Absences (Cahier d'appel)
        with tab4:
          st.markdown("#### Cahier d'Appel — Suivi des Absences et Retards")
          presences_list = (
              db.query(Presence).filter(Presence.eleve_id == eleve_obj.id).all()
          )
          if not presences_list:
            st.info("Aucune absence ou retard signalé. Exemplaire !")
          else:
            pres_data = []
            for p in presences_list:
              pres_data.append({
                  "Date": (
                      p.date.strftime("%d/%m/%Y")
                      if hasattr(p, "date") and p.date
                      else "N/D"
                  ),
                  "Statut": p.statut,
                  "Motif": getattr(p, "motif", None) or "Non spécifié",
              })
            st.dataframe(pd.DataFrame(pres_data), use_container_width=True, hide_index=True)

        # Onglet 5 : Situation Financière
        with tab5:
          st.markdown("#### Situation des Paiements de Scolarité")
          frais_scol = (
              float(getattr(classe, "frais_scolarite", 0.0) or 0.0)
              if classe
              else 0.0
          )
          frais_inscr = (
              float(getattr(classe, "frais_inscription", 0.0) or 0.0)
              if classe
              else 0.0
          )
          frais_coges = (
              float(getattr(classe, "frais_coges", 0.0) or 0.0)
              if classe
              else 0.0
          )

          montant_brut = (
              (frais_scol + frais_inscr + frais_coges)
              if (frais_scol + frais_inscr + frais_coges) > 0
              else 65000.0
          )

          reduction = float(getattr(eleve_obj, "montant_reduction", 0.0) or 0.0)
          montant_du_net = max(0.0, montant_brut - reduction)

          paiements_eleve = (
              db.query(Paiement).filter(Paiement.eleve_id == eleve_obj.id).all()
          )
          montant_paye = (
              sum(float(p.montant) for p in paiements_eleve)
              if paiements_eleve
              else 0.0
          )

          solde_restant = montant_du_net - montant_paye

          col1, col2, col3 = st.columns(3)
          with col1:
            st.metric(
                "Montant Net à Payer",
                f"{montant_du_net:,.0f} FCFA",
                delta=(
                    f"Réduction : -{reduction:,.0f} F"
                    if reduction > 0
                    else None
                ),
            )
          with col2:
            st.metric("Montant Versé", f"{montant_paye:,.0f} FCFA")
          with col3:
            if solde_restant > 0:
              st.metric(
                  "Solde Restant",
                  f"{solde_restant:,.0f} FCFA",
                  delta="Impayé",
                  delta_color="inverse",
              )
            elif solde_restant < 0:
              st.metric(
                  "Solde Restant",
                  f"{abs(solde_restant):,.0f} FCFA",
                  delta="Trop-perçu",
                  delta_color="normal",
              )
            else:
              st.metric(
                  "Solde Restant", "0 FCFA", delta="Soldé", delta_color="normal"
              )

          st.markdown("##### Historique des Versements Officiels")
          if not paiements_eleve:
            st.info("Aucun versement enregistré pour le moment.")
          else:
            hist_paiements = []
            for p in paiements_eleve:
              hist_paiements.append({
                  "Reçu N°": getattr(p, "reference_recu", "N/D"),
                  "Date": (
                      p.date_paiement.strftime("%d/%m/%Y %H:%M")
                      if getattr(p, "date_paiement", None)
                      else "N/D"
                  ),
                  "Montant (FCFA)": f"{float(p.montant):,.0f}",
                  "Mode": getattr(p, "mode_reglement", "Espèces"),
                  "Motif": getattr(p, "motif", "Scolarité"),
              })
            st.dataframe(
                pd.DataFrame(hist_paiements), use_container_width=True, hide_index=True
            )

        # Onglet 6 : Envoyer un message à l'administration
        with tab6:
          st.markdown("#### ✉️ Contacter l'Administration")
          st.markdown(f"Envoyez un message concernant le suivi de **{eleve_obj.nom} {eleve_obj.prenom}** directement à la direction.")
          
          with st.form("form_contact_admin_parent"):
            objet_message = st.text_input("Objet", placeholder="Ex : Demande de rendez-vous, Motif d'absence...")
            contenu_message = st.text_area("Message", placeholder="Rédigez votre message ici...")
            
            submit_msg = st.form_submit_button("Envoyer le message", type="primary")
            
            if submit_msg:
              if not objet_message or not contenu_message:
                st.error("⚠️ Veuillez renseigner l'objet et le contenu du message.")
              else:
                try:
                  nouveau_message = Message(
                      school_id=school_id,
                      expediteur=username or "Parent",
                      destinataire="Administration",
                      objet=f"[{eleve_obj.nom} {eleve_obj.prenom}] {objet_message}",
                      contenu=contenu_message,
                      date_envoi=datetime.now()
                  )
                  db.add(nouveau_message)
                  db.commit()

                  log_action_erp(
                      module="Espace Parent",
                      action=f"Envoi d'un message à l'administration concernant l'élève {eleve_obj.nom} {eleve_obj.prenom}",
                      statut="Succès"
                  )

                  st.success("✅ Votre message a été transmis avec succès à l'administration !")
                except Exception as ex:
                  db.rollback()
                  st.error(f"Erreur lors de l'envoi du message : {ex}")

  finally:
    db.close()


# Alias de compatibilité exhaustive pour le routeur app.py
afficher_espace_parent = afficher_espace_parent
afficher_portail_parent = afficher_espace_parent
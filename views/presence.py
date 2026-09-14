from datetime import datetime
from database.queries import get_classes_cached
import pandas as pd
import streamlit as st
from database.db_config import SessionLocal
from database.models import ActivityLog, Classe, Eleve, Presence, School


def afficher_presence():
  st.subheader("📋 Gestion de l'Assiduité & Registre des Présences")
  st.markdown(
      "Suivi des présences en temps réel, saisie par les enseignants et tableau"
      " de bord de contrôle pour le Censeur."
  )
  st.markdown("---")

  school_id = st.session_state.get("school_id")
  is_super_admin = st.session_state.get("is_super_admin", False)
  role_utilisateur = str(st.session_state.get("role", "")).lower()
  username = st.session_state.get("username", "admin")
  cycle_en_cours = st.session_state.get("cycle_actif", "Collège")

  if not school_id and not is_super_admin:
    st.warning("⚠️ Veuillez vous connecter pour accéder à cette section.")
    return

  db = SessionLocal()
  try:
    target_school_id = school_id
    if is_super_admin and not target_school_id:
      ecole_defaut = db.query(School).first()
      target_school_id = ecole_defaut.id if ecole_defaut else 1

    if school_id:
      ecole_courante = (
          db.query(School).filter(School.id == school_id).first()
      )
      school_name = (
          ecole_courante.nom
          if ecole_courante
          else st.session_state.get("school_name", "Établissement")
      )
    else:
      school_name = st.session_state.get("school_name", "Établissement")

    # Isolation des classes par cycle et par école
    classes_query = db.query(Classe).filter(Classe.cycle == cycle_en_cours)
    if not is_super_admin and school_id:
      classes_query = classes_query.filter(Classe.school_id == school_id)
    else:
      classes_query = classes_query.filter(
          Classe.school_id == target_school_id
      )
    classes_cycle = classes_query.all()

    st.markdown(
        f"### Suivi d'Assiduité — **{school_name} ({cycle_en_cours})**"
    )

    if not classes_cycle:
      st.warning(
          f"⚠️ Aucune classe configurée pour le cycle **{cycle_en_cours}**."
      )
      return

    noms_classes = [c.libelle if hasattr(c, 'libelle') else getattr(c, 'nom', '') for c in classes_cycle]

    col_sel1, col_sel2 = st.columns(2)
    with col_sel1:
      classe_choisie = st.selectbox(
          "Sélectionner la classe", noms_classes, key="presence_classe_select"
      )
    with col_sel2:
      date_appel = st.date_input(
          "Date concernée",
          value=datetime.now().date(),
          key="presence_date_select",
      )

    classe_obj = next(
        (c for c in classes_cycle if (c.libelle if hasattr(c, 'libelle') else getattr(c, 'nom', '')) == classe_choisie), None
    )
    if not classe_obj:
      return

    eleves_query = db.query(Eleve).filter(
        Eleve.classe_id == classe_obj.id, Eleve.school_id == target_school_id
    )
    eleves = eleves_query.order_by(Eleve.nom).all()

    if not eleves:
      st.info(f"Aucun élève inscrit dans la classe **{classe_choisie}**.")
      return

    # --- ROUTAGE DES INTERFACES SELON LE RÔLE ---
    is_censeur_or_admin = role_utilisateur in [
        "censeur",
        "directeur",
        "super_admin",
        "surveillant",
    ]

    # Récupérer les présences existantes pour la classe à cette date
    existantes = (
        db.query(Presence)
        .join(Eleve)
        .filter(
            Presence.school_id == target_school_id,
            Presence.date == date_appel,
            Eleve.classe_id == classe_obj.id,
        )
        .all()
    )
    dict_existantes = {p.eleve_id: p for p in existantes}

    if is_censeur_or_admin:
      # ==========================================
      # ESPACE CENSEUR / ADMINISTRATION (Contrôle & Synthèse amélioré)
      # ==========================================
      st.info(
          f"📐 Espace Censeur / Direction — Tableau de contrôle et de régularisation"
          f" pour la classe de **{classe_choisie}** au"
          f" {date_appel.strftime('%d/%m/%Y')} ({len(eleves)} élèves)."
      )

      if not existantes:
        st.warning(
            "⚠️ Aucun appel n'a encore été transmis par le professeur pour"
            " cette date. La liste complète des élèves s'affiche ci-dessous"
            " pour un contrôle ou une saisie administrative par exception."
        )

      data_suivi_censeur = []
      for e in eleves:
        p_ex = dict_existantes.get(e.id)
        statut_defaut = p_ex.statut if p_ex else "Présent"
        motif_defaut = p_ex.motif if p_ex and p_ex.motif else "Aucun"

        data_suivi_censeur.append({
            "eleve_id": e.id,
            "Matricule": e.matricule,
            "Nom & Prénom": f"{e.nom} {e.prenom}",
            "Statut": statut_defaut,
            "Motif / Remarque": motif_defaut,
        })

      df_suivi = pd.DataFrame(data_suivi_censeur)

      # Tableau éditable pour le Censeur
      edited_df_censeur = st.data_editor(
          df_suivi,
          column_config={
              "eleve_id": None,
              "Matricule": st.column_config.TextColumn(
                  "Matricule", disabled=True
              ),
              "Nom & Prénom": st.column_config.TextColumn(
                  "Nom & Prénom", disabled=True
              ),
              "Statut": st.column_config.SelectboxColumn(
                  "Statut administratif",
                  options=[
                      "Présent",
                      "Absent non justifié",
                      "Absent justifié",
                      "Retard",
                  ],
                  required=True,
              ),
              "Motif / Remarque": st.column_config.TextColumn(
                  "Motif / Visa de la Censure"
              ),
          },
          hide_index=True,
          use_container_width=True,
          key=f"editor_censeur_{classe_choisie}_{date_appel}",
      )

      col_exp1, col_exp2 = st.columns(2)
      with col_exp1:
        if st.button(
            "🛡️ Enregistrer les modifications de la Censure", type="primary"
        ):
          eleve_ids = [
              row["eleve_id"] for _, row in edited_df_censeur.iterrows()
          ]
          db.query(Presence).filter(
              Presence.school_id == target_school_id,
              Presence.date == date_appel,
              Presence.eleve_id.in_(eleve_ids),
          ).delete(synchronize_session=False)

          for _, row in edited_df_censeur.iterrows():
            nouvelle_presence = Presence(
                school_id=target_school_id,
                eleve_id=row["eleve_id"],
                date=date_appel,
                statut=row["Statut"],
                motif=(
                    row["Motif / Remarque"].strip()
                    if row["Motif / Remarque"]
                    and row["Motif / Remarque"] != "Aucun"
                    else None
                ),
            )
            db.add(nouvelle_presence)

          nouveau_log = ActivityLog(
              school_id=target_school_id,
              timestamp=datetime.now(),
              username=username,
              action=(
                  f"Validation/Régularisation censure — Classe {classe_choisie}"
                  f" ({date_appel.strftime('%d/%m/%Y')}) par {username}"
              ),
              module="Présence",
              statut="Succès",
          )
          db.add(nouveau_log)
          db.commit()

          st.success(
              f"✅ Registre officiel de la classe **{classe_choisie}** mis à jour"
              " et archivé avec succès !"
          )
          st.rerun()

      with col_exp2:
        # --- BOUTON D'EXPORT OFFICIEL ---
        csv_data = df_suivi.drop(columns=["eleve_id"]).to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Exporter la feuille d'appel (CSV)",
            data=csv_data,
            file_name=(
                f"appel_{classe_choisie}_{date_appel.strftime('%Y%m%d')}.csv"
            ),
            mime="text/csv",
        )

    else:
      # ==========================================
      # ESPACE ENSEIGNANT (Saisie de la feuille d'appel)
      # ==========================================
      st.info(
          f"👨‍🏫 Espace Enseignant — Feuille d'appel active pour la classe de"
          f" **{classe_choisie}** ({len(eleves)} élèves)."
      )

      data_appel = []
      for e in eleves:
        p_ex = dict_existantes.get(e.id)
        statut_defaut = p_ex.statut if p_ex else "Présent"
        motif_defaut = p_ex.motif if p_ex and p_ex.motif else ""

        data_appel.append({
            "eleve_id": e.id,
            "Matricule": e.matricule,
            "Nom & Prénom": f"{e.nom} {e.prenom}",
            "Statut": statut_defaut,
            "Motif": motif_defaut,
        })

      df_appel = pd.DataFrame(data_appel)

      edited_df = st.data_editor(
          df_appel,
          column_config={
              "eleve_id": None,
              "Matricule": st.column_config.TextColumn(
                  "Matricule", disabled=True
              ),
              "Nom & Prénom": st.column_config.TextColumn(
                  "Nom & Prénom", disabled=True
              ),
              "Statut": st.column_config.SelectboxColumn(
                  "Statut",
                  options=[
                      "Présent",
                      "Absent non justifié",
                      "Absent justifié",
                      "Retard",
                  ],
                  required=True,
              ),
              "Motif": st.column_config.TextColumn(
                  "Précisions / Motif (si absent ou retard)"
              ),
          },
          hide_index=True,
          use_container_width=True,
          key=f"editor_presence_{classe_choisie}_{date_appel}",
      )

      col_ens1, col_ens2 = st.columns(2)
      with col_ens1:
        if st.button(
            "💾 Transmettre l'appel à la Censure", type="primary"
        ):
          eleve_ids = [row["eleve_id"] for _, row in edited_df.iterrows()]
          db.query(Presence).filter(
              Presence.school_id == target_school_id,
              Presence.date == date_appel,
              Presence.eleve_id.in_(eleve_ids),
          ).delete(synchronize_session=False)

          for _, row in edited_df.iterrows():
            nouvelle_presence = Presence(
                school_id=target_school_id,
                eleve_id=row["eleve_id"],
                date=date_appel,
                statut=row["Statut"],
                motif=row["Motif"].strip() if row["Motif"] else None,
            )
            db.add(nouvelle_presence)

          nouveau_log = ActivityLog(
              school_id=target_school_id,
              timestamp=datetime.now(),
              username=username,
              action=(
                  f"Saisie appel de classe - {classe_choisie}"
                  f" ({date_appel.strftime('%d/%m/%Y')}) par le professeur"
                  f" {username}"
              ),
              module="Présence",
              statut="Succès",
          )
          db.add(nouveau_log)
          db.commit()

          st.success(
              f"✅ Feuille d'appel transmise avec succès pour la classe"
              f" **{classe_choisie}** !"
          )
          st.rerun()

      with col_ens2:
        csv_data_ens = df_appel.drop(columns=["eleve_id"]).to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Télécharger la feuille (CSV)",
            data=csv_data_ens,
            file_name=(
                f"appel_{classe_choisie}_{date_appel.strftime('%Y%m%d')}.csv"
            ),
            mime="text/csv",
        )

  finally:
    db.close()


# Alias de compatibilité
afficher_gestion_presence = afficher_presence
afficher_presence = afficher_presence